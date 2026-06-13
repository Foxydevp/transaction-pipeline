from uuid import uuid4

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.constants import JobStatus
from app.schemas import (
    JobCreateResponse,
    JobListResponse,
    JobResultsResponse,
    JobStatusResponse,
)
from app.services.csv_validator import CSVValidator, FileStorageService
from app.services.job_service import JobService
from app.worker.tasks import process_transaction_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post(
    "/upload",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload CSV and enqueue processing job",
)
async def upload_job(
    file: UploadFile = File(..., description="Transaction CSV file"),
    db: Session = Depends(get_db),
) -> JobCreateResponse:
    df, content = await CSVValidator.validate_upload(file)
    storage = FileStorageService()
    filename = file.filename or "upload.csv"
    job_id = str(uuid4())
    file_path = storage.save(job_id, filename, content)

    job = JobService(db).create_job(
        job_id=job_id,
        filename=filename,
        file_path=file_path,
        row_count_raw=len(df),
    )

    process_transaction_job.delay(job.id)

    return JobCreateResponse(job_id=job.id, status=job.status)


@router.get(
    "/{job_id}/status",
    response_model=JobStatusResponse,
    summary="Get job processing status",
)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
) -> JobStatusResponse:
    return JobService(db).get_status(job_id)


@router.get(
    "/{job_id}/results",
    response_model=JobResultsResponse,
    summary="Get processed job results",
)
def get_job_results(
    job_id: str,
    db: Session = Depends(get_db),
) -> JobResultsResponse:
    return JobService(db).get_results(job_id)


@router.get(
    "",
    response_model=JobListResponse,
    summary="List jobs with optional status filter",
)
def list_jobs(
    status_filter: JobStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
) -> JobListResponse:
    jobs, total = JobService(db).list_jobs(status=status_filter)
    return JobListResponse(
        jobs=JobService.to_list_items(jobs),
        total=total,
    )
