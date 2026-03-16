# S02: Incentive assessment artifacts + workflow advance — UAT

**Milestone:** M005-j3c8qk
**Written:** 2026-03-15

## UAT Type
- UAT mode: artifact-driven
- Why this mode is sufficient: The slice is validated by Temporal/Postgres integration tests that persist IncentiveAssessment artifacts, exercise workflow transitions, and assert API readback/guard denials.

## Preconditions
- Postgres and Temporal are available for integration tests (docker-compose or test harness).
- `.venv` is created with dependencies installed.
- `SPS_RUN_TEMPORAL_INTEGRATION=1` is set for the test run.

## Smoke Test
Run the full slice integration test suite:
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -v -s`
- **Expected:** All tests pass; logs include `incentives_activity.persisted` and `cases.incentives_fetched`.

## Test Cases
### 1. Workflow progression to INCENTIVES_COMPLETE
1. Run: `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -k "test_workflow_progression" -v -s`
2. **Expected:** Test passes and the workflow reaches `INCENTIVES_COMPLETE` with a persisted IncentiveAssessment; ledger entries are created for `INCENTIVES_*` transitions.

### 2. Incentives API readback fidelity
1. Run: `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -k "test_workflow_progression" -v -s`
2. **Expected:** The test asserts `GET /api/v1/cases/{case_id}/incentives` returns the fixture-backed programs and provenance fields without mismatch.

### 3. Guard denial on stale incentives
1. Run: `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -k "guard_denial" -v -s --log-cli-level=INFO`
2. **Expected:** The guard denies advancement with `guard_assertion_id=INV-SPS-INC-001` and logs the denial; the test passes.

## Edge Cases
### Stale assessment freshness window
1. Run the guard denial test above.
2. **Expected:** The workflow does not advance to `INCENTIVES_COMPLETE` when `evaluated_at` is outside the 3-day window.

## Failure Signals
- Pytest failures or skipped tests in `tests/m005_s02_incentives_workflow_test.py`.
- Missing `incentives_activity.persisted` or `cases.incentives_fetched` log lines during the tests.
- No `INCENTIVES_*` rows in `case_transition_ledger` after the progression test.

## Requirements Proved By This UAT
- R014 — Incentive assessment (F-005) via integration tests covering persistence, API readback, and guard denials.

## Not Proven By This UAT
- End-to-end docker-compose runbook proof (S03).

## Notes for Tester
- The incentive freshness window is 3 days; if fixtures are updated, ensure `evaluated_at` stays within range for the progression test.
