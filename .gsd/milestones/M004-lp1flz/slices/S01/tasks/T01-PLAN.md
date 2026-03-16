---
estimated_steps: 4
estimated_files: 4
---

# T01: Define intake contract + create PermitCase/Project via API

**Slice:** M004-lp1flz/S01 — Intake contract + Project persistence + INTAKE_COMPLETE workflow step
**Milestone:** M004-lp1flz

## Description
Establish the spec-derived intake HTTP boundary and persist PermitCase + Project in Postgres. This task introduces the CreateCase request/response contract, normalizes intake fields into the Project model, and starts the PermitCaseWorkflow using the canonical workflow ID.

## Steps
1. Add a spec-aligned CreateCase request/response model (tenant_id, intake_mode, project_description, site_address, requester + normalized project fields) with `extra="forbid"` validation.
2. Implement `/api/v1/cases` route to validate the intake payload, generate case_id/project_id, and insert PermitCase + Project rows in a single transaction.
3. Start the PermitCaseWorkflow using `permit_case_workflow_id(case_id)` and Temporal client wiring after the DB commit.
4. Return 201 with case_id, project_id, and case_state=INTAKE_PENDING (no PII in logs).

## Must-Haves
- [ ] Intake request/response contract aligned to the spec and Project model.
- [ ] PermitCase + Project rows persisted via a single transaction from the intake payload.

## Verification
- `pytest tests/m004_s01_intake_api_workflow_test.py -k contract_validation`
- `pytest tests/m004_s01_intake_api_workflow_test.py -k persistence_rows`

## Observability Impact
- Signals added/changed: `intake_api.case_created` log with case_id/project_id; error log on insert failures.
- How a future agent inspects this: API logs + `permit_cases`/`projects` tables.
- Failure state exposed: HTTP 4xx/5xx with error code + missing rows in DB.

## Inputs
- `specs/sps/build-approved/spec.md` — CreateCase API payload shape.
- `model/sps/model.yaml` — Project required fields.

## Expected Output
- `src/sps/api/contracts/intake.py` — CreateCase request/response models.
- `src/sps/api/routes/cases.py` — API endpoint wiring + persistence logic.
- `src/sps/api/main.py` — router registration for `/api/v1/cases`.
