from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import JobStatus
from app.models import Job, JobSummary, Transaction
from app.schemas import (
    CategoryBreakdownItem,
    JobListItem,
    JobResultsResponse,
    JobStatusResponse,
    LLMSummaryResponse,
    TransactionResponse,
)
from app.services.anomaly_detector import AnomalyDetector
from app.services.data_cleaner import DataCleaner
from app.services.groq_service import GroqService


class JobService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_job(
        self,
        filename: str,
        file_path: Path,
        row_count_raw: int,
        job_id: str | None = None,
    ) -> Job:
        job = Job(
            id=job_id,
            filename=filename,
            file_path=str(file_path),
            status=JobStatus.PENDING,
            row_count_raw=row_count_raw,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self.db.query(Job).filter(Job.id == job_id).first()

    def get_job_or_404(self, job_id: str) -> Job:
        job = self.get_job(job_id)
        if not job:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )
        return job

    def list_jobs(self, status: JobStatus | None = None) -> tuple[list[Job], int]:
        query = self.db.query(Job)
        if status:
            query = query.filter(Job.status == status)
        total = query.count()
        jobs = query.order_by(Job.created_at.desc()).all()
        return jobs, total

    def get_status(self, job_id: str) -> JobStatusResponse:
        job = self.get_job_or_404(job_id)
        return JobStatusResponse(
            job_id=job.id,
            status=job.status,
            row_count_raw=job.row_count_raw,
            row_count_clean=job.row_count_clean,
            created_at=job.created_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )

    def get_results(self, job_id: str) -> JobResultsResponse:
        job = self.get_job_or_404(job_id)

        if job.status != JobStatus.COMPLETED:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Job is not completed (current status: {job.status.value})",
            )

        transactions = (
            self.db.query(Transaction)
            .filter(Transaction.job_id == job_id)
            .order_by(Transaction.date.desc())
            .all()
        )

        cleaned = [
            TransactionResponse.model_validate(txn)
            for txn in transactions
            if not txn.is_anomaly
        ]
        anomalies = [
            TransactionResponse.model_validate(txn)
            for txn in transactions
            if txn.is_anomaly
        ]

        category_expr = func.coalesce(
            Transaction.llm_category, Transaction.category, "Other"
        ).label("category")
        breakdown_rows = (
            self.db.query(
                category_expr,
                func.count(Transaction.id).label("count"),
                func.sum(Transaction.amount).label("total_amount"),
            )
            .filter(Transaction.job_id == job_id)
            .group_by(category_expr)
            .all()
        )

        category_breakdown = [
            CategoryBreakdownItem(
                category=row.category,
                count=int(row.count),
                total_amount=float(row.total_amount or 0),
            )
            for row in breakdown_rows
        ]

        spend_rows = (
            self.db.query(
                Transaction.currency,
                func.sum(Transaction.amount).label("total"),
            )
            .filter(Transaction.job_id == job_id)
            .group_by(Transaction.currency)
            .all()
        )
        spend_by_currency = {
            row.currency: float(row.total or 0) for row in spend_rows
        }

        llm_summary = None
        if job.summary:
            llm_summary = LLMSummaryResponse(
                total_spend_by_currency=spend_by_currency,
                top_merchants=job.summary.top_merchants,
                anomaly_count=job.summary.anomaly_count,
                narrative=job.summary.narrative,
                risk_level=job.summary.risk_level,
            )

        return JobResultsResponse(
            job_id=job.id,
            status=job.status,
            cleaned_transactions=cleaned,
            anomalies=anomalies,
            category_breakdown=category_breakdown,
            llm_summary=llm_summary,
        )

    @staticmethod
    def to_list_items(jobs: list[Job]) -> list[JobListItem]:
        return [
            JobListItem(
                job_id=job.id,
                filename=job.filename,
                status=job.status,
                row_count_raw=job.row_count_raw,
                row_count_clean=job.row_count_clean,
                created_at=job.created_at,
                completed_at=job.completed_at,
            )
            for job in jobs
        ]


class PipelineService:
    """Orchestrates the full transaction processing pipeline."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.cleaner = DataCleaner()
        self.anomaly_detector = AnomalyDetector()
        self.llm = GroqService()

    def process_job(self, job_id: str) -> None:
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = JobStatus.PROCESSING
        job.error_message = None
        self.db.commit()

        try:
            raw_df = pd.read_csv(job.file_path)
            cleaned_df = self.cleaner.clean(raw_df)
            job.row_count_clean = len(cleaned_df)

            anomaly_df = self.anomaly_detector.detect(cleaned_df)
            classified_df, _ = self.llm.classify_transactions(anomaly_df)
            summary_data = self.llm.generate_summary(classified_df)

            self._persist_transactions(job, classified_df)
            self._persist_summary(job, summary_data)

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            job = self.db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                self.db.commit()
            raise

    def _persist_transactions(self, job: Job, df: pd.DataFrame) -> None:
        self.db.query(Transaction).filter(Transaction.job_id == job.id).delete()

        records = df.to_dict(orient="records")
        for row in records:
            date_value = row["date"]
            if hasattr(date_value, "to_pydatetime"):
                date_value = date_value.to_pydatetime()

            self.db.add(
                Transaction(
                    job_id=job.id,
                    txn_id=str(row["txn_id"]),
                    date=date_value,
                    merchant=str(row["merchant"]),
                    amount=float(row["amount"]),
                    currency=str(row["currency"]),
                    status=str(row["status"]),
                    category=row.get("category"),
                    account_id=str(row["account_id"]),
                    is_anomaly=bool(row.get("is_anomaly", False)),
                    anomaly_reason=row.get("anomaly_reason"),
                    llm_category=row.get("llm_category"),
                    llm_failed=bool(row.get("llm_failed", False)),
                )
            )

    def _persist_summary(self, job: Job, summary: dict) -> None:
        spend = summary.get("total_spend_by_currency", {})
        existing = (
            self.db.query(JobSummary).filter(JobSummary.job_id == job.id).first()
        )
        if existing:
            self.db.delete(existing)
            self.db.flush()

        self.db.add(
            JobSummary(
                job_id=job.id,
                total_spend_inr=float(spend.get("INR", 0)),
                total_spend_usd=float(spend.get("USD", 0)),
                top_merchants=summary.get("top_merchants", []),
                anomaly_count=int(summary.get("anomaly_count", 0)),
                narrative=str(summary.get("narrative", "")),
                risk_level=str(summary.get("risk_level", "low")),
            )
        )
