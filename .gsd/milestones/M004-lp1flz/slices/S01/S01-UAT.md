# S01: Intake contract + Project persistence + INTAKE_COMPLETE workflow step — UAT

**Milestone:** M004-lp1flz
**Written:** 2026-03-15

## UAT Type
- UAT mode: live-runtime
- Why this mode is sufficient: The slice proves HTTP → Postgres → Temporal integration and ledger evidence, which requires the real API, worker, and database.

## Preconditions
- `docker compose up -d postgres temporal temporal-ui` is running.
- `.venv` exists with project dependencies installed.
- `SPS_DATABASE_URL` points at the docker-compose Postgres service (or default settings are valid).
- Temporal address/namespace/task queue settings are configured for local docker-compose (`SPS_TEMPORAL_ADDRESS`, `SPS_TEMPORAL_NAMESPACE`).

## Smoke Test
Run `bash scripts/verify_m004_s01.sh` and confirm it exits 0 with `runbook: ok`.

## Test Cases
### 1. Intake payload creates PermitCase + Project
1. Start the API and worker (or run `bash scripts/verify_m004_s01.sh` to do this automatically).
2. POST a spec-derived intake payload to `POST /api/v1/cases` (use `tests/fixtures/intake_payload.json` if available or mirror the payload in `tests/m004_s01_intake_api_workflow_test.py`).
3. **Expected:** HTTP 201 with `case_id`, `project_id`, and `case_state=INTAKE_PENDING`.

### 2. Persistence rows are created
1. Query Postgres: `select case_id, project_id, case_state from permit_cases where case_id = '<case_id>';`.
2. Query Postgres: `select project_id, project_type from projects where project_id = '<project_id>';`.
3. **Expected:** Both rows exist and the project fields match the intake payload.

### 3. Workflow advances to INTAKE_COMPLETE
1. Query Postgres: `select event_type, to_state from case_transition_ledger where case_id = '<case_id>' order by occurred_at desc;`.
2. **Expected:** A `CASE_STATE_CHANGED` ledger row exists with `to_state=INTAKE_COMPLETE`.

## Edge Cases
### Invalid intake payload is rejected
1. POST `/api/v1/cases` with a payload missing a required field (e.g., omit `site_address` or `requester`).
2. **Expected:** HTTP 422 response with Pydantic validation errors and no PermitCase/Project rows persisted.

## Failure Signals
- `POST /api/v1/cases` returns 4xx/5xx unexpectedly.
- Missing `permit_cases`/`projects` rows for a returned `case_id`/`project_id`.
- No `CASE_STATE_CHANGED` ledger row with `to_state=INTAKE_COMPLETE`.
- Runbook emits `runbook: failed` or logs contain `transition_denied`.

## Requirements Proved By This UAT
- R010 — Intake contract normalization into Project and INTAKE_COMPLETE workflow transition.

## Not Proven By This UAT
- R011 — JurisdictionResolution persistence and provenance.
- R012 — RequirementSet persistence with provenance.

## Notes for Tester
- The runbook sets a unique Temporal task queue per run; use it if you want to avoid stale worker backlog issues.
- The Temporal integration test in pytest is opt-in; the runbook is the authoritative live-runtime proof.
