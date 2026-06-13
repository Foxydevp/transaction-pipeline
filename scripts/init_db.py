#!/usr/bin/env python3
"""
Verify PostgreSQL connectivity and create all application tables.

Uses Alembic migrations (same path as production) so schema stays in sync
with alembic/versions/.

Usage (from project root):
    python scripts/init_db.py

Optional:
    python scripts/init_db.py --check-only   # connection + table check, no migrations
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path when run as: python scripts/init_db.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.core.config import settings
from app.core.database import engine
from app.models import Job, JobSummary, Transaction  # noqa: F401 — register models

EXPECTED_TABLES = ("jobs", "transactions", "job_summaries")


def mask_database_url(url: str) -> str:
    """Hide password in connection string for logs."""
    if "@" not in url:
        return url
    prefix, host_part = url.rsplit("@", 1)
    if "://" in prefix:
        scheme, creds = prefix.split("://", 1)
        if ":" in creds:
            user = creds.split(":", 1)[0]
            return f"{scheme}://{user}:****@{host_part}"
    return f"****@{host_part}"


def verify_connection() -> tuple[bool, str]:
    """Run a simple query and return PostgreSQL version."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            version = connection.execute(text("SELECT version()")).scalar_one()
        return True, str(version)
    except Exception as exc:
        return False, str(exc)


def run_migrations() -> None:
    alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(alembic_cfg, "head")


def verify_tables() -> tuple[list[str], list[str]]:
    """Return (existing expected tables, missing expected tables)."""
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    missing = [name for name in EXPECTED_TABLES if name not in existing]
    present = [name for name in EXPECTED_TABLES if name in existing]
    return present, missing


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify PostgreSQL connection and create database tables."
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only verify connection and tables; do not run migrations.",
    )
    args = parser.parse_args()

    print("Transaction Pipeline — database setup")
    print(f"Database URL: {mask_database_url(settings.database_url)}")
    print()

    print("Step 1/3: Verifying PostgreSQL connection...")
    ok, detail = verify_connection()
    if not ok:
        print("FAIL  Could not connect to PostgreSQL.")
        print(f"      Error: {detail}")
        print()
        print("Tips:")
        print("  - Ensure PostgreSQL is running (docker compose up db)")
        print("  - Check DATABASE_URL in .env (use localhost when running locally)")
        return 1

    print("OK    Connected successfully.")
    print(f"      {detail.split(',')[0]}")
    print()

    if not args.check_only:
        print("Step 2/3: Applying Alembic migrations...")
        try:
            run_migrations()
            print("OK    Migrations applied (alembic upgrade head).")
        except Exception as exc:
            print("FAIL  Migration failed.")
            print(f"      Error: {exc}")
            return 1
        print()
    else:
        print("Step 2/3: Skipped (--check-only).")
        print()

    step_label = "Step 3/3" if not args.check_only else "Step 3/3"
    print(f"{step_label}: Verifying application tables...")
    present, missing = verify_tables()

    if missing:
        print("FAIL  Missing tables:")
        for name in missing:
            print(f"      - {name}")
        if present:
            print("      Found:")
            for name in present:
                print(f"      - {name}")
        return 1

    print("OK    All expected tables exist:")
    for name in present:
        print(f"      - {name}")

    print()
    print("Database is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
