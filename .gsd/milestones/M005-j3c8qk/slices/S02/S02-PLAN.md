# S02: Incentive assessment artifacts + workflow advance

**Goal:** Persist fixture-backed IncentiveAssessment artifacts, expose them via the case API, and advance PermitCaseWorkflow from COMPLIANCE_COMPLETE to INCENTIVES_COMPLETE with a guarded freshness check.

**Demo:** `pytest tests/m005_s02_incentives_workflow_test.py` passes with Temporal integration, showing IncentiveAssessment persistence, `/cases/{case_id}/incentives` readback, and guarded advancement to INCENTIVES_COMPLETE.

Decomposition reasoning: incentive artifacts are the new authoritative data boundary and the riskiest integration point, so the first task establishes fixtures, schema, and idempotent persistence to keep activities deterministic. The second task then wires workflow/guards and the API surface, finishing with integration tests that prove the end-to-end contract and the guard denial path.

## Must-Haves
- Fixture-backed IncentiveAssessment persistence with provenance/evidence JSONB fields.
- `/api/v1/cases/{case_id}/incentives` read surface following existing 404/409 conventions.
- Guarded transition to INCENTIVES_COMPLETE with a 3-day freshness window and a registered guard assertion ID.
- Temporal/Postgres integration tests covering persistence, API response fidelity, and guard denial on stale assessments (R014).

## Proof Level
- This slice proves: integration
- Real runtime required: yes
- Human/UAT required: no

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -v -s`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -k "guard_denial" -v -s`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -k "guard_denial" -v -s --log-cli-level=INFO`

## Observability / Diagnostics
- Runtime signals: `incentives_activity.persisted`, `cases.incentives_fetched`, `case_transition_ledger` events for INCENTIVES_*.
- Inspection surfaces: `incentive_assessments` table, `case_transition_ledger` rows, GET `/api/v1/cases/{case_id}/incentives`.
- Failure visibility: guard denial event with `guard_assertion_id=INV-SPS-INC-001`, `normalized_business_invariants`, and evaluated_at timestamps.
- Redaction constraints: none.

## Integration Closure
- Upstream surfaces consumed: `src/sps/fixtures/phase5.py`, `apply_state_transition` guard gate, compliance artifact state in the workflow.
- New wiring introduced in this slice: incentive persistence activity + workflow branch to `INCENTIVES_COMPLETE`, incentives case API endpoint.
- What remains before the milestone is truly usable end-to-end: S03 docker-compose runbook proof.

## Tasks
- [x] **T01: Add incentive fixtures, schema, and persistence activity** `est:1.5h`
  - Why: Establish deterministic, idempotent IncentiveAssessment persistence before wiring workflow transitions.
  - Files: `specs/sps/build-approved/fixtures/phase5/incentives.json`, `src/sps/fixtures/phase5.py`, `src/sps/db/models.py`, `alembic/versions/<new>_incentive_assessments.py`, `src/sps/workflows/permit_case/contracts.py`, `src/sps/workflows/permit_case/activities.py`
  - Do: Add fixture dataset + Pydantic models/selectors, create IncentiveAssessment ORM + migration with JSONB provenance/evidence, define workflow contract + idempotent persistence activity mirroring compliance.
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -k "fixtures" -v -s`
  - Done when: IncentiveAssessment rows can be persisted from fixtures without duplication, and fixtures load deterministically via the phase5 selector.
- [x] **T02: Wire incentives guard, workflow advance, API read surface, and integration tests** `est:2h`
  - Why: Close the loop on R014 by advancing the workflow, exposing the artifact, and proving guard behavior.
  - Files: `src/sps/workflows/permit_case/workflow.py`, `src/sps/workflows/permit_case/activities.py`, `invariants/sps/guard-assertions.yaml`, `src/sps/api/contracts/cases.py`, `src/sps/api/routes/cases.py`, `tests/m005_s02_incentives_workflow_test.py`
  - Do: Add `INV-SPS-INC-001` guard assertion with 3-day freshness check, call incentive persistence + guarded transition in the workflow after compliance, add incentives response models + route, and implement Temporal/Postgres integration tests for persistence, API readback, and stale denial.
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -v -s`
  - Done when: Workflow reaches INCENTIVES_COMPLETE with a persisted IncentiveAssessment and stale assessments are denied with the correct guard assertion ID.

## Files Likely Touched
- `specs/sps/build-approved/fixtures/phase5/incentives.json`
- `src/sps/fixtures/phase5.py`
- `src/sps/db/models.py`
- `alembic/versions/<new>_incentive_assessments.py`
- `src/sps/workflows/permit_case/contracts.py`
- `src/sps/workflows/permit_case/activities.py`
- `src/sps/workflows/permit_case/workflow.py`
- `src/sps/api/contracts/cases.py`
- `src/sps/api/routes/cases.py`
- `invariants/sps/guard-assertions.yaml`
- `tests/m005_s02_incentives_workflow_test.py`
