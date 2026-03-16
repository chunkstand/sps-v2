# S03: End-to-end docker-compose proof for compliance + incentives — UAT

**Milestone:** M005-j3c8qk
**Written:** 2026-03-16

## UAT Type
- UAT mode: live-runtime
- Why this mode is sufficient: This slice’s purpose is an operational docker-compose proof that exercises the real API + Temporal worker + Postgres path.

## Preconditions
- Docker is running and can start the SPS compose stack.
- Local repository dependencies are installed (Python env ready for uvicorn).
- No conflicting services already bound to ports 8000 or 7233.

## Smoke Test
- Run `bash scripts/verify_m005_s03.sh` and confirm it exits 0.

## Test Cases
### 1. Runbook drives compliance + incentives to completion
1. Execute `bash scripts/verify_m005_s03.sh`.
2. Observe logs for `waiting_for_compliance_complete` followed by `waiting_for_incentives_complete`.
3. **Expected:** Script exits 0 and prints `runbook: ok` with Postgres summary rows for COMPLIANCE_COMPLETE and INCENTIVES_COMPLETE.

### 2. API readbacks return compliance evaluation
1. Run the runbook and capture the `case_id` in the output.
2. Confirm the runbook prints a JSON response for `fetching_api_compliance` containing `compliance_evaluations` with rule results, blockers, and provenance.
3. **Expected:** At least one compliance evaluation is returned with `compliance_evaluation_id` and `rule_results` populated.

### 3. API readbacks return incentive assessment
1. Run the runbook and capture the `case_id` in the output.
2. Confirm the runbook prints a JSON response for `fetching_api_incentives` containing `incentive_assessments` with candidate programs and provenance.
3. **Expected:** At least one incentive assessment is returned with `incentive_assessment_id` and `candidate_programs` populated.

## Edge Cases
### Missing ledger rows
1. Temporarily stop the worker after the intake step (to simulate a stalled workflow) and re-run the script.
2. **Expected:** The runbook fails with missing COMPLIANCE_COMPLETE or INCENTIVES_COMPLETE ledger assertions and exits non-zero.

## Failure Signals
- `scripts/verify_m005_s03.sh` exits non-zero.
- Postgres summary output missing `CASE_STATE_CHANGED|COMPLIANCE_COMPLETE` or `CASE_STATE_CHANGED|INCENTIVES_COMPLETE`.
- API readback blocks return empty arrays or 404 responses for compliance/incentives.

## Requirements Proved By This UAT
- R013 — Compliance evaluation persistence and API readback proven in live runtime.
- R014 — Incentive assessment persistence and API readback proven in live runtime.

## Not Proven By This UAT
- Guard denial paths (stale compliance/incentive evaluations).
- Any submission or reviewer flows beyond INCENTIVES_COMPLETE.

## Notes for Tester
- The runbook starts and stops the API and worker automatically; check `.gsd/runbook/` logs for diagnostics if failures occur.
