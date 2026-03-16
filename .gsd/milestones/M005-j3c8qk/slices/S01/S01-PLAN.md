# S01: Compliance evaluation artifacts + workflow advance

**Goal:** Persist fixture-backed ComplianceEvaluation artifacts with rule-by-rule outputs and provenance, and advance PermitCaseWorkflow to COMPLIANCE_COMPLETE under a guarded transition.
**Demo:** A Temporal-backed workflow run persists a ComplianceEvaluation from phase5 fixtures, advances the case to COMPLIANCE_COMPLETE, and `GET /api/v1/cases/{case_id}/compliance` returns the evaluation payload with provenance.

## Planning Notes
This slice is the first Phase 5 boundary and carries the determinism risk. The work is split to keep activity-side evaluation + persistence isolated from workflow wiring, then finalize with integration tests that prove the activity, guard, workflow, and API surfaces all line up. Verification mirrors the Phase 4 pattern: fixture schema validation, workflow progression under Temporal, Postgres assertions, and API read-back.

## Requirement Coverage
- R013 — Compliance evaluation (F-004)

## Must-Haves
- Fixture-backed ComplianceEvaluation persistence (rule results + blockers/warnings + provenance JSONB) keyed by stable IDs.
- Workflow advances RESEARCH_COMPLETE → COMPLIANCE_COMPLETE only after compliance evaluation is present and fresh.
- `GET /api/v1/cases/{case_id}/compliance` returns the persisted evaluation payload.
- Integration test proves the workflow advancement and API read surface using real Postgres + Temporal.

## Proof Level
- This slice proves: integration
- Real runtime required: yes
- Human/UAT required: no

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 python -m pytest tests/m005_s01_compliance_workflow_test.py -v -s`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 python -m pytest tests/m005_s01_compliance_workflow_test.py -k "guard_denial" -v -s`
- Inspect denial ledger payload: `SELECT event_type, guard_assertion_id, normalized_business_invariants FROM case_transition_ledger WHERE event_type = 'COMPLIANCE_REQUIRED_DENIED' ORDER BY occurred_at DESC LIMIT 1;`

## Observability / Diagnostics
- Runtime signals: `compliance_activity.persisted`, `workflow.transition_applied`, `activity.denied` (for guard failures)
- Inspection surfaces: `compliance_evaluations` table, `case_transition_ledger`, `GET /api/v1/cases/{case_id}/compliance`
- Failure visibility: denial payload includes `event_type`, `guard_assertion_id`, `normalized_business_invariants`
- Redaction constraints: no fixture payload secrets; only case IDs and rule IDs in logs

## Integration Closure
- Upstream surfaces consumed: `RequirementSet` fixtures, `apply_state_transition`, `PermitCaseWorkflow` activity wiring
- New wiring introduced in this slice: compliance evaluation activity + guard + API read surface
- What remains before the milestone is truly usable end-to-end: incentive assessment artifacts + runbook proof (S02/S03)

## Tasks
- [x] **T01: Add compliance fixture schema + persistence activity** `est:3h`
  - Why: Establish the authoritative ComplianceEvaluation model, fixtures, and idempotent activity persistence.
  - Files: `src/sps/fixtures/phase5.py`, `specs/sps/build-approved/fixtures/phase5/compliance.json`
  - Do: Define phase5 fixture schema + loader, add ComplianceEvaluation ORM + migration, add compliance activity + contracts with deterministic evaluator and provenance persistence.
  - Verify: `python -m pytest tests/m005_s01_compliance_workflow_test.py -k "fixture_schema" -v`
  - Done when: ComplianceEvaluation rows can be created idempotently from fixtures and include provenance JSONB.
- [x] **T02: Wire compliance guard, workflow transition, and API read surface** `est:3h`
  - Why: Connect the evaluation artifact to workflow advancement and expose it via the case API.
  - Files: `src/sps/workflows/permit_case/workflow.py`, `src/sps/workflows/permit_case/activities.py`
  - Do: Add compliance guard branch in `apply_state_transition`, wire workflow to call compliance activity then attempt RESEARCH_COMPLETE → COMPLIANCE_COMPLETE, add API response models + `/cases/{case_id}/compliance` endpoint.
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 python -m pytest tests/m005_s01_compliance_workflow_test.py -k "progression" -v`
  - Done when: Workflow advances to COMPLIANCE_COMPLETE with guard denial if compliance is missing/stale and API returns evaluation payload.
- [x] **T03: Integration tests for compliance workflow + API** `est:2h`
  - Why: Prove the end-to-end integration path with Temporal, Postgres, and the read surface.
  - Files: `tests/m005_s01_compliance_workflow_test.py`
  - Do: Add fixture schema validation, workflow progression test, API read assertions, and guard denial coverage with log/ledger checks.
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 python -m pytest tests/m005_s01_compliance_workflow_test.py -v -s`
  - Done when: Tests pass and verify ComplianceEvaluation persistence, COMPLIANCE_COMPLETE transition, and API response fields.

## Files Likely Touched
- `src/sps/fixtures/phase5.py`
- `specs/sps/build-approved/fixtures/phase5/compliance.json`
- `src/sps/db/models.py`
- `alembic/versions/*.py`
- `src/sps/workflows/permit_case/contracts.py`
- `src/sps/workflows/permit_case/activities.py`
- `src/sps/workflows/permit_case/workflow.py`
- `src/sps/api/contracts/cases.py`
- `src/sps/api/routes/cases.py`
- `tests/m005_s01_compliance_workflow_test.py`
