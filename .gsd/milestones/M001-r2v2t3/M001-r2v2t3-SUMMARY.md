---
id: M001-r2v2t3
provides:
  - Phase 1 authoritative Postgres schema + migrations for core SPS entities
  - Evidence registry with stable artifact IDs, deterministic object key layout, and S3-compatible storage binding w/ integrity checks
  - Retention/legal-hold persistence + INV-004 enforcement guardrails (fail-closed) for destructive evidence operations
key_decisions:
  - "Evidence stable IDs: ART-<ULID>; object key: evidence/<ULID[:2]>/<artifact_id>"
  - "Alembic env derives DB URL from sps.config.Settings (no DSN in alembic.ini)"
  - "Phase 1 /readyz is lightweight (no DB probe) to avoid coupling boot to infra availability"
  - "Deny destructive ops under hold with invariant metadata (INV-004 + operation + artifact_id + hold_id)"
patterns_established:
  - "Single source of truth config: Settings drives runtime + migrations + tests"
  - "InvariantDenied -> HTTP 423 with structured denial payload"
  - "Register with expected sha256; upload rejects mismatches; persist bytes/type"
observability_surfaces:
  - /healthz
  - /readyz
  - "./.venv/bin/alembic upgrade head && ./.venv/bin/alembic current"
  - "./.venv/bin/pytest -q tests/s01_db_schema_test.py"
  - "./.venv/bin/pytest -q tests/s02_evidence_roundtrip_test.py"
  - "./.venv/bin/pytest -q tests/s03_legal_hold_test.py"
requirement_outcomes:
  - id: R001
    from_status: active
    to_status: validated
    proof: "docker-compose Postgres + alembic upgrade head + tests/s01_db_schema_test.py passing"
  - id: R002
    from_status: active
    to_status: validated
    proof: "MinIO-backed storage adapter tests + end-to-end register/upload/fetch/download evidence roundtrip tests passing"
  - id: R003
    from_status: active
    to_status: validated
    proof: "legal hold bindings + INV-004 guard + tests/s03_legal_hold_test.py proving denial + purge exclusion"
duration: 7h
verification_result: passed
completed_at: 2026-03-15T21:39:51Z
---

# M001-r2v2t3: Phase 1 — authoritative data foundations

**Authoritative Postgres persistence + evidence registry (Postgres+MinIO) with stable IDs and integrity checks, plus legal-hold (INV-004) guardrails that fail closed.**

## What Happened

This milestone established the Phase 1 “authority substrate” that everything else in SPS depends on:

- **Durable authoritative persistence**: a Phase 1 Postgres schema with Alembic migrations and SQLAlchemy models for the core entities (PermitCase/Project/review records/contradictions/transition ledger/evidence metadata).
- **Evidence registry wired end-to-end**: a FastAPI evidence registry that registers artifact metadata with stable IDs and stores/retrieves content via an S3-compatible backend (MinIO), enforcing **sha256 integrity** at upload time.
- **Compliance guardrails for retention**: legal-hold records + bindings persisted in Postgres, and an INV-004 enforcement guard that **denies destructive evidence operations** under active hold with structured diagnostic detail. A conservative dry-run purge evaluator never marks held evidence as eligible.

Across slices, the work intentionally prioritized “real wiring” (Postgres + MinIO) and stable identifiers over deeper normalization or workflow complexity.

## Cross-Slice Verification

Milestone success criteria and definition-of-done signals were re-verified against live behavior:

1) **Migrations apply cleanly against local Postgres**
- `docker compose up -d postgres`
- `./.venv/bin/alembic upgrade head` (no errors)
- `./.venv/bin/alembic current` → `a06baa922883 (head)`
- `./.venv/bin/pytest -q tests/s01_db_schema_test.py` → pass

2) **Evidence artifacts can be registered/retrieved by stable ID; content in S3-compatible storage with integrity checks**
- `docker compose up -d postgres minio minio-init`
- `./.venv/bin/pytest -q tests/s02_storage_adapter_test.py` → pass
- `./.venv/bin/pytest -q tests/s02_evidence_roundtrip_test.py` → pass (register → upload → fetch → presigned download)

3) **Legal hold prevents purge/destructive delete with clear failure reason (INV-004)**
- `./.venv/bin/pytest -q tests/s03_legal_hold_test.py` → pass (held artifacts denied; purge evaluator excludes held artifacts)

4) **Real runtime entrypoint exists and is exercised**
- `./.venv/bin/uvicorn sps.api.main:app` and:
  - `curl -sf http://127.0.0.1:8000/healthz` → `{"status":"ok"}`
  - `curl -sf http://127.0.0.1:8000/readyz` → `{"status":"ok","env":"local"}`

## Requirement Changes

- R001: active → validated — `alembic upgrade head` against docker-compose Postgres + `tests/s01_db_schema_test.py` passing.
- R002: active → validated — MinIO-backed adapter tests + end-to-end evidence roundtrip tests passing.
- R003: active → validated — hold persistence + INV-004 guard + denial and purge exclusion tests passing.

## Forward Intelligence

### What the next milestone should know
- Docker Postgres init scripts only run on fresh volumes; if you touch init SQL, you often need `docker compose down -v`.
- Evidence ID format + S3 key layout are now compatibility surfaces; treat them as stable.
- Hold enforcement is defined by hold records + bindings (ACTIVE), not by legacy boolean flags; keep enforcement centralized (guard) as destructive purge gets implemented later.

### What's fragile
- S3 client behavior and presigned URL semantics can drift with dependency updates; keep adapter tests (and MinIO integration) as the first failure signal.

### Authoritative diagnostics
- `./.venv/bin/alembic current` — confirms migration head is applied.
- `./.venv/bin/pytest -q tests/s02_evidence_roundtrip_test.py` — quickest end-to-end proof (Postgres+MinIO).
- `./.venv/bin/pytest -q tests/s03_legal_hold_test.py` — proves INV-004 denial semantics and purge exclusion.

### What assumptions changed
- "We can enforce legal hold with a boolean" — replaced with durable hold records + bindings so holds are auditable and queryable.

## Files Created/Modified

- `src/sps/api/main.py` — FastAPI entrypoint + `/healthz` + `/readyz`.
- `src/sps/config.py` — env-backed settings + DSN redaction.
- `src/sps/db/models.py` — Phase 1 SQLAlchemy models (including legal hold tables).
- `alembic/` — authoritative migrations.
- `src/sps/api/routes/evidence.py` — evidence registry endpoints.
- `src/sps/storage/s3.py` — S3/MinIO adapter with sha256 integrity enforcement.
- `src/sps/retention/guard.py` — INV-004 guard.
- `src/sps/retention/purge.py` — dry-run purge evaluator.
- `tests/s01_db_schema_test.py` — Postgres-backed schema tests.
- `tests/s02_evidence_roundtrip_test.py` — end-to-end evidence roundtrip tests.
- `tests/s03_legal_hold_test.py` — legal hold enforcement tests.
