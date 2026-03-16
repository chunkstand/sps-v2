---
id: T03
parent: S02
milestone: M004-lp1flz
provides:
  - API read surfaces for jurisdiction/requirements artifacts with provenance, plus end-to-end verification.
key_files:
  - src/sps/api/contracts/cases.py
  - src/sps/api/routes/cases.py
  - tests/m004_s02_jurisdiction_requirements_workflow_test.py
  - scripts/verify_m004_s02.sh
key_decisions:
  - None
patterns_established:
  - Case artifact read endpoints return list wrappers and include provenance/evidence payloads.
observability_surfaces:
  - GET /api/v1/cases/{case_id}/jurisdiction, GET /api/v1/cases/{case_id}/requirements, logs cases.jurisdiction_fetched/cases.requirements_fetched
  - case_transition_ledger guard denial rows (JURISDICTION_REQUIRED_DENIED)
duration: 1.5h
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T03: Expose read surfaces + integration/runbook verification

**Added case read endpoints for jurisdiction/requirements artifacts, updated integration coverage, and shipped a runbook that proves workflow progression plus guard-denial visibility.**

## What Happened
- Added Pydantic response contracts for jurisdiction and requirement set payloads (including provenance/evidence fields).
- Implemented GET /cases/{case_id}/jurisdiction and /requirements with structured logs, case_id-rich error payloads, and DB lookups.
- Extended the S02 integration test to call the new API endpoints, validate payload parity with fixtures, and assert guard-denial ledger rows.
- Built a docker-compose runbook that seeds the fixture case, runs the workflow to RESEARCH_COMPLETE, validates persisted artifacts, hits the API read surfaces, and forces a denial row for diagnostics.

## Verification
- `./.venv/bin/pytest tests/m004_s02_jurisdiction_requirements_workflow_test.py` (1 passed, 1 skipped: Temporal integration is opt-in unless SPS_RUN_TEMPORAL_INTEGRATION=1).
- `bash scripts/verify_m004_s02.sh`

## Diagnostics
- API signals: `cases.jurisdiction_fetched` and `cases.requirements_fetched` logs include case_id/count.
- Failure surfaces: 404/409 responses include `case_id` and missing artifact reason; guard denials visible in `case_transition_ledger`.
- Runbook: `bash scripts/verify_m004_s02.sh` prints API payloads and ledger summaries.

## Deviations
- None.

## Known Issues
- None.

## Files Created/Modified
- `src/sps/api/contracts/cases.py` — response models for jurisdiction/requirement read surfaces.
- `src/sps/api/routes/cases.py` — new GET endpoints + logging/error payloads.
- `tests/m004_s02_jurisdiction_requirements_workflow_test.py` — API + guard-denial assertions.
- `scripts/verify_m004_s02.sh` — docker-compose runbook for workflow + persistence verification.
- `.gsd/milestones/M004-lp1flz/slices/S02/S02-PLAN.md` — mark T03 complete.
- `.gsd/STATE.md` — update next action.
