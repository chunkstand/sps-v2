# External Integrations

**Analysis Date:** 2026-03-17

## APIs & External Services

**Workflow Orchestration:**
- Temporal - workflow execution for permit cases (`src/sps/workflows/temporal.py`, `src/sps/workflows/worker.py`)
  - SDK/Client: `temporalio` (`pyproject.toml`)
  - Auth: Not detected (address/namespace configured via `SPS_TEMPORAL_ADDRESS`, `SPS_TEMPORAL_NAMESPACE`) (`src/sps/config.py`)

## Data Storage

**Databases:**
- PostgreSQL
  - Connection: `SPS_DB_DSN` or `SPS_DB_HOST`/`SPS_DB_PORT`/`SPS_DB_NAME`/`SPS_DB_USER`/`SPS_DB_PASSWORD` (`src/sps/config.py`)
  - Client: SQLAlchemy + psycopg (`src/sps/db/session.py`, `pyproject.toml`)

**File Storage:**
- S3-compatible object storage (MinIO defaults) (`src/sps/storage/s3.py`, `src/sps/config.py`)
  - Buckets: `SPS_S3_BUCKET_EVIDENCE`, `SPS_S3_BUCKET_RELEASE` (`src/sps/config.py`)
  - Endpoint/Auth: `SPS_S3_ENDPOINT_URL`, `SPS_S3_ACCESS_KEY`, `SPS_S3_SECRET_KEY`, `SPS_S3_REGION` (`src/sps/config.py`)

**Caching:**
- None detected

## Authentication & Identity

**Auth Provider:**
- Custom JWT validation
  - Implementation: PyJWT verification of issuer/audience/expiry (`src/sps/auth/identity.py`)
  - Config: `SPS_AUTH_JWT_ISSUER`, `SPS_AUTH_JWT_AUDIENCE`, `SPS_AUTH_JWT_SECRET`, `SPS_AUTH_JWT_ALGORITHM` (`src/sps/config.py`)
  - Legacy reviewer API key header: `SPS_REVIEWER_API_KEY` (`src/sps/auth/rbac.py`, `src/sps/config.py`)

## Monitoring & Observability

**Error Tracking:**
- None detected

**Logs:**
- Python logging with redaction filter (`src/sps/api/main.py`, `src/sps/logging/redaction.py`)

## CI/CD & Deployment

**Hosting:**
- Not detected

**CI Pipeline:**
- Custom CI policy artifact definitions (`ci/sps/merge-authorization.yaml`)

## Environment Configuration

**Required env vars:**
- `SPS_ENV`, `SPS_LOG_LEVEL` (`src/sps/config.py`)
- `SPS_DB_DSN`, `SPS_DB_HOST`, `SPS_DB_PORT`, `SPS_DB_NAME`, `SPS_DB_USER`, `SPS_DB_PASSWORD` (`src/sps/config.py`)
- `SPS_TEMPORAL_ADDRESS`, `TEMPORAL_ADDRESS`, `SPS_TEMPORAL_NAMESPACE`, `TEMPORAL_NAMESPACE`, `SPS_TEMPORAL_TASK_QUEUE`, `TEMPORAL_TASK_QUEUE` (`src/sps/config.py`)
- `SPS_S3_ENDPOINT_URL`, `SPS_S3_ACCESS_KEY`, `SPS_S3_SECRET_KEY`, `SPS_S3_REGION`, `SPS_S3_BUCKET_EVIDENCE`, `SPS_S3_BUCKET_RELEASE`, `SPS_S3_PRESIGN_EXPIRES_SECONDS` (`src/sps/config.py`)
- `SPS_AUTH_JWT_ISSUER`, `SPS_AUTH_JWT_AUDIENCE`, `SPS_AUTH_JWT_SECRET`, `SPS_AUTH_JWT_ALGORITHM`, `SPS_AUTH_MTLS_SIGNAL_HEADER` (`src/sps/config.py`)
- `SPS_REVIEWER_API_KEY` (`src/sps/config.py`)
- `SPS_SPEC_VERSION`, `SPS_APP_VERSION`, `SPS_SCHEMA_VERSION`, `SPS_MODEL_VERSION`, `SPS_POLICY_BUNDLE_VERSION`, `SPS_INVARIANT_PACK_VERSION`, `SPS_ADAPTER_VERSIONS` (`src/sps/config.py`)

**Secrets location:**
- Environment variables or `.env`-style files; `.env.example` present for reference (contents not read) (`src/sps/config.py`, `.env.example`)

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected

---

*Integration audit: 2026-03-17*
