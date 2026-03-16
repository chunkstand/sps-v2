---
estimated_steps: 5
estimated_files: 5
---

# T02: Wire activities + workflow transitions for jurisdiction/research

**Slice:** S02 — Jurisdiction + requirements fixtures, persistence, and workflow progression
**Milestone:** M004-lp1flz

## Description
Add deterministic activities and workflow branches that persist jurisdiction/requirements artifacts and advance PermitCaseWorkflow through JURISDICTION_COMPLETE and RESEARCH_COMPLETE using guarded transitions.

## Steps
1. Implement activities to load phase4 fixtures and persist JurisdictionResolution + RequirementSet rows with provenance metadata.
2. Extend `apply_state_transition` to allow INTAKE_COMPLETE → JURISDICTION_COMPLETE and JURISDICTION_COMPLETE → RESEARCH_COMPLETE transitions with guard assertions.
3. Update `PermitCaseWorkflow` to call the new activities and apply guarded transitions using deterministic request IDs.
4. Register new activities in the Temporal worker.
5. Add structured logs for activity start/finish with `case_id` and `request_id`.

## Must-Haves
- [ ] Workflow progresses through JURISDICTION_COMPLETE and RESEARCH_COMPLETE when artifacts are persisted.
- [ ] Guarded transitions are applied via `apply_state_transition` only (no direct DB state mutation in workflow).

## Verification
- `./.venv/bin/pytest tests/m004_s02_jurisdiction_requirements_workflow_test.py -k workflow_progression`

## Observability Impact
- Signals added/changed: `jurisdiction_activity.persisted`, `requirements_activity.persisted`, workflow `transition_*` logs.
- How a future agent inspects this: `case_transition_ledger` rows for the new states plus activity logs with `case_id`.
- Failure state exposed: guard denial events in the ledger with `denial_reason` and `guard_assertion_id`.

## Inputs
- `src/sps/fixtures/phase4.py` — fixture loader from T01.
- `src/sps/workflows/permit_case/workflow.py` — existing intake branch + request-id pattern.

## Expected Output
- `src/sps/workflows/permit_case/activities.py` — new jurisdiction/requirements activities and guard extensions.
- `src/sps/workflows/permit_case/workflow.py` — workflow branches to JURISDICTION_COMPLETE/RESEARCH_COMPLETE.
- `src/sps/workflows/worker.py` — activity registrations.
