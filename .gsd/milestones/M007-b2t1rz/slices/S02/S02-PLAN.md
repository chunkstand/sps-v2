# S02: Status normalization + tracking events

**Goal:** Normalize external status inputs via Phase 7 fixture maps and persist them as ExternalStatusEvent records with fail-closed behavior for unmapped statuses.
**Demo:** Ingest a raw portal status for a case and read back a normalized ExternalStatusEvent; unmapped status raises a fail-closed error and records nothing.

## Must-Haves
- Phase 7 status mapping fixtures with version metadata and loader selection honoring case_id override.
- ExternalStatusEvent persistence activity that normalizes raw status via fixture map and fails closed on unknown statuses.
- Case-scoped API endpoints to ingest and list normalized ExternalStatusEvent records.
- Integration tests proving known-status persistence + unknown-status fail-closed behavior.

## Proof Level
- This slice proves: integration
- Real runtime required: yes
- Human/UAT required: no

## Verification
- `pytest tests/m007_s02_external_status_events_test.py -v -s`

## Observability / Diagnostics
- Runtime signals: `external_status_event.persist.ok|error` logs with case_id, submission_attempt_id, mapping_version, normalized_status
- Inspection surfaces: `external_status_events` table; GET `/api/v1/cases/{case_id}/external-status-events`
- Failure visibility: activity exception with raw_status + mapping_version logged; absence of DB row on failure
- Redaction constraints: no PII in logs; raw status text only

## Integration Closure
- Upstream surfaces consumed: `src/sps/fixtures/phase7.py` loader pattern; submission_attempt IDs from S01
- New wiring introduced in this slice: API ingest endpoint → activity normalization → ExternalStatusEvent persistence
- What remains before the milestone is truly usable end-to-end: S03 runbook for live submission + tracking

## Tasks
- [x] **T01: Add Phase 7 status mapping fixtures + loader** `est:1h`
  - Why: Status normalization is fixture-driven and must be deterministic + versioned.
  - Files: `specs/sps/build-approved/fixtures/phase7/status-maps.json`, `src/sps/fixtures/phase7.py`
  - Do: Add a status mapping fixture file with adapter family + version metadata; extend the Phase 7 loader to select mappings (honor case_id override) and expose a lookup helper for normalization.
  - Verify: `pytest tests/m007_s02_external_status_events_test.py -v -s`
  - Done when: Loader returns a mapping entry for the test case and includes mapping version metadata.
- [x] **T02: Persist normalized external status events via activity + API** `est:2h`
  - Why: External status inputs must be normalized, persisted, and queryable with fail-closed behavior.
  - Files: `src/sps/db/models.py`, `alembic/versions/*_external_status_events.py`, `src/sps/workflows/permit_case/contracts.py`, `src/sps/workflows/permit_case/activities.py`, `src/sps/workflows/worker.py`, `src/sps/api/contracts/cases.py`, `src/sps/api/routes/cases.py`, `tests/m007_s02_external_status_events_test.py`
  - Do: Add ExternalStatusEvent model + migration; define contracts for normalization input/output; implement activity that looks up fixture map, normalizes status, fails closed on unknowns, and persists with idempotent insert; register activity; add case-scoped ingest + list endpoints; implement integration tests for known and unknown statuses plus API readback.
  - Verify: `pytest tests/m007_s02_external_status_events_test.py -v -s`
  - Done when: Known statuses persist with normalized enum values and unknown statuses raise with no persisted row; API list returns the persisted event.

## Files Likely Touched
- `specs/sps/build-approved/fixtures/phase7/status-maps.json`
- `src/sps/fixtures/phase7.py`
- `src/sps/db/models.py`
- `alembic/versions/*_external_status_events.py`
- `src/sps/workflows/permit_case/contracts.py`
- `src/sps/workflows/permit_case/activities.py`
- `src/sps/workflows/worker.py`
- `src/sps/api/contracts/cases.py`
- `src/sps/api/routes/cases.py`
- `tests/m007_s02_external_status_events_test.py`
