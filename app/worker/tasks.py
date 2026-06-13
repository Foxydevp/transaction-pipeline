import logging

from app.core.database import SessionLocal
from app.services.job_service import PipelineService
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="process_transaction_job",
    bind=True,
    max_retries=0,
    autoretry_for=(),
)
def process_transaction_job(self, job_id: str) -> dict:
    logger.info("Starting pipeline for job %s", job_id)
    db = SessionLocal()
    try:
        PipelineService(db).process_job(job_id)
        logger.info("Completed pipeline for job %s", job_id)
        return {"job_id": job_id, "status": "completed"}
    except Exception as exc:
        logger.exception("Pipeline failed for job %s: %s", job_id, exc)
        raise
    finally:
        db.close()
