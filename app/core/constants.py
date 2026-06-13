import enum

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class LLMCategory(str, enum.Enum):
    FOOD = "Food"
    SHOPPING = "Shopping"
    TRAVEL = "Travel"
    TRANSPORT = "Transport"
    UTILITIES = "Utilities"
    CASH_WITHDRAWAL = "Cash Withdrawal"
    ENTERTAINMENT = "Entertainment"
    OTHER = "Other"


USD_ANOMALY_MERCHANTS = frozenset({"SWIGGY", "OLA", "IRCTC"})

REQUIRED_CSV_COLUMNS = frozenset(
    {
        "txn_id",
        "date",
        "merchant",
        "amount",
        "currency",
        "status",
        "account_id",
        "notes",
    }
)

OPTIONAL_CSV_COLUMNS = frozenset({"category"})

ALL_CSV_COLUMNS = REQUIRED_CSV_COLUMNS | OPTIONAL_CSV_COLUMNS
print("REQUIRED_CSV_COLUMNS =", REQUIRED_CSV_COLUMNS)
print("OPTIONAL_CSV_COLUMNS =", OPTIONAL_CSV_COLUMNS)
print("ALL_CSV_COLUMNS =", ALL_CSV_COLUMNS)