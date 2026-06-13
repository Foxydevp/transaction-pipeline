"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-06-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  
    job_status = postgresql.ENUM(
        "pending",
        "processing",
        "completed",
        "failed",
        name="job_status"
    )

    # 2. Alembic will automatically create the ENUM when it builds this table
    op.create_table(
        "jobs",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("row_count_raw", sa.Integer(), nullable=True),
        sa.Column("row_count_clean", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jobs_status"), "jobs", ["status"], unique=False)

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("txn_id", sa.String(length=128), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("merchant", sa.String(length=512), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=True),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("is_anomaly", sa.Boolean(), nullable=False),
        sa.Column("anomaly_reason", sa.Text(), nullable=True),
        sa.Column("llm_category", sa.String(length=128), nullable=True),
        sa.Column("llm_failed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_transactions_account_id"), "transactions", ["account_id"], unique=False
    )
    op.create_index(op.f("ix_transactions_job_id"), "transactions", ["job_id"], unique=False)
    op.create_index(op.f("ix_transactions_txn_id"), "transactions", ["txn_id"], unique=False)

    op.create_table(
        "job_summaries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("total_spend_inr", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("total_spend_usd", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("top_merchants", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("anomaly_count", sa.Integer(), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_job_summaries_job_id"), "job_summaries", ["job_id"], unique=True
    )

def downgrade() -> None:
    op.drop_index(op.f("ix_job_summaries_job_id"), table_name="job_summaries")
    op.drop_table("job_summaries")
    op.drop_index(op.f("ix_transactions_txn_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_job_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_account_id"), table_name="transactions")
    op.drop_table("transactions")
    op.drop_index(op.f("ix_jobs_status"), table_name="jobs")
    op.drop_table("jobs")
    op.execute("DROP TYPE IF EXISTS job_status")
