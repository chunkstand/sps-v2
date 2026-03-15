---
id: T01
parent: S01
milestone: M001-r2v2t3
provides:
  - FastAPI app skeleton (`sps.api.main:app`) with liveness/readiness endpoints
  - Env-backed `Settings` with safe DSN redaction helpers
  - Runtime deps for Phase 1 stack (FastAPI/Pydantic/SQLAlchemy/Alembic/psycopg)
key_files:
  - pyproject.toml
  - src/sps/config.py
  - src/sps/api/main.py
key_decisions:
  - "Keep /readyz lightweight in Phase 1 (no DB probe yet) to avoid coupling boot to infra availability"
patterns_established:
  - "Central Settings via pydantic-settings + cached get_settings()"
observability_surfaces:
  - /healthz
  - /readyz
duration: 15m
verification_result: passed
completed_at: 2026-03-15T20:25:00Z
blocker_discovered: false
---

# T01: Add DB/config dependencies and app skeleton

**Added FastAPI app + env-backed config scaffold (no DB required to boot yet), and installed the Phase 1 persistence deps.**

## What Happened
- Expanded `pyproject.toml` dependencies to include the Phase 1 runtime stack (FastAPI/Pydantic v2 + SQLAlchemy/Alembic + psycopg).
- Implemented `sps.config.Settings` using `pydantic-settings`, including best-effort DSN password redaction.
- Added `sps.api.main:app` with `/healthz` and `/readyz` endpoints. Readiness is intentionally lightweight for now; deeper dependency checks will land when DB wiring/migrations are in place.

## Verification
- Ran: `./.venv/bin/python -c "from sps.api.main import app; print('ok')"` → prints `ok`.
- Ran: `./.venv/bin/python -c "from sps.config import Settings, get_settings; s=get_settings(); print('ok', s.env)"` → prints `ok local`.
- Installed deps via: `./.venv/bin/python -m pip install -e ".[dev]"`.

## Diagnostics
- Inspect endpoints by running: `./.venv/bin/uvicorn sps.api.main:app` then `curl localhost:8000/healthz` and `/readyz`.

## Deviations
- None.

## Known Issues
- None.

## Files Created/Modified
- `pyproject.toml` — added Phase 1 runtime dependencies.
- `src/sps/config.py` — env-backed settings + DSN redaction helper.
- `src/sps/api/main.py` — FastAPI app skeleton + `/healthz` and `/readyz`.
