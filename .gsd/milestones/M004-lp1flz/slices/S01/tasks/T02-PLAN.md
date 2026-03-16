---
estimated_steps: 4
estimated_files: 3
---

# T02: Wire INTAKE_PENDING → INTAKE_COMPLETE workflow transition

**Slice:** M004-lp1flz/S01 — Intake contract + Project persistence + INTAKE_COMPLETE workflow step
**Milestone:** M004-lp1flz

## Description
Extend the workflow and guard activity to handle intake completion. The workflow should detect INTAKE_PENDING cases, apply the guarded transition to INTAKE_COMPLETE, and return a completion result while preserving the existing review-pending behavior.

## Steps
1. Add a lightweight activity to read the current PermitCase state for branching.
2. Extend `apply_state_transition` to allow INTAKE_PENDING → INTAKE_COMPLETE with a Project-exists guard and ledger entry.
3. Update PermitCaseWorkflow to branch on case_state: execute the intake transition when INTAKE_PENDING, otherwise preserve the REVIEW_PENDING flow.
4. Update contracts/result payloads if needed to expose intake transition info without breaking existing tests.

## Must-Haves
- [ ] Guarded transition for INTAKE_PENDING → INTAKE_COMPLETE written to the ledger.
- [ ] Workflow branches correctly without regressing the REVIEW_PENDING path.

## Verification
- `pytest tests/m004_s01_intake_api_workflow_test.py -k workflow_transition`
- `pytest tests/m002_s01_temporal_permit_case_workflow_test.py`

## Observability Impact
- Signals added/changed: `workflow.transition_attempt` + `workflow.transition_applied` for INTAKE_COMPLETE.
- How a future agent inspects this: `case_transition_ledger` entries filtered by case_id/to_state.
- Failure state exposed: denial_reason in ledger payload and workflow error logs.

## Inputs
- `src/sps/workflows/permit_case/activities.py` — existing guard/ledger implementation.
- `src/sps/workflows/permit_case/workflow.py` — workflow run logic.

## Expected Output
- `src/sps/workflows/permit_case/activities.py` — intake transition guard + state reader activity.
- `src/sps/workflows/permit_case/workflow.py` — intake branch execution.
- `src/sps/workflows/permit_case/contracts.py` — any required contract/result updates.
