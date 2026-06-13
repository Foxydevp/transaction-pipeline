from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import JobStatus
from app.core.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
    )
    row_count_raw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_count_clean: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    summary: Mapped["JobSummary | None"] = relationship(
        "JobSummary",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    txn_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    merchant: Mapped[str] = mapped_column(String(512), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    is_anomaly: Mapped[bool] = mapped_column(default=False, nullable=False)
    anomaly_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    llm_failed: Mapped[bool] = mapped_column(default=False, nullable=False)

    job: Mapped["Job"] = relationship("Job", back_populates="transactions")


class JobSummary(Base):
    __tablename__ = "job_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    total_spend_inr: Mapped[float] = mapped_column(
        Numeric(18, 2), nullable=False, default=0
    )
    total_spend_usd: Mapped[float] = mapped_column(
        Numeric(18, 2), nullable=False, default=0
    )
    top_merchants: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    anomaly_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    narrative: Mapped[str] = mapped_column(Text, nullable=False, default="")
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False, default="low")

    job: Mapped["Job"] = relationship("Job", back_populates="summary")
