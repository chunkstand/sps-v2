---
id: M001-r2v2t3
provides:
  - Authoritative Postgres schema + Alembic migrations for Phase 1 entities
  - Evidence registry API with stable IDs and MinIO-backed content storage
  - Legal-hold guardrails (INV-004) with fail-closed denial surfaces and purge-eligibility exclusion
key_decisions:
  - "Phase 1 stack: FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic + psycopg; MinIO via boto3"
  - "Evidence IDs: ART-<ULID>; object key evidence/<ULID[:2]>/<artifact_id>"
patterns_established:
  - "Alembic derives DB URL from `sps.config.Settings` (no DSN in alembic.ini)"
  - "Integration tests apply migrations in-session and verify real Postgres/MinIO behavior"
observability_surfaces:
  - /healthz
  - /readyz
  - "./.venv/bin/alembic current"
  - "./.venv/bin/pytest -q tests/s01_db_schema_test.py"
  - "./.venv/bin/pytest -q tests/s02_evidence_roundtrip_test.py"
  - "./.venv/bin/pytest -q tests/s03_legal_hold_test.py"
requirement_outcomes:
  - id: R001
    from_status: active
    to_status: validated
    proof: "alembic upgrade head + tests/s01_db_schema_test.py"
  - id: R002
    from_status: active
    to_status: validated
    proof: "tests/s02_storage_adapter_test.py + tests/s02_evidence_roundtrip_test.py"
  - id: R003
    from_status: active
    to_status: validated
    proof: "tests/s03_legal_hold_test.py (deny + purge exclusion)"
duration: 1d
verification_result: passed
completed_at: 2026-03-15T23:20:00Z
---

# M001-r2v2t3: Phase 1 — authoritative data foundations

**Phase 1 now has real authoritative persistence + evidence registry + legal-hold guardrails, all exercised end-to-end against local Postgres + MinIO.**

## What Happened
Across S01–S03, Phase 1 established the durable “authority substrate” needed for later workflow and reviewer gates:
- **S01 (Authoritative schema):** created Phase 1 SQLAlchemy models + Alembic migrations and proved they apply cleanly to docker-compose Postgres, with Postgres-backed smoke/constraint tests.
- **S02 (Evidence registry):** implemented stable evidence IDs and a MinIO-backed storage adapter, then shipped API routes that can register evidence metadata, upload content, fetch metadata, and generate presigned downloads by stable ID.
- **S03 (Legal hold):** added durable legal-hold records + bindings, implemented the INV-004 guard that fails closed, proved destructive delete attempts are denied with invariant metadata, and added a dry-run purge evaluator that never treats held artifacts as purge-eligible.

## Cross-Slice Verification
- Postgres migrations + schema integrity:
  - `docker compose up -d postgres`
  - `./.venv/bin/alembic upgrade head`
  - `./.venv/bin/pytest -q tests/s01_db_schema_test.py`
- Evidence roundtrip (Postgres + MinIO):
  - `docker compose up -d postgres minio minio-init`
  - `./.venv/bin/pytest -q tests/s02_evidence_roundtrip_test.py`
- Legal hold enforcement (INV-004):
  - `./.venv/bin/pytest -q tests/s03_legal_hold_test.py`

## Requirement Changes
- R001: active → validated — `alembic upgrade head` + `tests/s01_db_schema_test.py`
- R002: active → validated — `tests/s02_storage_adapter_test.py` + `tests/s02_evidence_roundtrip_test.py`
- R003: active → validated — `tests/s03_legal_hold_test.py`

## Forward Intelligence
### What the next milestone should know
- This milestone intentionally leaves auth/access control out; later phases should treat Phase 1 APIs as internal/dev-only until governance controls are introduced.
- INV-004 enforcement is centralized in `sps.retention.guard.assert_not_on_legal_hold()`; keep destructive purge/delete paths routed through it.

### What's fragile
- Stable ID and object key layout choices are long-term compatibility surfaces. Avoid changing `ART-<ULID>` and `evidence/<ULID[:2]>/<artifact_id>` without an explicit migration strategy.

### Authoritative diagnostics
- `pytest -q tests/s02_evidence_roundtrip_test.py` is the quickest end-to-end sanity check across Postgres + MinIO.

### What assumptions changed
- "Local Postgres init scripts are fine" — fixed init SQL because `CREATE DATABASE` cannot run inside a DO block.
