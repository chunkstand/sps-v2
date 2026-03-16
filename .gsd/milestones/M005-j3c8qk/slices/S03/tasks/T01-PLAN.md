---
estimated_steps: 7
estimated_files: 5
---

# T01: Author M005 S03 docker-compose runbook

**Slice:** S03 — End-to-end docker-compose proof for compliance + incentives
**Milestone:** M005-j3c8qk

## Description
Create a docker-compose runbook that drives the live API + Temporal worker + Postgres path through COMPLIANCE_COMPLETE and INCENTIVES_COMPLETE, asserting persisted compliance/incentive artifacts and ledger transitions via containerized Postgres checks and API readbacks.

## Steps
1. Clone the structure of `scripts/verify_m004_s03.sh` into `scripts/verify_m005_s03.sh` and update names/headers for M005 S03.
2. Wire phase4 + phase5 fixture override env vars and cleanup logic that deletes fixture rows by fixture IDs before inserting runtime case rows.
3. Add workflow execution flow: start services, run migrations, launch uvicorn and worker, create case, start workflow, and wait for COMPLIANCE_COMPLETE then INCENTIVES_COMPLETE.
4. Add Postgres assertions (via `scripts/lib/assert_postgres.sh`) for `compliance_evaluations`, `incentive_assessments`, and `case_transition_ledger` transitions.
5. Add API readback checks for `/api/v1/cases/{case_id}/compliance` and `/api/v1/cases/{case_id}/incentives` to confirm persisted payloads.
6. Ensure runbook cleans up background processes and docker-compose services on exit (success or failure).
7. Run the script locally to confirm it exits 0 (document expected output paths in comments if needed).

## Must-Haves
- [ ] Runbook reaches INCENTIVES_COMPLETE via real uvicorn + worker runtime.
- [ ] Postgres assertions validate compliance/incentive artifact persistence and ledger entries.
- [ ] API readbacks return compliance/incentive payloads for the runtime case.

## Verification
- `bash scripts/verify_m005_s03.sh`
- Script exits 0 after showing compliance/incentive API readbacks and Postgres assertions.

## Observability Impact
- Signals added/changed: runbook log sections for compliance/incentive API readbacks and ledger assertions.
- How a future agent inspects this: runbook output + `scripts/lib/assert_postgres.sh` queries.
- Failure state exposed: non-zero exit with missing ledger rows or API payloads.

## Inputs
- `scripts/verify_m004_s03.sh` — baseline runbook structure and lifecycle management.
- `scripts/lib/assert_postgres.sh` — containerized Postgres assertion helpers.
- `specs/sps/build-approved/fixtures/phase5/compliance.json` — fixture IDs and evaluated_at timestamps.
- `specs/sps/build-approved/fixtures/phase5/incentives.json` — fixture IDs and assessed_at timestamps.

## Expected Output
- `scripts/verify_m005_s03.sh` — runbook script that proves compliance + incentives end-to-end.