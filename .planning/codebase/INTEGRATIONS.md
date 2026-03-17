# External Integrations

**Analysis Date:** 2026-03-17

## APIs & External Services

**Workflow Orchestration:**
- Temporal - workflow execution and signaling
  - SDK/Client: `temporalio` in `pyproject.toml` and `src/sps/workflows/temporal.py`
  - Auth: address/namespace via `SPS_TEMPORAL_ADDRESS`, `SPS_TEMPORAL_NAMESPACE` in `src/sps/config.py`

**Object Storage:**
- S3-compatible storage (MinIO in local dev) - evidence and release bundles
  - SDK/Client: `boto3` in `pyproject.toml` and `src/sps/storage/s3.py`
  - Auth: `SPS_S3_ACCESS_KEY`, `SPS_S3_SECRET_KEY` in `src/sps/config.py`

## Data Storage

**Databases:**
- PostgreSQL
  - Connection: `SPS_DB_DSN` or `SPS_DB_HOST`/`SPS_DB_PORT`/`SPS_DB_NAME`/`SPS_DB_USER`/`SPS_DB_PASSWORD` in `src/sps/config.py`
  - Client: SQLAlchemy + psycopg in `src/sps/db/session.py` and `pyproject.toml`

**File Storage:**
- S3-compatible storage (evidence + release buckets) in `src/sps/storage/s3.py`

**Caching:**
- None detected in `src/`

## Authentication & Identity

**Auth Provider:**
- Custom JWT auth (HS256) using PyJWT
  - Implementation: token validation in `src/sps/auth/identity.py`, guards in `src/sps/auth/rbac.py`

## Monitoring & Observability

**Error Tracking:**
- None detected in `src/`

**Logs:**
- Standard logging with redaction hook in `src/sps/api/main.py` and `src/sps/logging/redaction.py`

## CI/CD & Deployment

**Hosting:**
- Not detected

**CI Pipeline:**
- GitHub Actions in `.github/workflows/ci.yml`

## Environment Configuration

**Required env vars:**
- `SPS_DB_DSN`, `SPS_DB_HOST`, `SPS_DB_PORT`, `SPS_DB_NAME`, `SPS_DB_USER`, `SPS_DB_PASSWORD` in `src/sps/config.py`
- `SPS_TEMPORAL_ADDRESS`, `SPS_TEMPORAL_NAMESPACE`, `SPS_TEMPORAL_TASK_QUEUE` in `src/sps/config.py`
- `SPS_S3_ENDPOINT_URL`, `SPS_S3_ACCESS_KEY`, `SPS_S3_SECRET_KEY`, `SPS_S3_REGION` in `src/sps/config.py`
- `SPS_S3_BUCKET_EVIDENCE`, `SPS_S3_BUCKET_RELEASE`, `SPS_S3_PRESIGN_EXPIRES_SECONDS` in `src/sps/config.py`
- `SPS_AUTH_JWT_ISSUER`, `SPS_AUTH_JWT_AUDIENCE`, `SPS_AUTH_JWT_SECRET`, `SPS_AUTH_JWT_ALGORITHM` in `src/sps/config.py`
- `SPS_AUTH_MTLS_SIGNAL_HEADER`, `SPS_REVIEWER_API_KEY` in `src/sps/config.py`

**Secrets location:**
- Environment variables (example file present: `.env.example`)

## Webhooks & Callbacks

**Incoming:**
- Not detected (workflow signals are internal in `src/sps/workflows/permit_case/workflow.py`)

**Outgoing:**
- None detected in `src/`

---

*Integration audit: 2026-03-17*
