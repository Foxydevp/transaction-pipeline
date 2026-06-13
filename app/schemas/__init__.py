from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.constants import JobStatus


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str = "Job accepted for processing"


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    row_count_raw: int | None = None
    row_count_clean: int | None = None
    created_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)


class JobListItem(BaseModel):
    job_id: str
    filename: str
    status: JobStatus
    row_count_raw: int | None = None
    row_count_clean: int | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    jobs: list[JobListItem]
    total: int


class TransactionResponse(BaseModel):
    txn_id: str
    date: datetime
    merchant: str
    amount: float
    currency: str
    status: str
    category: str | None = None
    account_id: str
    is_anomaly: bool
    anomaly_reason: str | None = None
    llm_category: str | None = None
    llm_failed: bool = False

    model_config = ConfigDict(from_attributes=True)

    @field_validator("amount", mode="before")
    @classmethod
    def normalize_amount(cls, value: object) -> float:
        if isinstance(value, Decimal):
            return float(value)
        return float(value)  # type: ignore[arg-type]


class CategoryBreakdownItem(BaseModel):
    category: str
    count: int
    total_amount: float


class LLMSummaryResponse(BaseModel):
    total_spend_by_currency: dict[str, float]
    top_merchants: list[dict[str, Any]]
    anomaly_count: int
    narrative: str
    risk_level: str


class JobResultsResponse(BaseModel):
    job_id: str
    status: JobStatus
    cleaned_transactions: list[TransactionResponse]
    anomalies: list[TransactionResponse]
    category_breakdown: list[CategoryBreakdownItem]
    llm_summary: LLMSummaryResponse | None = None


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    version: str
