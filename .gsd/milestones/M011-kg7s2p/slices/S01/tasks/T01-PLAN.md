---
estimated_steps: 5
estimated_files: 4
---

# T01: Add post-submission artifact models + read APIs

**Slice:** S01 — Post-submission artifacts + workflow wiring
**Milestone:** M011-kg7s2p

## Description
Add durable schema + API read surfaces for correction tasks, resubmission packages, approval records, and inspection milestones so post-submission artifacts are queryable by case.

## Steps
1. Add ORM models with stable IDs, FK links to permit_cases and submission_attempts, and timestamp fields.
2. Create Alembic migration for the new tables + constraints.
3. Define API response/list contracts for the new artifacts in case contracts.
4. Add case routes to list artifacts by case_id with consistent ordering.
5. Add integration test coverage for list endpoints with seeded rows.

## Must-Haves
- [ ] New artifact tables exist with FK integrity to permit_cases/submission_attempts.
- [ ] Case read APIs return correction/resubmission/approval/inspection artifacts.

## Verification
- `pytest tests/m011_s01_post_submission_artifacts_api_test.py -v`

## Observability Impact
- Signals: new read endpoints expose correction/resubmission/approval/inspection artifacts via case APIs; DB tables provide durable audit trail for post-submission events.
- Inspect: query `/cases/{case_id}/correction-tasks`, `/resubmission-packages`, `/approval-records`, `/inspection-milestones` (or equivalent) plus direct table checks for persisted rows.
- Failure visibility: missing or empty list responses for known seeded rows; FK constraint violations or missing timestamps in DB rows indicate persistence gaps.

## Inputs
- `src/sps/db/models.py` — existing ORM layout and ID conventions
- `src/sps/api/routes/cases.py` — case API patterns for list endpoints

## Expected Output
- `src/sps/db/models.py` — new ORM models
- `alembic/versions/*.py` — migration for post-submission artifact tables
- `src/sps/api/contracts/cases.py` — response/list models
- `src/sps/api/routes/cases.py` — list endpoints for new artifacts
- `tests/m011_s01_post_submission_artifacts_api_test.py` — API read surface coverage
