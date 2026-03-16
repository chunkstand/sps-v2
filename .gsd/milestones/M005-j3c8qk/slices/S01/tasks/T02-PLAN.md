---
estimated_steps: 5
estimated_files: 6
---

# T02: Wire compliance guard, workflow transition, and API read surface

**Slice:** S01 — Compliance evaluation artifacts + workflow advance  
**Milestone:** M005-j3c8qk

## Description
Connect the ComplianceEvaluation artifact to guarded workflow advancement and expose it through the case API. This adds the guard branch in `apply_state_transition`, wires the workflow to persist compliance evaluations before attempting RESEARCH_COMPLETE → COMPLIANCE_COMPLETE, and adds `/cases/{case_id}/compliance` to the API contracts and routes.

## Steps
1. Extend `apply_state_transition` to enforce a compliance-evaluation-required guard for RESEARCH_COMPLETE → COMPLIANCE_COMPLETE, with a stable denial event + guard assertion ID and normalized invariants.
2. Update `PermitCaseWorkflow` to call `persist_compliance_evaluation` after requirements and before attempting the compliance transition.
3. Add API response models (`ComplianceEvaluationResponse`, list wrapper) in `src/sps/api/contracts/cases.py` and implement `/api/v1/cases/{case_id}/compliance` in `src/sps/api/routes/cases.py` with 404/409 behavior matching existing read surfaces.
4. Add structured logs for compliance fetch success/missing/failed (aligned to `cases.requirements_*` patterns).
5. Ensure guard denial is observable in `case_transition_ledger` with `event_type`, `guard_assertion_id`, and `normalized_business_invariants` populated.

## Must-Haves
- [ ] Guard denies advancement without a fresh ComplianceEvaluation and persists a denial ledger event.
- [ ] Workflow calls compliance activity and advances to COMPLIANCE_COMPLETE on success.
- [ ] `GET /api/v1/cases/{case_id}/compliance` returns evaluation payload or 409 when missing.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 python -m pytest tests/m005_s01_compliance_workflow_test.py -k "progression" -v`

## Observability Impact
- Signals added/changed: `activity.denied name=apply_state_transition ... event_type=COMPLIANCE_REQUIRED_DENIED` (or equivalent)
- How a future agent inspects this: `SELECT event_type, payload FROM case_transition_ledger WHERE case_id = '<id>' ORDER BY occurred_at;`
- Failure state exposed: guard denial payload includes `guard_assertion_id` and `normalized_business_invariants`

## Inputs
- `src/sps/workflows/permit_case/activities.py` — guard + activity wiring
- `src/sps/workflows/permit_case/workflow.py` — workflow orchestration pattern
- `src/sps/api/routes/cases.py` — existing case read endpoints

## Expected Output
- `src/sps/workflows/permit_case/workflow.py` — compliance activity + transition wiring
- `src/sps/workflows/permit_case/activities.py` — compliance guard branch
- `src/sps/api/contracts/cases.py` and `src/sps/api/routes/cases.py` — compliance read endpoint
