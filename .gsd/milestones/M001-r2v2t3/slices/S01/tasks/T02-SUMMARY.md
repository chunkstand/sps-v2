---
id: T02
parent: S01
milestone: M001-r2v2t3
provides:
  - SQLAlchemy Phase 1 schema models (PermitCase/Project/ReviewDecision/Contradiction/Evidence/Transition ledger/Release metadata)
  - Alembic environment wired to `sps.config.Settings` + an initial autogen migration
  - Fixed docker Postgres init script so local DB bootstraps correctly
key_files:
  - src/sps/db/models.py
  - alembic/env.py
  - alembic/versions/02b39bad0a95_phase1_schema.py
  - docker/postgres/init/00-init.sql
key_decisions:
  - "Represent Phase 1 contracts with stable-ID keyed tables + JSONB for nested/provenance fields; avoid premature deep normalization"
patterns_established:
  - "Alembic env pulls DB URL from Settings (no DSN in alembic.ini)"
observability_surfaces:
  - "./.venv/bin/alembic current"
duration: 60m
verification_result: passed
completed_at: 2026-03-15T20:45:00Z
blocker_discovered: false
---

# T02: Implement SQLAlchemy models + Alembic migrations for Phase 1 entities

**Created Phase 1 SQLAlchemy models + Alembic migrations (autogen + applied) and fixed Postgres init so docker-compose comes up cleanly.**

## What Happened
- Implemented Phase 1 SQLAlchemy models in `src/sps/db/models.py` for:
  - `permit_cases`, `projects`
  - `review_decisions`
  - `contradiction_artifacts`
  - `case_transition_ledger`
  - `evidence_artifacts`
  - `release_bundles`, `release_artifacts`
- Initialized Alembic (`alembic/`, `alembic.ini`) and rewired `alembic/env.py` to:
  - load the DB URL from `sps.config.Settings`
  - use `Base.metadata` for autogeneration
- Generated the initial schema migration and applied it against local docker-compose Postgres.
- Fixed `docker/postgres/init/00-init.sql` so database creation no longer attempts to run inside a `DO $$` block (Postgres forbids `CREATE DATABASE` inside functions/transactions).

## Verification
- `docker compose up -d postgres` (after fixing init SQL) brings Postgres up successfully.
- `./.venv/bin/alembic revision --autogenerate -m "phase1 schema"` generated a migration.
- `./.venv/bin/alembic upgrade head` applied cleanly.
- `./.venv/bin/alembic current` shows `02b39bad0a95 (head)`.

## Diagnostics
- Check migration status: `./.venv/bin/alembic current`
- Re-apply from scratch (fresh volume): `docker compose down -v && docker compose up -d postgres && ./.venv/bin/alembic upgrade head`

## Deviations
- Added a necessary fix to `docker/postgres/init/00-init.sql` to unblock local Postgres boot (required for the slice verification path).

## Known Issues
- None.

## Files Created/Modified
- `src/sps/db/models.py` — SQLAlchemy models for Phase 1 tables.
- `alembic/env.py` — Alembic env wired to `Settings` + `Base.metadata`.
- `alembic/versions/02b39bad0a95_phase1_schema.py` — initial Phase 1 schema migration.
- `docker/postgres/init/00-init.sql` — fixed DB creation to use `\gexec` (psql) instead of `DO`.
