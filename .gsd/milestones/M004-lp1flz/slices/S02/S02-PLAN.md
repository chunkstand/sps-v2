# S02: Jurisdiction + requirements fixtures, persistence, and workflow progression

**Goal:** Persist fixture-backed JurisdictionResolution + RequirementSet artifacts with provenance and advance PermitCaseWorkflow through JURISDICTION_COMPLETE and RESEARCH_COMPLETE.

**Demo:** POST an intake payload, then the workflow persists jurisdiction + requirements artifacts, transitions through JURISDICTION_COMPLETE and RESEARCH_COMPLETE, and the artifacts are inspectable via API/DB.

## Must-Haves
- Fixture datasets for jurisdiction + requirements under `specs/sps/build-approved/fixtures/phase4` and a loader that validates expected schema fields.
- JurisdictionResolution + RequirementSet persistence (models + migration) with provenance/evidence fields.
- Workflow wiring that calls activities to persist artifacts and applies guarded transitions to JURISDICTION_COMPLETE and RESEARCH_COMPLETE.
- Read surfaces (API + DB) to inspect persisted jurisdiction + requirements artifacts for a case.

## Proof Level
- This slice proves: integration
- Real runtime required: yes
- Human/UAT required: no

## Verification
- `tests/m004_s02_jurisdiction_requirements_workflow_test.py`
- `bash scripts/verify_m004_s02.sh`
- Inspect failure-path surface: query `case_transition_ledger` for guard denial rows after a forced invalid transition in tests/runbook.

## Observability / Diagnostics
- Runtime signals: structured logs `jurisdiction_activity.*`, `requirements_activity.*`, `workflow.transition_*`
- Inspection surfaces: `case_transition_ledger`, `jurisdiction_resolutions`, `requirement_sets` tables; `GET /api/v1/cases/{case_id}/jurisdiction`; `GET /api/v1/cases/{case_id}/requirements`
- Failure visibility: guard denial rows in `case_transition_ledger`, activity error logs with `case_id`/`request_id`
- Redaction constraints: preserve PII boundaries from intake (no raw contact data in logs)

## Integration Closure
- Upstream surfaces consumed: `POST /api/v1/cases`, `apply_state_transition`, `PermitCaseWorkflow` intake branch
- New wiring introduced in this slice: jurisdiction/requirements activities registered in the worker and invoked by the workflow; new API read endpoints
- What remains before the milestone is truly usable end-to-end: S03 docker-compose runbook proving live API + worker + Temporal run to RESEARCH_COMPLETE

## Tasks
- [x] **T01: Add jurisdiction/requirements fixtures + persistence schema** `est:2h`
  - Why: Establish authoritative fixture data and DB tables before workflow activities write artifacts.
  - Files: `specs/sps/build-approved/fixtures/phase4/jurisdiction.json`, `specs/sps/build-approved/fixtures/phase4/requirements.json`, `src/sps/db/models.py`, `alembic/versions/<new>_jurisdiction_requirements.py`, `src/sps/fixtures/phase4.py`
  - Do: Create fixture datasets matching the spec fields (support level, evidence IDs, freshness/contradiction states, rankings); add JurisdictionResolution + RequirementSet models with JSONB provenance; create Alembic migration; add loader/validator module for phase4 fixtures.
  - Verify: `./.venv/bin/pytest tests/m004_s02_jurisdiction_requirements_workflow_test.py -k fixture_schema`
  - Done when: Fixtures load with schema validation and migration creates the new tables/columns.

- [x] **T02: Wire activities + workflow transitions for jurisdiction/research** `est:3h`
  - Why: Persist artifacts and advance the workflow through JURISDICTION_COMPLETE and RESEARCH_COMPLETE using guarded transitions.
  - Files: `src/sps/workflows/permit_case/activities.py`, `src/sps/workflows/permit_case/workflow.py`, `src/sps/workflows/worker.py`, `src/sps/db/models.py`
  - Do: Add activities to load fixtures and persist JurisdictionResolution/RequirementSet with provenance; extend `apply_state_transition` for new states; update workflow to call activities and apply guarded transitions with deterministic request IDs; register activities in the worker.
  - Verify: `./.venv/bin/pytest tests/m004_s02_jurisdiction_requirements_workflow_test.py -k workflow_progression`
  - Done when: A Temporal run moves from INTAKE_COMPLETE → JURISDICTION_COMPLETE → RESEARCH_COMPLETE with persisted artifacts.

- [x] **T03: Expose read surfaces + integration/runbook verification** `est:2h`
  - Why: Make persisted artifacts inspectable and prove end-to-end persistence with real API + worker.
  - Files: `src/sps/api/routes/cases.py`, `src/sps/api/contracts/cases.py`, `tests/m004_s02_jurisdiction_requirements_workflow_test.py`, `scripts/verify_m004_s02.sh`
  - Do: Add GET endpoints to return JurisdictionResolution and RequirementSet for a case; add response contracts; extend tests to assert API/DB payloads and ledger transitions; add docker-compose runbook with Postgres assertions.
  - Verify: `./.venv/bin/pytest tests/m004_s02_jurisdiction_requirements_workflow_test.py` and `bash scripts/verify_m004_s02.sh`
  - Done when: API responses include provenance/evidence fields and runbook shows RESEARCH_COMPLETE with persisted artifacts.

## Files Likely Touched
- `specs/sps/build-approved/fixtures/phase4/jurisdiction.json`
- `specs/sps/build-approved/fixtures/phase4/requirements.json`
- `src/sps/fixtures/phase4.py`
- `src/sps/db/models.py`
- `alembic/versions/<new>_jurisdiction_requirements.py`
- `src/sps/workflows/permit_case/activities.py`
- `src/sps/workflows/permit_case/workflow.py`
- `src/sps/workflows/worker.py`
- `src/sps/api/contracts/cases.py`
- `src/sps/api/routes/cases.py`
- `tests/m004_s02_jurisdiction_requirements_workflow_test.py`
- `scripts/verify_m004_s02.sh`
