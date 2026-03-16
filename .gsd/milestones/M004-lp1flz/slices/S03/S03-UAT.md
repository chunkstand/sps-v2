# S03: End-to-end docker-compose proof (API + worker + Postgres + Temporal) — UAT

**Milestone:** M004-lp1flz
**Written:** 2026-03-15

## UAT Type
- UAT mode: live-runtime
- Why this mode is sufficient: The slice is an operational proof that live docker-compose services plus the real API/worker advance a case to RESEARCH_COMPLETE.

## Preconditions
- Docker is running and `docker compose` can start Postgres/Temporal.
- Python virtualenv is available at `./.venv` with dependencies installed.
- Ports 8000 and 7233 are free.

## Smoke Test
- Run `bash scripts/verify_m004_s03.sh` and confirm it ends with `runbook: ok`.

## Test Cases
### 1. Intake → RESEARCH_COMPLETE (end-to-end)
1. Run `bash scripts/verify_m004_s03.sh`.
2. Observe `runbook: intake_api_201_ok` with a case_id and project_id.
3. **Expected:** Output includes `runbook: waiting_for_research_complete` followed by `runbook: ok`, and `postgres_summary` shows `CASE_STATE_CHANGED` rows for INTAKE_COMPLETE, JURISDICTION_COMPLETE, and RESEARCH_COMPLETE.

### 2. API read surfaces return fixture-backed artifacts
1. Run `bash scripts/verify_m004_s03.sh`.
2. Observe the `runbook: fetching_api_jurisdiction` and `runbook: fetching_api_requirements` outputs.
3. **Expected:** Both responses include the runtime case_id and fixture-backed artifacts (jurisdictions/requirement_sets arrays) with provenance fields.

### 3. Repeatability with fixture override
1. Run `bash scripts/verify_m004_s03.sh` twice back-to-back.
2. **Expected:** Both runs succeed; no `JURISDICTION_REQUIRED_DENIED` appears in the worker log, and each run reaches RESEARCH_COMPLETE.

## Edge Cases
### Fixture lookup failures
1. Temporarily set `SPS_PHASE4_FIXTURE_CASE_ID_OVERRIDE` to a non-existent case_id and rerun the runbook.
2. **Expected:** The runbook fails with a LookupError message containing `fixture_case_id` and does not advance past INTAKE_COMPLETE.

## Failure Signals
- `JURISDICTION_REQUIRED_DENIED` or `RESEARCH_REQUIRED_DENIED` in the worker log.
- Missing `CASE_STATE_CHANGED` ledger rows for JURISDICTION_COMPLETE or RESEARCH_COMPLETE.
- API read surfaces return 404 or empty arrays for jurisdiction/requirements.

## Requirements Proved By This UAT
- R010 — Intake persists Project/PermitCase and reaches INTAKE_COMPLETE under live services.
- R011 — Jurisdiction resolution persists and advances to JURISDICTION_COMPLETE.
- R012 — Requirement set persists and advances to RESEARCH_COMPLETE.

## Not Proven By This UAT
- Any compliance, incentives, submission, or reviewer governance requirements beyond R010–R012.

## Notes for Tester
- Worker logs are written to `.gsd/runbook/m004_s03_worker_*.log` (not `docker compose logs worker`).
