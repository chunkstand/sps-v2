---
id: S02
parent: M001-r2v2t3
milestone: M001-r2v2t3
provides:
  - Evidence registry endpoints wired to Postgres + MinIO
  - Stable evidence IDs + deterministic object key layout
  - S3 adapter with integrity enforcement and presigned downloads
requires:
  - slice: S01
    provides: Postgres schema/migrations and DB session wiring
affects:
  - S03
key_files:
  - src/sps/evidence/ids.py
  - src/sps/evidence/models.py
  - src/sps/storage/s3.py
  - src/sps/api/routes/evidence.py
  - src/sps/db/models.py
  - tests/s02_storage_adapter_test.py
  - tests/s02_evidence_roundtrip_test.py
key_decisions:
  - "Evidence stable IDs: ART-<ULID>; object key: evidence/<ULID[:2]>/<artifact_id>"
patterns_established:
  - "Register with expected sha256; upload rejects mismatches; persist bytes/type"
observability_surfaces:
  - "./.venv/bin/pytest -q tests/s02_evidence_roundtrip_test.py"
drill_down_paths:
  - .gsd/milestones/M001-r2v2t3/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001-r2v2t3/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M001-r2v2t3/slices/S02/tasks/T03-SUMMARY.md
duration: 3h
verification_result: passed
completed_at: 2026-03-15T22:00:00Z
---

# S02: Evidence registry API + MinIO content roundtrip

**Shipped an evidence registry that can register metadata, upload content to MinIO, and retrieve evidence by stable ID end-to-end.**

## What Happened
- Implemented evidence stable IDs + deterministic object key layout.
- Added an S3-compatible storage adapter (MinIO) with presigned downloads and integrity enforcement.
- Implemented evidence registry API endpoints under `/api/v1` and proved:
  - register → upload → fetch metadata → download works against real Postgres + MinIO
  - sha mismatches fail closed
- Extended the DB schema to store evidence content metadata (`content_bytes`, `content_type`).

## Verification
- `docker compose up -d postgres minio minio-init`
- `./.venv/bin/alembic upgrade head`
- `./.venv/bin/pytest -q tests/s02_storage_adapter_test.py`
- `./.venv/bin/pytest -q tests/s02_evidence_roundtrip_test.py`

## Requirements Advanced
- R002 — Evidence registry exists and is wired to real object storage; artifacts are retrievable by stable ID.

## Requirements Validated
- R002 — Validated by MinIO-backed adapter tests and end-to-end evidence roundtrip tests.

## New Requirements Surfaced
- (none)

## Requirements Invalidated or Re-scoped
- None.

## Deviations
- Added `content_bytes`/`content_type` columns (and migration) to satisfy the “sha256/bytes correlation” must-have.

## Known Limitations
- No auth or access control yet (Phase 1 focuses on correctness + wiring).
- Download is presigned URL only; no streaming proxy endpoint.

## Follow-ups
- None.

## Files Created/Modified
- `src/sps/api/routes/evidence.py` — evidence registry endpoints.
- `src/sps/storage/s3.py` — MinIO adapter.
- `tests/s02_evidence_roundtrip_test.py` — end-to-end evidence roundtrip.

## Forward Intelligence
### What the next slice should know
- Evidence rows store expected checksum up front; upload is the enforcement point.
- When legal-hold is implemented, it must guard both DB destructive ops and any object deletion path.

### What's fragile
- Any change to ID format or object key layout is a long-term compatibility hazard; treat as stable once released.

### Authoritative diagnostics
- `pytest -q tests/s02_evidence_roundtrip_test.py` is the quickest end-to-end proof.

### What assumptions changed
- "We can validate integrity without storing bytes" — we added `content_bytes` to make integrity checkable in DB.
