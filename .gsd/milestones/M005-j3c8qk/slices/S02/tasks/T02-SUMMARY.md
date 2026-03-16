---
id: T02
parent: S02
milestone: M005-j3c8qk
provides:
  - Incentive guard + workflow advancement + incentives API surface with integration coverage
key_files:
  - invariants/sps/guard-assertions.yaml
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/workflow.py
  - src/sps/api/contracts/cases.py
  - src/sps/api/routes/cases.py
  - tests/m005_s02_incentives_workflow_test.py
key_decisions:
  - None
patterns_established:
  - Incentive freshness guard mirrors compliance/requirements guard structure with ledger-backed denial events
observability_surfaces:
  - case_transition_ledger INCENTIVES_* events, incentives_activity.persisted + cases.incentives_fetched logs, GET /api/v1/cases/{case_id}/incentives
duration: 1.5h
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Wire incentives guard, workflow advance, API read surface, and integration tests

**Added the incentive freshness guard, wired workflow advancement to INCENTIVES_COMPLETE, exposed incentives read API, and expanded Temporal/Postgres integration tests.**

## What Happened
- Registered guard assertion INV-SPS-INC-001 and implemented a 3-day incentive assessment freshness gate in the state transition guard.
- Extended PermitCaseWorkflow to persist IncentiveAssessment fixtures and advance COMPLIANCE_COMPLETE → INCENTIVES_COMPLETE, including a branch for starting at COMPLIANCE_COMPLETE.
- Added incentive assessment response contracts and a /cases/{case_id}/incentives endpoint with consistent error handling and logging.
- Expanded incentives integration tests to cover workflow progression, API readback fidelity, and stale guard denial behavior.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -v -s`

## Diagnostics
- Inspect `case_transition_ledger` for INCENTIVES_* events and call `GET /api/v1/cases/{case_id}/incentives` to confirm persisted assessments and fetch logs.

## Deviations
- None.

## Known Issues
- None.

## Files Created/Modified
- `invariants/sps/guard-assertions.yaml` — added INV-SPS-INC-001 assertion metadata.
- `src/sps/workflows/permit_case/activities.py` — added incentive freshness guard + events.
- `src/sps/workflows/permit_case/workflow.py` — persisted incentives and advanced workflow to INCENTIVES_COMPLETE.
- `src/sps/api/contracts/cases.py` — added incentive response models.
- `src/sps/api/routes/cases.py` — added incentives endpoint + response mapping.
- `tests/m005_s02_incentives_workflow_test.py` — integration tests for workflow, API, and guard denial.
