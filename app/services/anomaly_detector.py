import pandas as pd

from app.core.constants import USD_ANOMALY_MERCHANTS


class AnomalyDetector:
    """Detects anomalous transactions using rule-based heuristics."""

    @staticmethod
    def _merchant_key(merchant: str) -> str:
        return merchant.strip().upper()

    @classmethod
    def detect(cls, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        result["is_anomaly"] = False
        result["anomaly_reason"] = None

        account_medians = result.groupby("account_id")["amount"].median()

        for idx, row in result.iterrows():
            reasons: list[str] = []
            account_id = row["account_id"]
            amount = float(row["amount"])
            median = float(account_medians.get(account_id, amount))

            if median > 0 and amount > 3 * median:
                reasons.append(
                    f"Amount {amount:.2f} exceeds 3x account median ({median:.2f})"
                )

            currency = str(row["currency"]).upper()
            merchant = cls._merchant_key(str(row["merchant"]))
            if currency == "USD" and merchant in USD_ANOMALY_MERCHANTS:
                reasons.append(
                    f"USD currency used with local merchant {row['merchant']}"
                )

            if reasons:
                result.at[idx, "is_anomaly"] = True
                result.at[idx, "anomaly_reason"] = "; ".join(reasons)

        return result
