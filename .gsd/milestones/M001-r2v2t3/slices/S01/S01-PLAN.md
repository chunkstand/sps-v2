# S01: Postgres schema + migrations + typed model package

**Goal:** Establish the authoritative Postgres schema (Phase 1) with migrations + typed Python models, so downstream services can persist and validate core SPS entities.
**Demo:** With `docker compose up -d`, we can apply migrations and run a small smoke path that inserts/reads core records from Postgres.

## Must-Haves

- Postgres migrations (Alembic) for core Phase 1 tables: PermitCase, Project, review records, contradictions, transition ledger, evidence metadata, and release applicability / artifact metadata.
- Typed Python models for core entities (Pydantic) and persistence models (SQLAlchemy) with validation at write boundaries.
- A minimal FastAPI app skeleton with health endpoints and DB connectivity wiring.

## Proof Level

- This slice proves: integration
- Real runtime required: yes (Postgres)
- Human/UAT required: no

## Verification

- `docker compose up -d postgres`
- `./.venv/bin/alembic upgrade head`
- `./.venv/bin/pytest -q tests/s01_db_schema_test.py`

## Observability / Diagnostics

- Runtime signals: structured error responses for DB connectivity + migration failures; log lines for migration version and DB DSN host (no secrets)
- Inspection surfaces: `/healthz`, `/readyz` endpoints; `alembic current`; Postgres tables
- Failure visibility: error includes operation + table + invariant/constraint name when applicable
- Redaction constraints: never log passwords, S3 secrets, or raw evidence content

## Integration Closure

- Upstream surfaces consumed: `model/sps/model.yaml` (for enum names), `specs/sps/build-approved/plan.md` Phase 1
- New wiring introduced in this slice: Alembic migration runner; DB session lifecycle; FastAPI app entrypoint
- What remains before the milestone is truly usable end-to-end: evidence registry endpoints + MinIO binding + legal hold guard

## Tasks

- [x] **T01: Add DB/config dependencies and app skeleton** `est:45m`
  - Why: We need a real service + config layer to host migrations, DB session mgmt, and later evidence APIs.
  - Files: `pyproject.toml`, `src/sps/config.py`, `src/sps/api/main.py`
  - Do: Add SQLAlchemy/Alembic/psycopg/FastAPI dependencies; implement env-backed config (DB DSN, env name); add `/healthz` and `/readyz` endpoints; wire DB engine/session dependency.
  - Verify: `./.venv/bin/python -c "from sps.api.main import app; print('ok')"`
  - Done when: API module imports and health endpoints return 200 without DB access.

- [x] **T02: Implement SQLAlchemy models + Alembic migrations for Phase 1 entities** `est:2h`
  - Why: Phase 1 exit criteria requires authoritative stores and keys before workflow logic.
  - Files: `src/sps/db/models.py`, `alembic/versions/*`, `alembic.ini`
  - Do: Define tables for PermitCase/Project/ReviewDecision/Contradiction/StateTransitionLedger/EvidenceArtifact metadata plus release applicability and artifact metadata; add indexes for stable IDs; enforce foreign keys and non-null constraints; generate and commit Alembic migrations.
  - Verify: `docker compose up -d postgres && ./.venv/bin/alembic upgrade head`
  - Done when: migrations apply cleanly on a fresh Postgres volume and `alembic current` shows head.

- [x] **T03: Add DB smoke + schema constraint tests** `est:1h`
  - Why: Prove the schema is real and enforceable before building APIs on top of it.
  - Files: `tests/s01_db_schema_test.py`, `src/sps/db/session.py`
  - Do: Add pytest integration test that connects to Postgres, runs minimal insert/read for each core table, and asserts constraints (e.g. required fields, FK integrity) fail as expected.
  - Verify: `./.venv/bin/pytest -q tests/s01_db_schema_test.py`
  - Done when: test passes locally against docker-compose Postgres.

## Files Likely Touched

- `pyproject.toml`
- `src/sps/config.py`
- `src/sps/api/main.py`
- `src/sps/db/models.py`
- `src/sps/db/session.py`
- `alembic.ini`
- `alembic/`
- `tests/s01_db_schema_test.py`
