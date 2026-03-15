---
estimated_steps: 7
estimated_files: 3
---

# T01: Add DB/config dependencies and app skeleton

**Slice:** S01 — Postgres schema + migrations + typed model package
**Milestone:** M001-r2v2t3

## Description
Add the minimal FastAPI app + configuration layer that will host DB wiring and migrations work, without yet requiring a live DB connection to boot.

## Steps
1. Inspect existing `pyproject.toml` + app structure to align with repo conventions.
2. Add dependencies for FastAPI runtime, DB access, and migrations (FastAPI, uvicorn, SQLAlchemy 2, Alembic, psycopg).
3. Implement `src/sps/config.py` with env-backed settings (DB DSN, environment name), with safe redaction helpers.
4. Add `src/sps/api/main.py` exporting `app = FastAPI(...)`.
5. Add `/healthz` and `/readyz` endpoints (both should return 200 without requiring DB access yet).
6. Add placeholder DB engine/session dependency wiring stubs that do not connect until used by later tasks.
7. Add a tiny import smoke check.

## Must-Haves
- [ ] `pyproject.toml` includes required deps for FastAPI + SQLAlchemy/Alembic + Postgres driver.
- [ ] `src/sps/config.py` exists and loads config from env without logging secrets.
- [ ] `src/sps/api/main.py` defines `app` and health endpoints.

## Verification
- `./.venv/bin/python -c "from sps.api.main import app; print('ok')"`
- (Optional) `./.venv/bin/python -c "from sps.config import Settings; print('ok')"`

## Observability Impact
- Signals added/changed: basic health endpoints (`/healthz`, `/readyz`) and safe config redaction.
- How a future agent inspects this: run `uvicorn sps.api.main:app` and hit `/healthz`.
- Failure state exposed: import/config errors surface clearly during app startup without leaking secrets.

## Inputs
- `pyproject.toml` — existing dependency + tooling conventions.
- `src/` — existing package layout and entrypoint patterns.

## Expected Output
- `pyproject.toml` — DB + API dependencies added.
- `src/sps/config.py` — Settings object for env-backed config.
- `src/sps/api/main.py` — FastAPI app skeleton with `/healthz` and `/readyz`.
