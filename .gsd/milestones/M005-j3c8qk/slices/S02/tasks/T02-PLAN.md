---
estimated_steps: 4
estimated_files: 6
---

# T02: Wire incentives guard, workflow advance, API read surface, and integration tests

**Slice:** S02 — Incentive assessment artifacts + workflow advance
**Milestone:** M005-j3c8qk

## Description
Wire the incentive assessment into the workflow, enforce freshness guards, expose the read API, and prove the end-to-end contract via Temporal/Postgres integration tests.

## Steps
1. Register `INV-SPS-INC-001` in `invariants/sps/guard-assertions.yaml` and add a 3-day freshness guard in `apply_state_transition` for COMPLIANCE_COMPLETE → INCENTIVES_COMPLETE.
2. Update `src/sps/workflows/permit_case/workflow.py` to persist IncentiveAssessment and attempt the guarded transition to INCENTIVES_COMPLETE.
3. Add incentives response models in `src/sps/api/contracts/cases.py` and a `/cases/{case_id}/incentives` route in `src/sps/api/routes/cases.py` mirroring compliance error handling.
4. Add `tests/m005_s02_incentives_workflow_test.py` covering persistence, API readback, and stale-guard denial behavior.

## Must-Haves
- [ ] Workflow reaches INCENTIVES_COMPLETE when incentive assessment is fresh.
- [ ] Stale incentive assessment blocks advancement with `INV-SPS-INC-001`.
- [ ] `/api/v1/cases/{case_id}/incentives` returns eligibility + provenance payloads.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -v -s`

## Observability Impact
- Signals added/changed: `case_transition_ledger` INCENTIVES_* events, `cases.incentives_fetched` log.
- How a future agent inspects this: query `case_transition_ledger` and hit the incentives endpoint.
- Failure state exposed: guard denial event with assertion ID and evaluated_at timestamps.

## Inputs
- `src/sps/workflows/permit_case/activities.py` — incentive persistence activity from T01.
- `src/sps/workflows/permit_case/contracts.py` — incentive contract types from T01.

## Expected Output
- `src/sps/workflows/permit_case/workflow.py` — incentive persistence + transition wiring.
- `invariants/sps/guard-assertions.yaml` — `INV-SPS-INC-001` entry.
- `src/sps/api/contracts/cases.py` + `src/sps/api/routes/cases.py` — incentives API surface.
- `tests/m005_s02_incentives_workflow_test.py` — integration tests proving R014.
