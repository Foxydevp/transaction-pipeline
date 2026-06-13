import json
import logging
import time
from typing import Any

import google.generativeai as genai
import pandas as pd

from app.core.config import settings
from app.core.constants import LLMCategory

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {category.value for category in LLMCategory}


class GeminiService:
    """Gemini API integration for classification and narrative summaries."""

    def __init__(self) -> None:
        self._configured = False
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
            self._model = genai.GenerativeModel(settings.gemini_model)
            self._configured = True
        else:
            self._model = None
            logger.warning("GEMINI_API_KEY not set; LLM features will use fallbacks")

    def _call_with_retry(self, prompt: str) -> str:
        if not self._configured or self._model is None:
            raise RuntimeError("Gemini API is not configured")

        last_error: Exception | None = None
        for attempt in range(settings.gemini_max_retries):
            try:
                response = self._model.generate_content(prompt)
                return response.text.strip()
            except Exception as exc:
                last_error = exc
                # If we hit a 429, apply aggressive backoff
                wait_seconds = (attempt + 1) * 6  # 6s, 12s, 18s... gives the RPM quota time to reset
                logger.warning(
                    "Gemini request failed (attempt %s/%s). Retrying in %ss. Error: %s",
                    attempt + 1,
                    settings.gemini_max_retries,
                    wait_seconds,
                    exc,
                )
                if attempt < settings.gemini_max_retries - 1:
                    time.sleep(wait_seconds)

        raise RuntimeError(f"Gemini request failed after retries: {last_error}")

    @staticmethod
    def _parse_json_response(text: str) -> Any:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        return json.loads(cleaned)

    def classify_batch(self, transactions: list[dict[str, Any]]) -> list[str | None]:
        if not transactions:
            return []

        if not self._configured:
            return [None] * len(transactions)

        payload = [
            {
                "txn_id": txn["txn_id"],
                "merchant": txn["merchant"],
                "amount": txn["amount"],
                "currency": txn["currency"],
                "status": txn["status"],
            }
            for txn in transactions
        ]

        prompt = f"""
Classify each transaction into exactly one category from this list:
{sorted(VALID_CATEGORIES)}

Return ONLY valid JSON array with objects:
[{{"txn_id": "...", "category": "..."}}]

Transactions:
{json.dumps(payload, default=str)}
"""
        try:
            raw = self._call_with_retry(prompt)
            parsed = self._parse_json_response(raw)
            category_map = {
                item["txn_id"]: item.get("category")
                for item in parsed
                if isinstance(item, dict) and "txn_id" in item
            }
            results: list[str | None] = []
            for txn in transactions:
                category = category_map.get(txn["txn_id"])
                if category in VALID_CATEGORIES:
                    results.append(category)
                else:
                    results.append(None)
            return results
        except Exception as exc:
            logger.error("Batch classification failed: %s", exc)
            return [None] * len(transactions)

    def classify_transactions(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, list[int]]:
        result = df.copy()
        result["llm_category"] = None
        result["llm_failed"] = False
        failed_indices: list[int] = []

        records = result.to_dict(orient="records")
        batch_size = settings.gemini_batch_size

        for start in range(0, len(records), batch_size):
            # If this isn't the first batch, rest for a moment to protect the free tier RPM limits
            if start > 0:
                logger.info("Enforcing rate-limiting cooldown between transaction batches...")
                time.sleep(4)  # 4-second buffer window protects your 15 RPM cap

            batch = records[start : start + batch_size]
            categories = self.classify_batch(batch)

            for offset, category in enumerate(categories):
                idx = start + offset
                if category is None:
                    result.at[idx, "llm_failed"] = True
                    failed_indices.append(idx)
                else:
                    result.at[idx, "llm_category"] = category

        return result, failed_indices

    def generate_summary(self, df: pd.DataFrame) -> dict[str, Any]:
        spend_by_currency = (
            df.groupby("currency")["amount"]
            .sum()
            .round(2)
            .astype(float)
            .to_dict()
        )

        top_merchants_df = (
            df.groupby("merchant")["amount"]
            .agg(["sum", "count"])
            .reset_index()
            .sort_values("sum", ascending=False)
            .head(5)
        )
        top_merchants = [
            {
                "merchant": row["merchant"],
                "total_amount": float(row["sum"]),
                "transaction_count": int(row["count"]),
            }
            for _, row in top_merchants_df.iterrows()
        ]

        anomaly_count = int(df["is_anomaly"].sum()) if "is_anomaly" in df.columns else 0

        fallback = {
            "total_spend_by_currency": spend_by_currency,
            "top_merchants": top_merchants,
            "anomaly_count": anomaly_count,
            "narrative": (
                f"Processed {len(df)} transactions with {anomaly_count} anomalies detected."
            ),
            "risk_level": self._derive_risk_level(anomaly_count, len(df)),
        }

        if not self._configured:
            return fallback

        stats = {
            "transaction_count": len(df),
            "total_spend_by_currency": spend_by_currency,
            "top_merchants": top_merchants,
            "anomaly_count": anomaly_count,
            "anomaly_examples": df[df["is_anomaly"]]
            .head(5)[["txn_id", "merchant", "amount", "currency", "anomaly_reason"]]
            .to_dict(orient="records"),
        }

        prompt = f"""
Analyze these transaction statistics and return ONLY valid JSON with keys:
- total_spend_by_currency (object)
- top_merchants (array)
- anomaly_count (integer)
- narrative (string, 2-4 sentences)
- risk_level (one of: low, medium, high)

Statistics:
{json.dumps(stats, default=str)}
"""
        try:
            # Short rest before triggering summary generation right after classification batches finish
            time.sleep(2) 
            raw = self._call_with_retry(prompt)
            parsed = self._parse_json_response(raw)
            return {
                "total_spend_by_currency": parsed.get(
                    "total_spend_by_currency", spend_by_currency
                ),
                "top_merchants": parsed.get("top_merchants", top_merchants),
                "anomaly_count": int(parsed.get("anomaly_count", anomaly_count)),
                "narrative": parsed.get("narrative", fallback["narrative"]),
                "risk_level": parsed.get("risk_level", fallback["risk_level"]),
            }
        except Exception as exc:
            logger.error("Summary generation failed, using fallback: %s", exc)
            return fallback

    @staticmethod
    def _derive_risk_level(anomaly_count: int, total_rows: int) -> str:
        if total_rows == 0:
            return "low"
        ratio = anomaly_count / total_rows
        if ratio >= 0.15 or anomaly_count >= 10:
            return "high"
        if ratio >= 0.05 or anomaly_count >= 3:
            return "medium"
        return "low"