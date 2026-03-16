# S02: Status normalization + tracking events — UAT

**Milestone:** M007-b2t1rz
**Written:** 2026-03-16

## UAT Type
- UAT mode: mixed
- Why this mode is sufficient: integration tests exercise real Postgres persistence + API surfaces without requiring a human UI.

## Preconditions
- Postgres is running and reachable by the default SPS settings (e.g., via `docker-compose up -d postgres`).
- `.venv` exists with dev dependencies installed (`pytest`, `alembic`).
- Repository root is the working directory.

## Smoke Test
Run `source .venv/bin/activate && pytest tests/m007_s02_external_status_events_test.py -v -s` — all 4 tests pass.

## Test Cases

### 1. Known status normalization persists an ExternalStatusEvent
1. Run `source .venv/bin/activate && pytest tests/m007_s02_external_status_events_test.py -k persistence_known_status -v -s`.
2. **Expected:** Test passes; logs show Alembic upgrade and the persisted event has `normalized_status=APPROVAL_REPORTED` with `mapping_version=2026-03-16.1`.

### 2. Unknown status fails closed and writes nothing
1. Run `source .venv/bin/activate && pytest tests/m007_s02_external_status_events_test.py -k unknown_status_fails_closed -v -s`.
2. **Expected:** Test passes; `UNKNOWN_RAW_STATUS` is raised and no `external_status_events` row exists for the event.

### 3. API ingest + list readback
1. Run `source .venv/bin/activate && pytest tests/m007_s02_external_status_events_test.py -k api_list_readback -v -s`.
2. **Expected:** API ingest returns 201 with `normalized_status=APPROVAL_REPORTED`; list endpoint returns exactly one event with `mapping_version=2026-03-16.1`.

## Edge Cases

### Unknown raw status through API
1. Run `source .venv/bin/activate && pytest tests/m007_s02_external_status_events_test.py -k unknown_status_fails_closed -v -s` (covers API unknown-status handling through the activity path).
2. **Expected:** Unknown raw status is rejected (fail-closed) and no event is persisted.

## Failure Signals
- Any test failures or non-zero pytest exit code.
- API ingest returning 500/404 instead of 201 for known statuses.
- `external_status_events` table missing or empty after the known-status test.

## Requirements Proved By This UAT
- R017 — status normalization + tracking events persisted and queryable.

## Not Proven By This UAT
- Live docker-compose runbook behavior (S03) for full submission + tracking persistence across services.

## Notes for Tester
- Tests self-run Alembic upgrades and DB resets; ensure Postgres is running before executing pytest.
