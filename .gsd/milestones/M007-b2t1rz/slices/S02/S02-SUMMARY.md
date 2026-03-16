---
id: S02
parent: M007-b2t1rz
milestone: M007-b2t1rz
provides:
  - fixture-driven external status normalization with persisted ExternalStatusEvent records and API ingest/list surfaces
requires:
  - slice: S01
    provides: SubmissionAttempt + receipt/manual fallback persistence and proof bundle gate
affects:
  - S03
key_files:
  - specs/sps/build-approved/fixtures/phase7/status-maps.json
  - src/sps/fixtures/phase7.py
  - src/sps/db/models.py
  - alembic/versions/f0b4c9d7e2a1_external_status_events.py
  - src/sps/workflows/permit_case/contracts.py
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/worker.py
  - src/sps/api/contracts/cases.py
  - src/sps/api/routes/cases.py
  - tests/m007_s02_external_status_events_test.py
key_decisions:
  - none
patterns_established:
  - fixture-driven status normalization with fail-closed unknown raw statuses and idempotent persistence by event_id
observability_surfaces:
  - external_status_event.persist.ok|error logs with case_id/event_id/mapping_version
  - GET /api/v1/cases/{case_id}/external-status-events
  - external_status_events table
  - cases.external_status_ingested|unknown|persist_failed API logs
  - tests/m007_s02_external_status_events_test.py (integration harness + DB reset/migrate)
drill_down_paths:
  - .gsd/milestones/M007-b2t1rz/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M007-b2t1rz/slices/S02/tasks/T02-SUMMARY.md
duration: 1.5h
verification_result: passed
completed_at: 2026-03-16
---

# S02: Status normalization + tracking events

**Fixture-driven external status normalization now persists ExternalStatusEvent records and exposes case-scoped ingest/list APIs with fail-closed unknown status handling.**

## What Happened
Phase 7 status mapping fixtures and loader selection logic were added, then wired into a new ExternalStatusEvent persistence activity and case-scoped API endpoints. The activity normalizes raw status inputs via fixture maps, fails closed on unknown statuses, and persists idempotently. Tests were extended to cover known-status persistence, unknown-status failure with no DB row, and API ingest/list readback. The integration tests now perform Alembic upgrades and DB resets to guarantee the new table exists in local environments.

## Verification
- `source .venv/bin/activate && pytest tests/m007_s02_external_status_events_test.py -v -s`

## Requirements Advanced
- R017 — status mapping fixtures + normalization activity + API ingest/list surface.

## Requirements Validated
- R017 — proved by `pytest tests/m007_s02_external_status_events_test.py -v -s` (known status persist, unknown status fail-closed, API list readback).

## New Requirements Surfaced
- none

## Requirements Invalidated or Re-scoped
- none

## Deviations
- none

## Known Limitations
- Live docker-compose runbook for status ingest is still pending in S03; only integration tests prove persistence so far.

## Follow-ups
- Execute S03 runbook to prove live submission + tracking persistence across Postgres/Temporal/MinIO.

## Files Created/Modified
- `specs/sps/build-approved/fixtures/phase7/status-maps.json` — Phase 7 status mapping fixtures with version metadata.
- `src/sps/fixtures/phase7.py` — status mapping loader + case override selection helper.
- `src/sps/db/models.py` — ExternalStatusEvent model.
- `alembic/versions/f0b4c9d7e2a1_external_status_events.py` — migration for external_status_events.
- `src/sps/workflows/permit_case/contracts.py` — normalization request/result + enums.
- `src/sps/workflows/permit_case/activities.py` — normalization + persistence activity with fail-closed behavior.
- `src/sps/workflows/worker.py` — activity registration.
- `src/sps/api/contracts/cases.py` — external status ingest/list contracts.
- `src/sps/api/routes/cases.py` — ingest + list endpoints.
- `tests/m007_s02_external_status_events_test.py` — integration coverage plus DB migrate/reset helpers.

## Forward Intelligence
### What the next slice should know
- The external status event tests now self-migrate and reset the DB; Postgres must be running before running pytest.

### What's fragile
- Fixture selection depends on `SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE`; missing overrides will load default fixture mappings and may not match test expectations.

### Authoritative diagnostics
- `GET /api/v1/cases/{case_id}/external-status-events` — primary read surface for persisted normalized events.
- `external_status_event.persist.ok|error` logs — authoritative normalization success/fail signal (includes mapping_version and raw_status).

### What assumptions changed
- Assumed DB migrations already applied; tests now run Alembic upgrades to ensure new tables exist locally.
