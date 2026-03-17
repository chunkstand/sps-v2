# S01: Emergency/override artifacts + guard enforcement + lifecycle proof — UAT

**Milestone:** M012-v8s3qn
**Written:** 2026-03-16

## UAT Type
- UAT mode: live-runtime
- Why this mode is sufficient: The slice’s risk is runtime enforcement across API + Temporal + Postgres; the docker-compose stack provides the full authority path.

## Preconditions
- Docker and docker compose installed.
- Python virtualenv created at `.venv` with project dependencies.
- Ports 5432, 7233, 8000 are free.

## Smoke Test
- Run `bash scripts/verify_m012_s01.sh` and confirm it exits 0 with `runbook.success`.

## Test Cases

### 1. Declare emergency with bounded duration
1. Start stack: `bash scripts/start_temporal_dev.sh`.
2. Create a case via `POST /api/v1/cases` with an intake JWT.
3. `POST /api/v1/emergencies` with escalation-owner JWT and `duration_hours: 2`.
4. **Expected:** HTTP 201, response contains `emergency_id`, `expires_at` within 2 hours, and a row exists in `emergency_records`.

### 2. Override creation + guarded transition success
1. Create a valid override via `POST /api/v1/overrides` with `affected_surfaces: ["REVIEW_PENDING->APPROVED_FOR_SUBMISSION"]`.
2. Seed a blocking contradiction for the case.
3. Submit a review decision that includes `override_id`.
4. **Expected:** Transition succeeds (CASE_STATE_CHANGED), `override_artifacts` contains the override_id, and no OVERRIDE_DENIED entry exists for the case.

### 3. Expired override denial
1. Update the override to be expired (e.g., `UPDATE override_artifacts SET expires_at=NOW()-INTERVAL '1 hour'`).
2. Attempt the same guarded transition with the expired override.
3. **Expected:** HTTP 403 (OVERRIDE_DENIED), `case_transition_ledger` contains `event_type=OVERRIDE_DENIED` with `guard_assertion_id=INV-SPS-EMERG-001`.

### 4. EMERGENCY_HOLD entry and cleanup exit
1. Signal emergency hold entry with a valid `emergency_id`.
2. Poll `case_transition_ledger` for `to_state=EMERGENCY_HOLD`.
3. Signal emergency hold exit with `reviewer_confirmation_id` and `target_state=REVIEW_PENDING`.
4. **Expected:** Entry and exit appear in `case_transition_ledger` as `CASE_STATE_CHANGED` events; case returns to REVIEW_PENDING.

## Edge Cases

### Emergency duration cap enforcement
1. `POST /api/v1/emergencies` with `duration_hours: 25`.
2. **Expected:** HTTP 422 with `INVALID_DURATION` error payload.

### Override out-of-scope denial
1. Create override with `affected_surfaces` not including `REVIEW_PENDING->APPROVED_FOR_SUBMISSION`.
2. Attempt guarded transition using that override.
3. **Expected:** HTTP 403 with OVERRIDE_DENIED and guard assertion INV-SPS-EMERG-001 in ledger payload.

## Failure Signals
- `OVERRIDE_DENIED` ledger entries missing `guard_assertion_id`.
- Transition succeeds without a valid override when a blocking contradiction exists.
- EMERGENCY_HOLD entry/exit fails to write `CASE_STATE_CHANGED` rows.

## Requirements Proved By This UAT
- R034 — Emergency and override workflows are explicit, time-bounded, and enforced.

## Not Proven By This UAT
- R035 — Admin policy/config governance (future milestone).

## Notes for Tester
- The runbook cleans up docker-compose (`docker compose down -v`) on exit; re-run `scripts/start_temporal_dev.sh` if you need to inspect Postgres after the runbook.
