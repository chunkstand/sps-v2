---
estimated_steps: 4
estimated_files: 2
---

# T03: Integration tests for compliance workflow + API

**Slice:** S01 — Compliance evaluation artifacts + workflow advance  
**Milestone:** M005-j3c8qk

## Description
Add Temporal/Postgres integration tests that validate the phase5 fixture schema, prove the workflow advances to COMPLIANCE_COMPLETE with a persisted ComplianceEvaluation, and confirm the case API returns the evaluation payload. This provides the primary proof surface for R013.

## Steps
1. Create `tests/m005_s01_compliance_workflow_test.py` mirroring the Phase 4 integration test structure (migrations, reset, Temporal worker, workflow run).
2. Add a fixture-schema test that loads the phase5 compliance dataset and asserts rule results, blockers/warnings, and provenance fields are present.
3. Add a workflow progression test that persists a PermitCase at RESEARCH_COMPLETE, runs the workflow, asserts a ledger row for COMPLIANCE_COMPLETE, and verifies a ComplianceEvaluation row exists in Postgres.
4. Use `httpx.ASGITransport` to call `/api/v1/cases/{case_id}/compliance` and assert the response payload matches the fixture provenance and rule outputs; assert log messages for compliance activity and API fetch.

## Must-Haves
- [ ] Fixture schema test proves phase5 compliance fixtures load and include rule output data.
- [ ] Workflow progression test asserts COMPLIANCE_COMPLETE ledger event and ComplianceEvaluation persistence.
- [ ] API test asserts evaluation payload fields and provenance are returned.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 python -m pytest tests/m005_s01_compliance_workflow_test.py -v -s`

## Inputs
- `src/sps/fixtures/phase5.py` — fixture loader
- `src/sps/workflows/permit_case/workflow.py` — compliance wiring
- `src/sps/api/main.py` — ASGI app for in-process HTTP

## Expected Output
- `tests/m005_s01_compliance_workflow_test.py` — integration tests covering fixture schema, workflow progression, and API read surface

## Observability Impact
- Adds integration coverage around existing signals (`compliance_activity.persisted`, `workflow.transition_applied`, `cases.compliance_*` logs) by asserting they appear during workflow and API tests.
- Future agents can inspect test output and database rows (compliance_evaluations, case_transition_ledger) to validate compliance persistence and workflow advancement.
- Failures surface via missing log messages, absent COMPLIANCE_COMPLETE ledger events, or missing evaluation/provenance fields in API responses.
