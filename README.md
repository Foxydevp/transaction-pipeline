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
**[🔍 View the High-Level System Architecture Diagram (draw.io)](https://viewer.diagrams.net/?tags=%7B%7D&lightbox=1&highlight=0000ff&edit=_blank&layers=1&nav=1&dark=auto#R%3Cmxfile%3E%3Cdiagram%20name%3D%22Page-1%22%20id%3D%228wV1R4KSiYlsP4pSgbRC%22%3EzVnbcuI4EP0aqpKHoXwBA48JucxskQkTZze7T1vClrE3suWR5QHy9duSZSNjhyEEKJIqYreklnTOUas7dOxxvLxnKA0fqI9JxzL8Zce%2B6VjWYGTDpzCsCoPZGw4Ky5xFvrKtDW70hpXRUNY88nFW68gpJTxK60aPJgn2eM2GGKOLereAkvqsKZrjhsH1EGlaXyKfh4V12DfW9q84moflzKahWmJUdlaGLEQ%2BXWgm%2B7ZjjxmlvHiKl2NMBHglLsW4u3daq4UxnPBdBngkEj0bo5SjjK%2FKPTOaJz4Ww8yOfb0II47dFHmidQEsgy3kMVHNQUTImBLK5FjbR3gYeGDPOKOvWGtxvCGeBdBSzPcLkVzN17EcAou5nsHDXDyM1VILM2ypaqm6stJy4f35NOmIvd%2FB5x2jCceJf6kmwYzjpbZPBc09pjHmbAVdQo09R1G1WDNtlvQpLz31qvRslXQjpbN55XlNBTwoNtqZQWl0dFr6eOj32mgZWjPbcXai5Q5l%2FGr6DXpdvGCwGi5mgPDlbkR9gQFfUeITOM7w9Pw8FRAkc4azrL33XQRbl0uKfMQjmuxF6rCFVKdOqr3Bqjk8AKsM%2B1G2C68QGFLx6K1IBAQz%2B%2FfszgopTGaVAXmvcymQx5yDG6zsWRFQzX5TEkGAHa%2F1pPqD0Qx0vYsknopNGhcPwKIIpZZxLbx9SBQQk4UPjrJX%2BPMzxzBda88b7NE8LQRUCBFaUZxK18YLZTDxsTTS39BI7wASWWgrPt7ZD4LAeodoZ%2Bb0xdmHEzZPwEZwILDOwDWczIl8uzF3kwLsDUtgL66yVeJphBjfIS3YKoiwotnsQv8phAmB65Ucy2JY3puQFkQByb3OupczAM5bNRVjCVcP8hoWjuyleAW9IogjhjwmcnE3mEPiIKPLpgdbeHjGCaDBV4WXR%2BaFGICElVQifALeI5ztpbwqX9CkZ1nbpVdJ8zPaIyQ%2BuvD64rc1F5A%2FBxLePaM%2FocuY0NwvOdkpc5gQFKMvdte%2BbOpQhBsXaIWU0jL%2BcB%2B%2FF5pJc94emq4R90KxChDGnLLoDbVLSvT9DokpNP8SCnLzOEaKuUNop7q6lJuReYSrzZ%2Bd8b2GTUh2Bm2qGzkDGx1KdVOacchd3B8i%2BbxBHM1QhneLcUID%2F9GZvDdTSFZh7iqBTRn14CrVTR6N4c7j2L9slxMEoyRDMoRJlx7BKMG%2B5GdFKHpvHCzh30zKb%2B%2Fg1WsJXr%2FJrezBAQSIldqw36jemoqkOfNwswbSlCrcuOqVMh7SOU0QuV1br%2BthUFMsXkb8b%2B35H3g2upbQJczEVqLNKF%2B0xmINHLE55htVgKa64jZ8dJ8LMUDuA3SKKOP%2B1c4Ow6SILLU6%2BDNIW%2FshXe3msDAbNZgHNZjNOsyyEdKIsPLXxFzXgwa7zBzgVs9Zos4JwHEivO3zwltJWUFu1mTdNfs1yFshLu8KDV6ZVn1LMgg24nKlopS8mBaB8PJUOPfODGcdZmNL9GgPHlqxqQHdk%2BEjn5EoE7nJsyywTgNvfz94tX0cE%2BANHe8gY71U0xDuC4THcPHmMT4xws5%2BCOsbObcrsKpJNISdrpZdTyYPMscWSJwG5cF%2BKFc7Oevr7x1RD7rrmqesZ4oM8RSID89N11tDx3C%2FK3AoVZ2TV%2F0mFFXEqVAe7Yfy8RLobSi3KLuJclv%2BPBIw39%2Bq9JnhLCf8s0KWQ6%2Bggl9pHVIaJTXPU2FYV0FVqV5WQZtf1mz03%2Fye4aP9rb6xIYdixWtxVFvfseAyzixfGnzuPm85k6Yh1PIjL%2F6L%2BfRhsSgqjK5tD%2Brkbal4N%2Bgsu9AgyDBvnOitpAmFV98mFt3X38nat%2F8D%3C%2Fdiagram%3E%3C%2Fmxfile%3E)**

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
