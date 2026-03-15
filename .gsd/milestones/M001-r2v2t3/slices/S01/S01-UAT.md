# S01: Postgres schema + migrations + typed model package — UAT

**Milestone:** M001-r2v2t3
**Written:** 2026-03-15

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: this slice’s success criteria are “real Postgres migrations apply and the schema is enforceable,” which is best proven by docker-compose + Alembic + Postgres-backed integration tests, plus a quick live check of the service health surfaces.

## Preconditions

- Docker Desktop running
- Python deps installed: `./.venv/bin/python -m pip install -e ".[dev]"`
- Port 8000 available (for the FastAPI smoke check)

## Smoke Test

1. `docker compose up -d postgres`
2. `./.venv/bin/alembic upgrade head`
3. `./.venv/bin/pytest -q tests/s01_db_schema_test.py`
4. **Expected:** Alembic applies cleanly and pytest passes.

## Test Cases

### 1. Fresh-volume migration

1. `docker compose down -v`
2. `docker compose up -d postgres`
3. `./.venv/bin/alembic upgrade head`
4. `./.venv/bin/alembic current`
5. **Expected:** Postgres starts successfully; migrations apply to a fresh volume; `alembic current` reports a head revision.

### 2. Schema constraints fail closed

1. `docker compose up -d postgres`
2. `./.venv/bin/pytest -q tests/s01_db_schema_test.py::test_fk_violation_fails_closed`
3. **Expected:** test passes, proving FK violations raise `IntegrityError`.

### 3. Service health + readiness endpoints

1. Start the app: `./.venv/bin/uvicorn sps.api.main:app --port 8000`
2. In another shell:
   - `curl -fsS http://127.0.0.1:8000/healthz`
   - `curl -fsS http://127.0.0.1:8000/readyz`
3. **Expected:** both return HTTP 200 JSON; `/readyz` includes the configured environment (e.g. `{"status":"ok","env":"local"}`).

## Edge Cases

### Docker init script regression

1. `docker compose down -v && docker compose up -d postgres`
2. **Expected:** Postgres container stays `Up` (does not exit during init). If it exits, check `docker compose logs postgres` for init SQL failures.

## Failure Signals

- `docker compose ps` shows postgres exited
- `./.venv/bin/alembic upgrade head` fails to connect or fails applying DDL
- `pytest` failures in `tests/s01_db_schema_test.py`
- Uvicorn fails to start, or `/healthz` / `/readyz` do not return 200

## Requirements Proved By This UAT

- R001 — Postgres schema + migrations exist and are enforceable against real Postgres.

## Not Proven By This UAT

- Evidence registry APIs or MinIO roundtrips (S02)
- Legal hold enforcement (S03)

## Notes for Tester

- If you change `docker/postgres/init/00-init.sql`, you generally need `docker compose down -v` for it to take effect (init scripts run only on fresh volumes).
