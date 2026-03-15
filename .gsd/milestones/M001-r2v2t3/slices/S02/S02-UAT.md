# S02: Evidence registry API + MinIO content roundtrip — UAT

**Milestone:** M001-r2v2t3
**Written:** 2026-03-15

## UAT Type
- UAT mode: live-runtime
- Why this mode is sufficient: the slice is defined by real Postgres + MinIO roundtrip behavior, best proven by integration tests and a minimal curl-based sanity pass.

## Preconditions
- Docker Desktop running
- Dependencies installed: `./.venv/bin/python -m pip install -e ".[dev]"`

## Smoke Test
1. `docker compose up -d postgres minio minio-init`
2. `./.venv/bin/alembic upgrade head`
3. `./.venv/bin/pytest -q tests/s02_evidence_roundtrip_test.py`
4. **Expected:** tests pass.

## Test Cases

### 1. Evidence roundtrip via API
1. `docker compose up -d postgres minio minio-init`
2. `./.venv/bin/uvicorn sps.api.main:app`
3. In another shell, run a minimal register+upload (or just rely on pytest).
4. **Expected:** evidence is retrievable by stable ID and download returns content.

### 2. Sha mismatch fails closed
1. Run: `./.venv/bin/pytest -q tests/s02_evidence_roundtrip_test.py::test_evidence_upload_rejects_sha_mismatch`
2. **Expected:** test passes; upload returns 422.

## Edge Cases

### Bucket missing
1. Stop and delete MinIO volume: `docker compose down -v`
2. Restart: `docker compose up -d minio minio-init`
3. **Expected:** buckets are recreated and tests still pass.

## Failure Signals
- `docker compose ps` shows minio/postgres exited
- `pytest` failures in `tests/s02_*`
- MinIO console shows no objects after upload (http://localhost:9001)

## Requirements Proved By This UAT
- R002 — Evidence registry by stable ID with object storage binding and integrity enforcement.

## Not Proven By This UAT
- R003 — Legal hold prevents purge/destructive delete (S03)

## Notes for Tester
- This slice intentionally has no auth; treat endpoints as internal/dev-only until governance controls land.
