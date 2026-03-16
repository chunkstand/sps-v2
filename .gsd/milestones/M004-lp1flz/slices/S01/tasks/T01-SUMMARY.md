---
id: T01
parent: S01
milestone: M004-lp1flz
provides:
  - CreateCase intake contract + persistence endpoint
key_files:
  - src/sps/api/contracts/intake.py
  - src/sps/api/routes/cases.py
  - src/sps/api/main.py
  - tests/m004_s01_intake_api_workflow_test.py
key_decisions:
  - None
patterns_established:
  - Intake payload normalized into Project rows with contact_metadata for requester/project_description
observability_surfaces:
  - "intake_api.case_created" and "intake_api.case_create_failed" logs; permit_cases/projects tables
duration: 1h
verification_result: failed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Define intake contract + create PermitCase/Project via API

**Added CreateCase intake contract + /api/v1/cases endpoint that persists PermitCase/Project in one transaction and logs case_created events.**

## What Happened
- Added spec-aligned CreateCase request/response models (extra=forbid) with site address, requester, and normalized project fields.
- Implemented /api/v1/cases route to generate case_id/project_id, persist PermitCase + Project in a single transaction, and best-effort start the PermitCaseWorkflow after commit.
- Registered cases router in the FastAPI app and added tests for contract validation + persistence rows.

## Verification
- `pytest tests/m004_s01_intake_api_workflow_test.py -k contract_validation` (failed: pytest not installed)
- `pytest tests/m004_s01_intake_api_workflow_test.py -k persistence_rows` (failed: pytest not installed)
- `pytest tests/m004_s01_intake_api_workflow_test.py` (failed: pytest not installed)
- `bash scripts/verify_m004_s01.sh` (failed: script missing)

## Diagnostics
- Check API logs for `intake_api.case_created` and `intake_api.case_create_failed` with case_id/project_id.
- Inspect `permit_cases` and `projects` tables for newly created IDs.

## Deviations
- None.

## Known Issues
- Pytest is not installed in the current environment, so verification could not run.
- `scripts/verify_m004_s01.sh` does not exist yet (slice runbook still pending).
- Observability signals were not exercised in a live runtime (no Temporal/Postgres run during verification).

## Files Created/Modified
- `src/sps/api/contracts/intake.py` — CreateCase request/response contract models.
- `src/sps/api/routes/cases.py` — intake endpoint with transactional persistence + workflow start.
- `src/sps/api/main.py` — register `/api/v1/cases` router.
- `tests/m004_s01_intake_api_workflow_test.py` — contract validation + persistence tests.
- `.gsd/milestones/M004-lp1flz/slices/S01/S01-PLAN.md` — marked T01 complete + added failure-path verification step.
- `.gsd/STATE.md` — advanced next action to T02.
