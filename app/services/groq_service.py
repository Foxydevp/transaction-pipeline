import json
import logging
import time
from typing import Any

import pandas as pd
from groq import Groq

from app.core.config import settings
from app.core.constants import LLMCategory

logger = logging.getLogger(__name__)
VALID_CATEGORIES = {category.value for category in LLMCategory}

class GroqService:
    """Groq API integration for blazing fast classification and summaries."""

    def __init__(self) -> None:
        self._configured = False
        if settings.groq_api_key:
            self.client = Groq(api_key=settings.groq_api_key)
            self.model = settings.groq_model
            self._configured = True
        else:
            self.client = None
            logger.warning("GROQ_API_KEY not set; LLM features will use fallbacks")

    def _call_with_retry(self, prompt: str) -> str:
        if not self._configured or self.client is None:
            raise RuntimeError("Groq API is not configured")

        last_error: Exception | None = None
        # Groq's limits are much higher, but we keep a brief retry mechanism just in case
        for attempt in range(settings.gemini_max_retries): 
            try:
                # Groq requires JSON mode to have the word "JSON" in the prompt
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0, # 0 makes it strictly factual and deterministic
                    response_format={"type": "json_object"} # Guarantees valid JSON output
                )
                return response.choices[0].message.content
            except Exception as exc:
                last_error = exc
                wait_seconds = (attempt + 1) * 3
                logger.warning(f"Groq request failed. Retrying in {wait_seconds}s. Error: {exc}")
                time.sleep(wait_seconds)

        raise RuntimeError(f"Groq request failed after retries: {last_error}")

    def classify_batch(self, transactions: list[dict[str, Any]]) -> list[str | None]:
        if not transactions or not self._configured:
            return [None] * len(transactions)

        payload = [
            {
                "txn_id": txn["txn_id"],
                "merchant": txn["merchant"],
                "amount": txn["amount"],
                "notes": txn.get("notes", "") # Added notes for better context
            }
            for txn in transactions
        ]

        prompt = f"""
You are a transaction classifier. Classify each transaction into exactly one category from this list: {sorted(VALID_CATEGORIES)}

You must return a valid JSON object with a single root key called "transactions", which contains an array of objects.
Format: {{"transactions": [{{"txn_id": "...", "category": "..."}}]}}

Transactions to classify:
{json.dumps(payload, default=str)}
"""
        try:
            raw = self._call_with_retry(prompt)
            parsed = json.loads(raw)
            
            # Extract the array from the JSON object root
            results_array = parsed.get("transactions", [])
            category_map = {item["txn_id"]: item.get("category") for item in results_array}
            
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

    def classify_transactions(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[int]]:
        result = df.copy()
        result["llm_category"] = None
        result["llm_failed"] = False
        failed_indices: list[int] = []

        records = result.to_dict(orient="records")
        batch_size = 50 # We can safely use 50 here with Groq!

        for start in range(0, len(records), batch_size):
            if start > 0:
                time.sleep(2) # Tiny 2-second buffer to comfortably stay under 30 RPM
                
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
        # Keep your existing Pandas aggregations exactly as they were!
        spend_by_currency = df.groupby("currency")["amount"].sum().round(2).to_dict()
        top_merchants_df = df.groupby("merchant")["amount"].agg(["sum", "count"]).reset_index().sort_values("sum", ascending=False).head(5)
        top_merchants = [
            {"merchant": row["merchant"], "total_amount": float(row["sum"]), "transaction_count": int(row["count"])}
            for _, row in top_merchants_df.iterrows()
        ]
        anomaly_count = int(df["is_anomaly"].sum()) if "is_anomaly" in df.columns else 0

        fallback = {
            "total_spend_by_currency": spend_by_currency, "top_merchants": top_merchants,
            "anomaly_count": anomaly_count, "narrative": f"Processed {len(df)} transactions.", "risk_level": "low"
        }

        if not self._configured: return fallback

        stats = {
            "transaction_count": len(df), "total_spend_by_currency": spend_by_currency,
            "top_merchants": top_merchants, "anomaly_count": anomaly_count,
        }

        prompt = f"""
Analyze these transaction statistics. Return a valid JSON object with EXACTLY these keys:
- "total_spend_by_currency" (object)
- "top_merchants" (array)
- "anomaly_count" (integer)
- "narrative" (string, 2-4 sentences explaining the spending habits)
- "risk_level" (string: "low", "medium", or "high")

Statistics:
{json.dumps(stats, default=str)}
"""
        try:
            raw = self._call_with_retry(prompt)
            parsed = json.loads(raw)
            return {
                "total_spend_by_currency": parsed.get("total_spend_by_currency", spend_by_currency),
                "top_merchants": parsed.get("top_merchants", top_merchants),
                "anomaly_count": int(parsed.get("anomaly_count", anomaly_count)),
                "narrative": parsed.get("narrative", fallback["narrative"]),
                "risk_level": parsed.get("risk_level", fallback["risk_level"]),
            }
        except Exception as exc:
            logger.error("Summary generation failed: %s", exc)
            return fallback