---
id: T02
parent: S02
milestone: M001-r2v2t3
provides:
  - S3-compatible storage adapter wired for local MinIO (put/head/presign)
  - Integrity enforcement (sha256 + bytes) at upload boundary
  - Adapter integration tests against docker-compose MinIO
key_files:
  - src/sps/storage/s3.py
  - src/sps/config.py
  - tests/s02_storage_adapter_test.py
  - pyproject.toml
key_decisions:
  - "Use boto3 with explicit endpoint_url for MinIO compatibility"
patterns_established:
  - "Storage adapter raises typed errors (StorageError/IntegrityError) and never logs secrets"
observability_surfaces:
  - "./.venv/bin/pytest -q tests/s02_storage_adapter_test.py"
duration: 45m
verification_result: passed
completed_at: 2026-03-15T21:25:00Z
blocker_discovered: false
---

# T02: Implement S3-compatible storage adapter (MinIO)

**Implemented an S3-compatible storage adapter (MinIO) with presigned download URLs and integrity checks.**

## What Happened
- Extended `sps.config.Settings` with S3/MinIO config (endpoint URL, creds, buckets, presign expiry) matching `.env.example` naming.
- Added `src/sps/storage/s3.py` adapter:
  - `ensure_bucket()`
  - `put_bytes()` with sha256 + byte-length enforcement
  - `head()`
  - `presign_get()`
- Added integration tests in `tests/s02_storage_adapter_test.py` that run against docker-compose MinIO.

## Verification
- Brought up MinIO: `docker compose up -d minio minio-init`
- Ran: `./.venv/bin/pytest -q tests/s02_storage_adapter_test.py` → 2 passed.

## Diagnostics
- MinIO console: http://localhost:9001
- Buckets: `sps-evidence`, `sps-release`

## Deviations
- None.

## Known Issues
- None.

## Files Created/Modified
- `pyproject.toml` — added `boto3`.
- `src/sps/config.py` — added S3/MinIO settings.
- `src/sps/storage/s3.py` — storage adapter.
- `tests/s02_storage_adapter_test.py` — adapter integration tests.
