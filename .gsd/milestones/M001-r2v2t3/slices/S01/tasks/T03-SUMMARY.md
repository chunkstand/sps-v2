---
id: T03
parent: S01
milestone: M001-r2v2t3
provides:
  - DB session helpers (`get_engine`, `get_sessionmaker`, `get_db`) for runtime + tests
  - Postgres-backed integration tests proving schema insert/read + FK constraint enforcement
key_files:
  - src/sps/db/session.py
  - tests/s01_db_schema_test.py
key_decisions:
  - "Run `alembic upgrade head` programmatically in the test session fixture so fresh docker volumes don't require manual migration steps"
patterns_established:
  - "Session-scoped migration fixture + per-test TRUNCATE for repeatable integration tests"
observability_surfaces:
  - "./.venv/bin/pytest -q tests/s01_db_schema_test.py"
duration: 35m
verification_result: passed
completed_at: 2026-03-15T20:55:00Z
blocker_discovered: false
---

# T03: Add DB smoke + schema constraint tests

**Added DB session helpers and Postgres-backed integration tests that prove the Phase 1 schema is migratable and enforces key constraints.**

## What Happened
- Added `src/sps/db/session.py` with cached engine + sessionmaker helpers and a `get_db()` generator suitable for later FastAPI wiring.
- Added `tests/s01_db_schema_test.py`:
  - Applies migrations via Alembic at session start.
  - Truncates tables between tests for repeatability.
  - Smoke test inserts/reads rows across the core Phase 1 tables.
  - Negative test proves FK violations fail closed.

## Verification
- Ran: `./.venv/bin/pytest -q tests/s01_db_schema_test.py` → 2 passed.

## Diagnostics
- Re-run schema verification: `./.venv/bin/pytest -q tests/s01_db_schema_test.py`
- If Postgres is missing: `docker compose up -d postgres`

## Deviations
- None.

## Known Issues
- None.

## Files Created/Modified
- `src/sps/db/session.py` — engine/session helpers.
- `tests/s01_db_schema_test.py` — schema smoke + FK negative test.
