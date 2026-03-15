---
id: T03
parent: S02
milestone: M001-r2v2t3
provides:
  - Evidence registry API routes wired to Postgres + MinIO
  - DB migration adding evidence content metadata fields (bytes/type)
  - End-to-end integration tests proving register → upload → metadata → download roundtrip
key_files:
  - src/sps/api/routes/evidence.py
  - src/sps/api/main.py
  - src/sps/db/models.py
  - alembic/versions/c1fc8c772c8d_evidence_content_metadata.py
  - tests/s02_evidence_roundtrip_test.py
key_decisions:
  - "Register requires expected checksum (sha256:<hex>) up front; upload rejects mismatches and records content_bytes/content_type"
patterns_established:
  - "Evidence API under /api/v1 with deterministic storage_uri derived from stable ID"
observability_surfaces:
  - "./.venv/bin/pytest -q tests/s02_evidence_roundtrip_test.py"
duration: 90m
verification_result: passed
completed_at: 2026-03-15T21:45:00Z
blocker_discovered: false
---

# T03: Add evidence registry API routes and integration test

**Implemented the evidence registry API (Postgres + MinIO) and proved end-to-end evidence content roundtrip by stable ID.**

## What Happened
- Extended the `evidence_artifacts` persistence model to capture content metadata:
  - `content_bytes`, `content_type`
  - shipped an Alembic migration and applied it locally.
- Implemented FastAPI evidence routes under `/api/v1`:
  - `POST /api/v1/evidence/artifacts` — register metadata + expected checksum, server assigns `artifact_id` and deterministic `storage_uri`
  - `PUT /api/v1/evidence/artifacts/{id}/content` — upload bytes to MinIO, reject sha mismatch, persist bytes/type
  - `GET /api/v1/evidence/artifacts/{id}` — fetch metadata
  - `GET /api/v1/evidence/artifacts/{id}/download` — presigned URL
- Added `tests/s02_evidence_roundtrip_test.py` proving:
  - register → upload → fetch → download works against real docker-compose Postgres + MinIO
  - sha mismatch uploads are rejected (fail closed)
- Added `httpx` to dev deps (required for `fastapi.testclient`).

## Verification
- `docker compose up -d postgres minio minio-init`
- `./.venv/bin/alembic upgrade head`
- `./.venv/bin/pytest -q tests/s02_evidence_roundtrip_test.py` → 2 passed

## Diagnostics
- Run the API: `./.venv/bin/uvicorn sps.api.main:app`
- MinIO console: http://localhost:9001

## Deviations
- None.

## Known Issues
- None.

## Files Created/Modified
- `src/sps/db/models.py` — added evidence content metadata fields.
- `alembic/versions/c1fc8c772c8d_evidence_content_metadata.py` — migration.
- `src/sps/api/routes/evidence.py` — evidence registry endpoints.
- `src/sps/api/main.py` — router included.
- `tests/s02_evidence_roundtrip_test.py` — end-to-end integration tests.
- `pyproject.toml` — added `httpx` to dev deps.
