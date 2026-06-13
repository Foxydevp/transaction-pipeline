from pathlib import Path

import pandas as pd
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.core.constants import ALL_CSV_COLUMNS, REQUIRED_CSV_COLUMNS


class CSVValidator:
    """Validates uploaded CSV structure and content."""

    @staticmethod
    def validate_extension(filename: str) -> None:
        if not filename.lower().endswith(".csv"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only CSV files are accepted",
            )

    @staticmethod
    def validate_columns(df: pd.DataFrame) -> None:
        columns = {col.strip().lower() for col in df.columns}
        missing = REQUIRED_CSV_COLUMNS - columns
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required columns: {sorted(missing)}",
            )

        unknown = columns - ALL_CSV_COLUMNS
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown columns: {sorted(unknown)}",
            )

    @staticmethod
    def validate_not_empty(df: pd.DataFrame) -> None:
        if df.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV file contains no data rows",
            )

    @classmethod
    def validate_dataframe(cls, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = [col.strip().lower() for col in df.columns]
        cls.validate_columns(df)
        cls.validate_not_empty(df)

        return df

    @classmethod
    async def validate_upload(cls, file: UploadFile) -> tuple[pd.DataFrame, bytes]:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required",
            )

        cls.validate_extension(file.filename)
        content = await file.read()

        if len(content) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds {settings.max_upload_size_mb}MB limit",
            )

        if not content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty",
            )

        try:
            df = pd.read_csv(pd.io.common.BytesIO(content))
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid CSV format: {exc}",
            ) from exc

        df = cls.validate_dataframe(df)
        return df, content


class FileStorageService:
    """Persists uploaded files to disk."""

    def __init__(self, upload_dir: Path | None = None) -> None:
        self.upload_dir = upload_dir or settings.upload_dir

    def ensure_directory(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save(self, job_id: str, filename: str, content: bytes) -> Path:
        self.ensure_directory()
        safe_name = Path(filename).name
        destination = self.upload_dir / f"{job_id}_{safe_name}"
        destination.write_bytes(content)
        return destination
