from datetime import datetime

import pandas as pd


class DataCleaner:
    """Cleans and normalizes transaction CSV data."""

    @staticmethod
    def normalize_dates(series: pd.Series) -> pd.Series:
        parsed = pd.to_datetime(series, errors="coerce", dayfirst=True)
        if parsed.isna().any():
            fallback = pd.to_datetime(series, errors="coerce", dayfirst=False)
            parsed = parsed.fillna(fallback)
        return parsed

    @staticmethod
    def clean_amount(value: object) -> float | None:
        if pd.isna(value):
            return None
        text = str(value).strip().replace(",", "").replace("$", "")
        try:
            return float(text)
        except ValueError:
            return None

    @classmethod
    def clean(cls, df: pd.DataFrame) -> pd.DataFrame:
        cleaned = df.copy()
        cleaned.columns = [col.strip().lower() for col in cleaned.columns]

        cleaned["date"] = cls.normalize_dates(cleaned["date"])
        cleaned["amount"] = cleaned["amount"].apply(cls.clean_amount)
        cleaned["currency"] = (
            cleaned["currency"].astype(str).str.strip().str.upper()
        )
        cleaned["status"] = cleaned["status"].astype(str).str.strip().str.upper()
        cleaned["merchant"] = cleaned["merchant"].astype(str).str.strip()
        cleaned["txn_id"] = cleaned["txn_id"].astype(str).str.strip()
        cleaned["account_id"] = cleaned["account_id"].astype(str).str.strip()

        if "category" not in cleaned.columns:
            cleaned["category"] = None
        cleaned["category"] = cleaned["category"].apply(
            lambda x: str(x).strip() if pd.notna(x) and str(x).strip() else "Uncategorized"
        )

        cleaned = cleaned.dropna(subset=["date", "amount", "txn_id", "account_id"])
        cleaned = cleaned.drop_duplicates(subset=["txn_id"], keep="first")

        return cleaned.reset_index(drop=True)

    @staticmethod
    def to_records(df: pd.DataFrame) -> list[dict]:
        records: list[dict] = []
        for row in df.to_dict(orient="records"):
            date_value = row["date"]
            if isinstance(date_value, pd.Timestamp):
                date_value = date_value.to_pydatetime()
            elif not isinstance(date_value, datetime):
                date_value = pd.to_datetime(date_value).to_pydatetime()

            records.append(
                {
                    "txn_id": row["txn_id"],
                    "date": date_value,
                    "merchant": row["merchant"],
                    "amount": float(row["amount"]),
                    "currency": row["currency"],
                    "status": row["status"],
                    "category": row.get("category"),
                    "account_id": row["account_id"],
                }
            )
        return records
