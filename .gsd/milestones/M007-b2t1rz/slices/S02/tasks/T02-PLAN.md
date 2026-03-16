---
estimated_steps: 6
estimated_files: 8
---

# T02: Persist normalized external status events via activity + API

**Slice:** S02 — Status normalization + tracking events
**Milestone:** M007-b2t1rz

## Description
Add the ExternalStatusEvent persistence path with strict normalization and fail-closed behavior, then expose case-scoped ingest and list endpoints. Cover known-status success and unknown-status failure in integration tests.

## Steps
1. Add ExternalStatusEvent SQLAlchemy model and Alembic migration aligned with the contract schema (including submission_attempt_id and mapping_version fields).
2. Extend workflow contracts to include a status normalization request/response shape using the spec enum.
3. Implement activity that looks up the status mapping fixture, normalizes raw status, fails closed on unknowns, and persists ExternalStatusEvent with idempotent insert handling.
4. Register the activity in the Temporal worker.
5. Add API contracts + case-scoped endpoints to ingest a raw status and list ExternalStatusEvent records for a case.
6. Implement integration tests for known status persistence, unknown status fail-closed behavior, and API list readback.

## Must-Haves
- [ ] ExternalStatusEvent rows persist normalized status, raw status, mapping version, and submission_attempt linkage.
- [ ] Unknown raw statuses fail closed with a raised error and no persisted row.
- [ ] Case API can ingest and list ExternalStatusEvent records.

## Verification
- `pytest tests/m007_s02_external_status_events_test.py -v -s`
- Confirm DB row exists for known status and none for unknown status; API list returns the persisted row.

## Observability Impact
- Signals added/changed: `external_status_event.persist.ok|error` logs with case_id, mapping_version, normalized_status
- How a future agent inspects this: query `external_status_events` table or call GET `/api/v1/cases/{case_id}/external-status-events`
- Failure state exposed: activity exception + log with raw_status/mapping_version and no DB row on failure

## Inputs
- `src/sps/fixtures/phase7.py` — status mapping lookup helper from T01.
- `src/sps/workflows/permit_case/activities.py` — idempotent insert pattern from submission adapter.

## Expected Output
- `src/sps/db/models.py` — ExternalStatusEvent model.
- `alembic/versions/*_external_status_events.py` — migration for external_status_events table.
- `src/sps/workflows/permit_case/contracts.py` — status normalization contracts.
- `src/sps/workflows/permit_case/activities.py` — normalization + persistence activity.
- `src/sps/workflows/worker.py` — activity registered.
- `src/sps/api/contracts/cases.py` — API schemas for status ingest/list.
- `src/sps/api/routes/cases.py` — new endpoints for external status events.
- `tests/m007_s02_external_status_events_test.py` — integration tests.
