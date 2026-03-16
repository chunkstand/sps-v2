# S01: Compliance evaluation artifacts + workflow advance — UAT

**Milestone:** M005-j3c8qk
**Written:** 2026-03-15

## UAT Type
- UAT mode: live-runtime
- Why this mode is sufficient: The slice is proven via Temporal/Postgres-backed integration tests that exercise the real workflow, activities, and API surface.

## Preconditions
- Postgres + Temporal are available (local docker-compose or configured services).
- `.venv` is created with dependencies installed.
- `SPS_RUN_TEMPORAL_INTEGRATION=1` is set.

## Smoke Test
Run `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s01_compliance_workflow_test.py -k "phase5_fixture_schema" -v` and confirm it passes.

## Test Cases
### 1. Workflow progression persists compliance evaluation and advances state
1. Run `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s01_compliance_workflow_test.py -k "workflow_progression" -v -s`.
2. Observe logs for `compliance_activity.persisted` and `cases.compliance_fetched`.
3. **Expected:** Test passes, workflow reaches COMPLIANCE_COMPLETE, and the API read returns the evaluation payload with rule results, blockers, warnings, and provenance.

### 2. Compliance guard denies stale/missing evaluation
1. Run `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s01_compliance_workflow_test.py -k "guard_denial" -v -s`.
2. **Expected:** Test passes and the guard denial path records a COMPLIANCE_* denial event with `guard_assertion_id=INV-SPS-COMP-001` in the transition ledger.

## Edge Cases
### Missing compliance evaluation
1. Execute the guard denial test above.
2. **Expected:** Transition is denied; no COMPLIANCE_COMPLETE state is applied.

## Failure Signals
- `tests/m005_s01_compliance_workflow_test.py` failures.
- Missing `compliance_activity.persisted` logs or empty `compliance_evaluations` table after progression test.
- API `/api/v1/cases/{case_id}/compliance` returns 404/409 in the progression test.

## Requirements Proved By This UAT
- R013 — Compliance evaluation persistence, guarded workflow advancement, and compliance API read-back.

## Not Proven By This UAT
- Incentive assessment artifacts or COMPLIANCE_COMPLETE → INCENTIVES_COMPLETE progression (S02).
- End-to-end docker-compose runbook proof (S03).

## Notes for Tester
- Logs in the integration tests are the fastest way to confirm observability surfaces (`compliance_activity.persisted`, `cases.compliance_fetched`) without manual DB queries.
