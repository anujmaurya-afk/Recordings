# Recording Converter

A production-ready web application for bulk conversion of S3 recording URLs to **presigned S3 URLs** (7-day expiry) or **CloudFront URLs** (30-day expiry).

## Architecture

```
Frontend (React + TypeScript)
   ↓ HTTP polling
Backend (FastAPI + SQLite)
   ↓ asyncio worker pool
Recording Service Adapter
   ├── recordings.py  →  7-day S3 presigned URL (default)
   └── cloudfront.py  →  30-day CloudFront URL (optional)
```

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Copy environment config
copy .env.example .env

# Edit .env with your AWS credentials (see Configuration below)

# Install Python dependencies
pip install -r requirements.txt

# Start the API server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend

# Install Node dependencies
npm install

# Start the dev server
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Configuration

Edit `backend/.env`:

### AWS

```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=ap-south-1
```

### URL Provider

```env
# Default: 7-day S3 presigned URLs
URL_PROVIDER=recordings

# Alternative: CloudFront URLs
# URL_PROVIDER=cloudfront
```

### Presigned URL Expiry

```env
# 604800 seconds = 7 days (S3 maximum)
RECORDING_URL_EXPIRY_SECONDS=604800
```

### CloudFront (optional — for 30-day signed URLs)

```env
CLOUDFRONT_DOMAIN=https://your-distribution.cloudfront.net
CLOUDFRONT_URL_EXPIRY_DAYS=30

# For signed CloudFront URLs (optional — leave empty for unsigned CDN URLs):
CLOUDFRONT_KEY_PAIR_ID=APKAXXXXXXXX
CLOUDFRONT_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----
```

> **Note:** If `CLOUDFRONT_KEY_PAIR_ID` and `CLOUDFRONT_PRIVATE_KEY` are not set, CloudFront URLs will be unsigned (permanent CDN URLs without expiry).

### Worker Concurrency

```env
# Number of simultaneous S3/CloudFront API calls
MAX_WORKERS=5
```

---

## How It Works

### URL Conversion Flow

1. User pastes S3 URLs or uploads a CSV/Excel file
2. Frontend sends URLs to the backend API
3. Backend creates a **job** with a unique `JOB-YYYYMMDD-XXXXXXXX` ID
4. A background worker pool (up to `MAX_WORKERS` concurrent) processes each recording
5. Each URL is passed to `recordings.py` → `generate_presigned_url()` (or `cloudfront.py` → `generate_cloudfront_url()`)
6. Results are stored in SQLite
7. Frontend polls `/api/jobs/{job_id}` every 2 seconds for live progress
8. On completion, results can be downloaded as CSV or Excel

### Presigned URL (7-day, default)

Uses `boto3.client('s3').generate_presigned_url()` with `ExpiresIn=604800` (7 days).

The presigned URL includes an `X-Amz-Signature` that expires in exactly 7 days.

### CloudFront URL (30-day)

If `CLOUDFRONT_KEY_PAIR_ID` and `CLOUDFRONT_PRIVATE_KEY` are configured, uses `botocore.signers.CloudFrontSigner` to create a signed URL with a `date_less_than` policy 30 days from now.

If signing keys are not configured, returns an unsigned CloudFront URL (permanent).

### Duplicate URL Handling

Within a single job, if the same S3 URL appears multiple times, it is converted **only once**. Subsequent rows with the same URL reuse the cached result. This saves API calls and avoids redundant work.

### Failure Isolation

Each recording is processed independently. A failure in one recording (404, auth error, timeout) **never stops** the rest of the job. Failed records are tracked with user-friendly error messages. Use **Retry Failed** to reprocess only failed records.

---

## API Endpoints

Once the backend is running, visit [http://localhost:8000/docs](http://localhost:8000/docs) for interactive Swagger documentation.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/jobs/urls` | Create job from pasted URLs |
| `POST` | `/api/jobs/file` | Create job from uploaded CSV/Excel |
| `GET` | `/api/jobs/{job_id}` | Job status and progress |
| `GET` | `/api/jobs/{job_id}/results` | Paginated results (filterable) |
| `POST` | `/api/jobs/{job_id}/retry` | Retry failed records |
| `GET` | `/api/jobs/{job_id}/download/csv` | Download results as CSV |
| `GET` | `/api/jobs/{job_id}/download/excel` | Download results as Excel |
| `POST` | `/api/parse/csv` | Upload and parse CSV file |
| `POST` | `/api/parse/excel` | Upload and parse Excel file |
| `GET` | `/api/parse/excel/{file_id}/sheet` | Select a sheet in uploaded Excel |
| `GET` | `/health` | Health check |

---

## Input Formats

### S3 HTTPS URLs

```
https://bucket.s3.ap-south-1.amazonaws.com/path/to/recording.wav
https://bucket.s3.amazonaws.com/folder/recording.mp3
```

### S3 URIs

```
s3://bucket-name/path/to/recording.wav
```

### Paste Links

- One URL per line
- Comma-separated
- Mixed is supported

### CSV

Any CSV with a column containing S3 URLs. The application auto-detects likely URL columns (columns named `url`, `link`, `recording`, `audio`, `src`, etc.).

### Excel

Supports `.xlsx` and `.xls`. Select the sheet and URL column before starting conversion.

---

## Running Tests

```bash
cd recording-converter

# From the project root (with backend in PYTHONPATH)
$env:PYTHONPATH="backend"
cd backend
pytest ../tests/ -v
```

---

## Project Structure

```
recording-converter/
│
├── backend/
│   ├── recordings.py          ← Original (patched: env vars)  7-day presigned URLs
│   ├── cloudfront.py          ← Original (patched: env vars + optional signing)
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── main.py            ← FastAPI app
│       ├── config.py          ← Pydantic settings
│       ├── api/
│       │   ├── jobs.py        ← Job CRUD + download endpoints
│       │   └── uploads.py     ← File parse endpoints
│       ├── services/
│       │   ├── recording_service.py   ← Adapter: recordings.py + cloudfront.py
│       │   ├── job_service.py         ← SQLite job/record CRUD
│       │   ├── file_parser.py         ← CSV/Excel streaming parser
│       │   └── url_validator.py       ← URL validation + dedup
│       ├── workers/
│       │   └── conversion_worker.py   ← Async worker pool
│       ├── models/
│       │   └── db.py                  ← SQLite schema + connection
│       └── schemas/
│           └── schemas.py             ← Pydantic request/response schemas
│
├── frontend/
│   └── src/
│       ├── App.tsx
│       ├── pages/
│       │   ├── Home.tsx
│       │   ├── NewJob.tsx
│       │   └── JobDetail.tsx
│       ├── services/api.ts
│       ├── hooks/useJobPolling.ts
│       └── types/index.ts
│
├── tests/
│   ├── test_url_validator.py
│   ├── test_file_parser.py
│   ├── test_recording_service.py
│   └── test_jobs_api.py
│
└── README.md
```

---

## Security Notes

- AWS credentials are **never** exposed to the frontend
- Uploaded files are size-limited (`MAX_FILE_SIZE_MB=50`)
- File extension + MIME validation on uploads
- All user input is validated before processing
- Presigned URLs contain AWS signatures — do not log them in production
- CloudFront private keys are read from environment variables, never hardcoded

---

## Deployment

For production deployment:

1. Set `CORS_ORIGINS` to your frontend domain
2. Use a production WSGI server: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4`
3. Build the frontend: `npm run build` → serve the `dist/` folder via nginx or similar
4. Use a persistent volume for the SQLite database (`DATABASE_PATH`)
5. Store secrets in environment variables or a secrets manager, not `.env` files
