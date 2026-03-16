---
estimated_steps: 4
estimated_files: 3
---

# T03: Add integration test + operator runbook for intake flow

**Slice:** M004-lp1flz/S01 — Intake contract + Project persistence + INTAKE_COMPLETE workflow step
**Milestone:** M004-lp1flz

## Description
Prove the end-to-end intake path using real Temporal + Postgres and the HTTP boundary. The test and runbook should demonstrate that intake creates PermitCase/Project and the workflow reaches INTAKE_COMPLETE.

## Steps
1. Add an integration test that starts a Temporal worker, calls `/api/v1/cases` via httpx ASGI transport, and waits for INTAKE_COMPLETE in the ledger.
2. Assert PermitCase + Project rows are persisted and mapped to the returned case_id/project_id.
3. Add `scripts/verify_m004_s01.sh` to run the same flow against docker-compose services (worker + API + DB).
4. Document runbook diagnostics (log tails + ledger queries) on failure.

## Must-Haves
- [ ] Integration test proves HTTP → Postgres → Temporal → INTAKE_COMPLETE.
- [ ] Runbook script exercises the real services and asserts DB outcomes.

## Verification
- `pytest tests/m004_s01_intake_api_workflow_test.py`
- `bash scripts/verify_m004_s01.sh`

## Observability Impact
- Signals added/changed: runbook emits structured `runbook:` progress messages.
- How a future agent inspects this: runbook log files + Postgres assertions.
- Failure state exposed: non-zero runbook exit with tail logs and query output.

## Inputs
- `scripts/verify_m003_s01.sh` — runbook structure reference.
- `tests/m003_s01_reviewer_api_boundary_test.py` — Temporal + HTTP test patterns.

## Expected Output
- `tests/m004_s01_intake_api_workflow_test.py` — end-to-end integration test.
- `scripts/verify_m004_s01.sh` — operator runbook for intake.
