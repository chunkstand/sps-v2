---
id: T02
parent: S02
milestone: M007-b2t1rz
provides:
  - external status event persistence activity + API ingest/list surface
key_files:
  - src/sps/db/models.py
  - alembic/versions/f0b4c9d7e2a1_external_status_events.py
  - src/sps/workflows/permit_case/activities.py
  - src/sps/api/routes/cases.py
key_decisions:
  - none
patterns_established:
  - External status events use activity-level normalization + idempotent insert with fail-closed error on unknown raw statuses.
observability_surfaces:
  - external_status_event.persist.ok|error logs; GET /api/v1/cases/{case_id}/external-status-events
duration: 1h
verification_result: failed (pytest module unavailable)
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Persist normalized external status events via activity + API

**Added ExternalStatusEvent persistence (model + migration), normalization contracts/activity, and case-scoped ingest/list endpoints with integration tests.**

## What Happened
- Added ExternalStatusEvent SQLAlchemy model and Alembic migration, including mapping_version and submission_attempt linkage.
- Extended workflow contracts with ExternalStatusClass/Confidence enums and normalization request/result shapes.
- Implemented persist_external_status_event activity: loads fixture mapping, normalizes, fails closed on unknown raw status, and persists idempotently with structured logs.
- Registered the new activity in the Temporal worker.
- Added API ingest + list endpoints and contracts for external status events.
- Expanded integration tests to cover known-status persistence, unknown-status fail-closed, and API list readback.

## Verification
- `pytest tests/m007_s02_external_status_events_test.py -v -s` failed: `pytest` command not found in environment.
- `python -m pytest tests/m007_s02_external_status_events_test.py -v -s` failed: `python` not found.
- `python3 -m pytest tests/m007_s02_external_status_events_test.py -v -s` failed: `No module named pytest`.

## Diagnostics
- Logs: `external_status_event.persist.ok|error` with case_id, event_id, mapping_version, normalized_status
- Query: `external_status_events` table
- API: `GET /api/v1/cases/{case_id}/external-status-events`

## Deviations
- None.

## Known Issues
- Verification blocked because `pytest` is unavailable in the current runtime environment (python3 lacks pytest module).

## Files Created/Modified
- `src/sps/db/models.py` — added ExternalStatusEvent model.
- `alembic/versions/f0b4c9d7e2a1_external_status_events.py` — migration for external_status_events table.
- `src/sps/workflows/permit_case/contracts.py` — added external status enums and normalization request/result models.
- `src/sps/workflows/permit_case/activities.py` — added normalization + persistence activity with logs.
- `src/sps/workflows/worker.py` — registered new activity.
- `src/sps/api/contracts/cases.py` — added API schemas for external status ingest/list.
- `src/sps/api/routes/cases.py` — added external status ingest/list endpoints.
- `tests/m007_s02_external_status_events_test.py` — added integration tests for known/unknown status and API list readback.
