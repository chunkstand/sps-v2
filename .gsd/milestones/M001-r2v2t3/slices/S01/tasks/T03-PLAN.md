---
estimated_steps: 7
estimated_files: 2
---

# T03: Add DB smoke + schema constraint tests

**Slice:** S01 — Postgres schema + migrations + typed model package
**Milestone:** M001-r2v2t3

## Description
Prove the Phase 1 schema is real and enforceable by running integration tests against docker-compose Postgres, including negative constraint assertions.

## Steps
1. Add/confirm DB session helpers (`src/sps/db/session.py`) for test use.
2. Create pytest fixtures for DB DSN and connection lifecycle.
3. Write a smoke test that inserts/reads minimal rows for each core table.
4. Add negative tests asserting constraints fail (e.g., missing required fields, FK violations).
5. Ensure test setup is repeatable (fresh schema / transactional isolation).
6. Run tests against docker-compose Postgres.
7. Document how to run the test locally.

## Must-Haves
- [ ] `tests/s01_db_schema_test.py` passes against docker-compose Postgres.
- [ ] At least one representative negative constraint test exists (fails closed with a clear DB error).

## Verification
- `docker compose up -d postgres`
- `./.venv/bin/pytest -q tests/s01_db_schema_test.py`

## Observability Impact
- Signals added/changed: integration test coverage that fails loudly on schema drift.
- How a future agent inspects this: run `pytest -q tests/s01_db_schema_test.py`.
- Failure state exposed: migration/schema errors surface as failing tests with table/constraint context.

## Inputs
- `src/sps/db/models.py` — models and metadata.
- `alembic/` — schema must already migrate.

## Expected Output
- `src/sps/db/session.py` — engine/session helpers for runtime + tests.
- `tests/s01_db_schema_test.py` — smoke + constraint tests.
