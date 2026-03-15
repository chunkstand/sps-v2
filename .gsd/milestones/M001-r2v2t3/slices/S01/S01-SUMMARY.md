---
id: S01
parent: M001-r2v2t3
milestone: M001-r2v2t3
provides:
  - FastAPI service scaffold with health/readiness endpoints
  - Authoritative Phase 1 Postgres schema + Alembic migrations
  - DB session helpers and Postgres-backed schema smoke/constraint tests
requires: []
affects:
  - S02
  - S03
key_files:
  - pyproject.toml
  - src/sps/config.py
  - src/sps/api/main.py
  - src/sps/db/models.py
  - src/sps/db/session.py
  - alembic/
  - docker/postgres/init/00-init.sql
  - tests/s01_db_schema_test.py
key_decisions:
  - "Keep /readyz lightweight in Phase 1 (no DB probe) to avoid coupling boot to infra availability"
  - "Schema uses stable-ID primary keys (string) consistent with spec examples (CASE-*, ART-*, REV-*)"
  - "Use JSONB for nested/provenance-like structures to avoid premature deep normalization"
patterns_established:
  - "Alembic env derives DB URL from `sps.config.Settings`"
  - "Integration tests run `alembic upgrade head` in a session fixture; per-test TRUNCATE for repeatability"
observability_surfaces:
  - /healthz
  - /readyz
  - "./.venv/bin/alembic current"
  - "./.venv/bin/pytest -q tests/s01_db_schema_test.py"
drill_down_paths:
  - .gsd/milestones/M001-r2v2t3/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001-r2v2t3/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M001-r2v2t3/slices/S01/tasks/T03-SUMMARY.md
duration: 2h
verification_result: passed
completed_at: 2026-03-15T21:31:05Z
---

# S01: Postgres schema + migrations + typed model package

**Shipped a real Phase 1 Postgres schema (migrations + tests) and the minimal service/config scaffold that downstream evidence APIs will build on.**

## What Happened
This slice established the Phase 1 “authority substrate”:

- A minimal FastAPI service entrypoint (`sps.api.main:app`) with `/healthz` and `/readyz`.
- Env-backed settings (`sps.config.Settings`) with safe DSN redaction.
- Phase 1 SQLAlchemy models and Alembic migrations that create the authoritative tables for core SPS entities (PermitCase, Project, ReviewDecision, ContradictionArtifact, transition ledger, evidence metadata, and release metadata).
- Postgres-backed integration tests proving:
  - migrations apply cleanly against `docker compose` Postgres
  - representative inserts/reads succeed
  - FK integrity failures fail closed

## Verification
- `docker compose up -d postgres`
- `./.venv/bin/alembic upgrade head`
- `./.venv/bin/alembic current` → `a06baa922883 (head)`
- `./.venv/bin/pytest -q tests/s01_db_schema_test.py` → pass
- Runtime surface smoke:
  - `./.venv/bin/uvicorn sps.api.main:app` then `curl http://127.0.0.1:8000/healthz` and `/readyz` → 200

## Requirements Advanced
- R001 — Phase 1 schema/migrations exist for the authoritative entities and are proven by Alembic + Postgres-backed tests.

## Requirements Validated
- R001 — Validated by `alembic upgrade head` against docker-compose Postgres + `tests/s01_db_schema_test.py` passing.

## New Requirements Surfaced
- (none)

## Requirements Invalidated or Re-scoped
- None.

## Deviations
- Fixed `docker/postgres/init/00-init.sql` because Postgres forbids `CREATE DATABASE` inside a `DO $$` block; without this, the local Postgres container exited during init and blocked all integration verification.

## Known Limitations
- Schema is intentionally “thin” in a few places (string enums, JSONB payloads) to keep Phase 1 unblocked; later slices can tighten with check constraints / typed enums once workflows and invariant enforcement are in place.

## Follow-ups
- Consider adding a DB probe to `/readyz` once API routes depend on DB connectivity (likely during S02).

## Files Created/Modified
- `pyproject.toml` — Phase 1 persistence stack deps.
- `src/sps/config.py` — env-backed settings + DSN redaction.
- `src/sps/api/main.py` — service entrypoint + `/healthz` + `/readyz`.
- `src/sps/db/models.py` — Phase 1 SQLAlchemy models.
- `src/sps/db/session.py` — engine/session helpers for runtime + tests.
- `alembic/` + `alembic.ini` — migrations.
- `docker/postgres/init/00-init.sql` — fixed init script so local DB boots cleanly.
- `tests/s01_db_schema_test.py` — Postgres-backed schema smoke + constraint tests.

## Forward Intelligence

### What the next slice should know
- Docker Postgres init scripts run only on fresh volumes; if you change init SQL, you often need `docker compose down -v` to re-run it.
- When inserting FK-linked rows via SQLAlchemy without ORM relationships, you may need explicit `flush()` ordering in tests.

### What's fragile
- Any future change to the DB DSN env var names must keep Alembic and runtime aligned (both flow through `Settings`).

### Authoritative diagnostics
- `./.venv/bin/alembic current` + `./.venv/bin/pytest -q tests/s01_db_schema_test.py` are the fastest “is the schema real?” signals.

### What assumptions changed
- "The init SQL was already correct" — it wasn’t; `CREATE DATABASE` cannot run inside a `DO` block, so we had to switch to `\gexec`.
