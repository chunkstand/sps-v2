---
estimated_steps: 6
estimated_files: 1
---

# T02: Build the S03 end-to-end docker-compose runbook

**Slice:** S03 — End-to-end docker-compose proof (API + worker + Postgres + Temporal)
**Milestone:** M004-lp1flz

## Description
Create a new operator runbook that posts intake via the real API, starts a worker configured with the fixture override, and verifies the workflow advances through RESEARCH_COMPLETE with persisted artifacts and API read surfaces.

## Steps
1. Add `scripts/verify_m004_s03.sh` patterned on `verify_m004_s01.sh` + `verify_m004_s02.sh` with shared lifecycle/cleanup helpers.
2. Start docker-compose infra and apply migrations, then start the API server.
3. POST `/api/v1/cases` to capture the runtime `case_id`, then export `SPS_PHASE4_FIXTURE_CASE_ID_OVERRIDE=CASE-EXAMPLE-001` (read from fixture file) before starting the worker.
4. Start the worker, wait for readiness, and poll `case_transition_ledger` for INTAKE_COMPLETE, JURISDICTION_COMPLETE, and RESEARCH_COMPLETE.
5. Assert artifact persistence in Postgres and fetch the jurisdiction/requirements API endpoints for the runtime case.
6. Include failure diagnostics (worker/api log tails + ledger snapshot) consistent with other runbooks.

## Must-Haves
- [ ] Runbook proves intake → RESEARCH_COMPLETE with real services and fixture-backed artifacts.
- [ ] Postgres assertions use `scripts/lib/assert_postgres.sh` and avoid leaking secrets.

## Verification
- `bash scripts/verify_m004_s03.sh`
- Successful run prints API responses + ledger summaries for the intake case_id.

## Observability Impact
- Signals added/changed: runbook output includes structured log hints and ledger summaries.
- How a future agent inspects this: run `bash scripts/verify_m004_s03.sh` and inspect `docker compose logs worker` for activity-level traces.
- Failure state exposed: log tails + ledger snapshot printed on runbook exit.

## Inputs
- `scripts/verify_m004_s01.sh` — lifecycle and diagnostics patterns.
- `scripts/verify_m004_s02.sh` — ledger + artifact assertion patterns.

## Expected Output
- `scripts/verify_m004_s03.sh` — operator proof script for the full intake → RESEARCH_COMPLETE path.
