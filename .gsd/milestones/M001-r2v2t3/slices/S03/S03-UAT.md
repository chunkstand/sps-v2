# S03: Retention + legal hold guardrails (INV-004) + purge denial tests — UAT

**Milestone:** M001-r2v2t3
**Written:** 2026-03-15

## UAT Type
- UAT mode: live-runtime
- Why this mode is sufficient: legal-hold enforcement is a runtime safety property that must be proven against real Postgres state + real API error surfaces.

## Preconditions
- Docker Desktop running
- Dependencies installed: `./.venv/bin/python -m pip install -e ".[dev]"`

## Smoke Test
1. `docker compose up -d postgres`
2. `./.venv/bin/alembic upgrade head`
3. `./.venv/bin/pytest -q tests/s03_legal_hold_test.py`
4. **Expected:** tests pass.

## Test Cases

### 1. Destructive delete denied under hold (INV-004)
1. `docker compose up -d postgres`
2. Run: `./.venv/bin/pytest -q tests/s03_legal_hold_test.py -k deny`
3. **Expected:** DELETE attempt returns 423 and includes `invariant_id=INV-004` in response payload.

### 2. Dry-run purge excludes held artifacts
1. Run: `./.venv/bin/pytest -q tests/s03_legal_hold_test.py -k purge`
2. **Expected:** held artifacts are not listed purge-eligible.

## Edge Cases

### Migration drift
1. `./.venv/bin/alembic current`
2. **Expected:** shows head revision; if not, rerun `./.venv/bin/alembic upgrade head`.

## Failure Signals
- Any 2xx response from destructive delete when hold is ACTIVE
- Purge evaluator listing held artifacts
- Missing invariant metadata in denial payload

## Requirements Proved By This UAT
- R003 — Legal hold prevents purge/destructive delete of bound evidence (INV-004)

## Not Proven By This UAT
- Any actual destructive purge job (Phase 1 keeps destructive purge disabled)

## Notes for Tester
- The Phase 1 delete endpoint is intentionally disabled when not held (501). The goal here is proving the denial semantics under hold.
