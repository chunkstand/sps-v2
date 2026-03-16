---
estimated_steps: 5
estimated_files: 5
---

# T03: Expose read surfaces + integration/runbook verification

**Slice:** S02 — Jurisdiction + requirements fixtures, persistence, and workflow progression
**Milestone:** M004-lp1flz

## Description
Expose API read surfaces for persisted artifacts and add integration tests + runbook to prove workflow progression and artifact persistence in real runtime.

## Steps
1. Add response contracts for JurisdictionResolution + RequirementSet payloads.
2. Implement GET endpoints on the cases router to fetch jurisdiction/requirements artifacts by case_id.
3. Extend integration tests to assert API responses and DB persistence after workflow progression.
4. Add docker-compose runbook with Postgres assertions for the new tables and transitions.
5. Update logs/response errors to include case_id for diagnostics.

## Must-Haves
- [ ] API endpoints return persisted jurisdiction/requirements artifacts with provenance fields.
- [ ] Integration tests + runbook prove RESEARCH_COMPLETE with persisted artifacts and ledger transitions.

## Verification
- `./.venv/bin/pytest tests/m004_s02_jurisdiction_requirements_workflow_test.py`
- `bash scripts/verify_m004_s02.sh`

## Observability Impact
- Signals added/changed: API logs `cases.jurisdiction_fetched`, `cases.requirements_fetched`.
- How a future agent inspects this: `GET /api/v1/cases/{case_id}/jurisdiction`, `GET /api/v1/cases/{case_id}/requirements`, `case_transition_ledger`.
- Failure state exposed: API 404/409 responses with `case_id` and missing artifact reason.

## Inputs
- `src/sps/workflows/permit_case/activities.py` — artifacts persisted by workflow.
- `tests/m004_s01_intake_api_workflow_test.py` — existing integration test patterns.

## Expected Output
- `src/sps/api/contracts/cases.py` — response models.
- `src/sps/api/routes/cases.py` — new read endpoints.
- `tests/m004_s02_jurisdiction_requirements_workflow_test.py` — integration tests.
- `scripts/verify_m004_s02.sh` — docker-compose runbook.
