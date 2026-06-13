# AI-Powered Transaction Processing Pipeline

Production-ready backend for ingesting transaction CSV files, cleaning and validating data, detecting anomalies, classifying transactions with an LLM (Groq/Llama-3), and returning structured analytics.

## Stack

| Component | Technology |
|-----------|------------|
| API | FastAPI |
| Database | PostgreSQL + SQLAlchemy |
| Migrations | Alembic |
| Task Queue | Celery + Redis |
| Data Processing | Pandas |
| LLM | Groq Cloud (Llama-3.3) |
| Containers | Docker + Docker Compose |

## Architecture

```text
Client
  │
  ▼
FastAPI (POST /jobs/upload)
  │
  ├── Validate CSV
  ├── Store file
  ├── Create Job (pending)
  └── Enqueue Celery task
         │
         ▼
Celery Worker Pipeline
  ├── Read CSV
  ├── Clean & normalize
  ├── Anomaly detection
  ├── Groq batch classification
  ├── Narrative summary (retry w/ backoff)
  └── Persist results
         │
         ▼
PostgreSQL (jobs, transactions, job_summaries)
```

## Project Structure

```
transaction-pipeline/
├── app/
│   ├── api/              # HTTP routes and dependencies
│   ├── core/             # Config, database, constants
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic request/response models
│   ├── services/         # Business logic
│   ├── worker/           # Celery app and tasks
│   └── main.py           # FastAPI application
├── alembic/              # Database migrations
├── sample_data/          # Example CSV for testing
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
```

Set your Groq API key in `.env`:

```
GROQ_API_KEY=your_actual_key_here
```

### 2. Start services

```bash
docker compose up --build
```

Services:

- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

Migrations run automatically on API startup.

### 3. Upload a CSV

```bash
curl -X POST "http://localhost:8000/api/v1/jobs/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample_data/transactions.csv"
```

Response:

```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Job accepted for processing"
}
```

### 4. Poll job status

```bash
curl "http://localhost:8000/api/v1/jobs/{job_id}/status"
```

Statuses: `pending` → `processing` → `completed` | `failed`

### 5. Fetch results

```bash
curl "http://localhost:8000/api/v1/jobs/{job_id}/results"
```

Returns cleaned transactions, anomalies, category breakdown, and LLM summary.

### 6. List jobs

```bash
curl "http://localhost:8000/api/v1/jobs"
curl "http://localhost:8000/api/v1/jobs?status=completed"
```

## CSV Format

Required columns:

| Column | Description |
|--------|-------------|
| `txn_id` | Unique transaction identifier |
| `date` | Transaction date (multiple formats supported) |
| `merchant` | Merchant name |
| `amount` | Amount (supports `$` prefix and commas) |
| `currency` | Currency code (e.g. INR, USD) |
| `status` | Transaction status |
| `account_id` | Account identifier |

Optional: `category`

## Processing Pipeline

### Data Cleaning

1. Normalize date formats
2. Strip `$` and commas from amounts
3. Uppercase status and currency
4. Fill missing categories with `null` (LLM fills later)
5. Remove duplicate `txn_id` rows

### Anomaly Detection

| Rule | Description |
|------|-------------|
| Amount spike | `amount > 3×` account median |
| Currency mismatch | USD used with Swiggy, Ola, or IRCTC |

### LLM Classification

Groq (Llama-3.3-70b) classifies transactions into:
Food, Shopping, Travel, Transport, Utilities, Cash Withdrawal, Entertainment, Other

- Batch requests to maximize throughput and prevent rate limits
- Enforced strict JSON mode for guaranteed parsing
- 3 retries with exponential backoff on failure

### Narrative Summary

Returns structured JSON:

```json
{
  "total_spend_by_currency": {"INR": 12345.67},
  "top_merchants": [{"merchant": "Amazon", "total_amount": 2500}],
  "anomaly_count": 2,
  "narrative": "...",
  "risk_level": "medium"
}
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/jobs/upload` | Upload CSV, enqueue job |
| GET | `/api/v1/jobs/{job_id}/status` | Job status |
| GET | `/api/v1/jobs/{job_id}/results` | Processed results |
| GET | `/api/v1/jobs?status=` | List jobs |

## Local Development (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Start PostgreSQL and Redis locally, then:
export DATABASE_URL=postgresql+psycopg2://root:root@localhost:5432/transactions
export REDIS_URL=redis://localhost:6379/0
export CELERY_BROKER_URL=redis://localhost:6379/0
export GROQ_API_KEY=your_key

alembic upgrade head
uvicorn app.main:app --reload
celery -A app.worker.celery_app worker --loglevel=info
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `REDIS_URL` | — | Redis URL |
| `CELERY_BROKER_URL` | — | Celery broker |
| `CELERY_RESULT_BACKEND` | — | Celery result backend |
| `GROQ_API_KEY` | — | Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Model name |
| `GROQ_MAX_RETRIES` | `3` | Retry count |
| `GROQ_BATCH_SIZE` | `20` | Transactions per LLM batch |
| `UPLOAD_DIR` | `/app/uploads` | File storage path |
| `MAX_UPLOAD_SIZE_MB` | `50` | Max upload size |

## Database Schema

### jobs

Tracks upload and processing lifecycle.

### transactions

Stores cleaned, classified, and anomaly-flagged rows per job.

### job_summaries

Stores aggregated spend, top merchants, narrative, and risk level.

## License

MIT
