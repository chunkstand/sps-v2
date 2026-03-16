# S03: End-to-end docker-compose proof for compliance + incentives

**Goal:** Provide a docker-compose runbook that exercises the live API + Temporal worker + Postgres path to drive a case through COMPLIANCE_COMPLETE and INCENTIVES_COMPLETE with persisted compliance/incentive artifacts and ledgered transitions.
**Demo:** `bash scripts/verify_m005_s03.sh` brings up the stack, runs a workflow, and exits 0 after asserting compliance/incentive artifacts and ledger transitions via API + Postgres checks.

## Requirements
- R013 — Compliance evaluation (F-004)
- R014 — Incentive assessment (F-005)

## Planning Notes
This slice is a single integration proof; one focused runbook task is enough. The risk is integration drift (fixtures, guards, and runtime wiring), so the plan prioritizes a single end-to-end script modeled on the proven M004 runbook with Postgres assertions and API readbacks. Verification is the runbook itself, which covers the runtime boundary and provides operational proof.

## Must-Haves
- Runbook script that launches docker-compose services, runs migrations, and drives a workflow to INCENTIVES_COMPLETE.
- Postgres assertions (via containerized psql) for ComplianceEvaluation + IncentiveAssessment persistence and transition ledger entries.
- API readback checks for `/api/v1/cases/{case_id}/compliance` and `/api/v1/cases/{case_id}/incentives`.
- Fixture override + fixture-id cleanup to keep deterministic data and avoid idempotent insert conflicts.

## Proof Level
- This slice proves: operational
- Real runtime required: yes
- Human/UAT required: no

## Verification
- `bash scripts/verify_m005_s03.sh`
- `bash scripts/verify_m005_s03.sh || (echo "runbook failed; check logs for missing ledger/API rows" >&2)`

## Observability / Diagnostics
- Runtime signals: `compliance_activity.persisted`, `incentives_activity.persisted`, `case_transition_ledger` rows for COMPLIANCE/INCENTIVES transitions.
- Inspection surfaces: runbook logs, `scripts/lib/assert_postgres.sh`, case API endpoints.
- Failure visibility: runbook exit code + stderr, missing ledger rows or API responses, guard denial entries in ledger.
- Redaction constraints: avoid printing DSNs/passwords (use containerized psql via compose exec).

## Integration Closure
- Upstream surfaces consumed: `scripts/verify_m004_s03.sh`, `scripts/lib/assert_postgres.sh`, `src/sps/fixtures/phase5.py`, `src/sps/api/routes/cases.py`.
- New wiring introduced in this slice: end-to-end runbook for compliance + incentives docker-compose proof.
- What remains before the milestone is truly usable end-to-end: nothing.

## Tasks
- [x] **T01: Author M005 S03 docker-compose runbook** `est:2h`
  - Why: Delivers the end-to-end operational proof required for the milestone and validates R013/R014 in live runtime.
  - Files: `scripts/verify_m005_s03.sh`, `scripts/verify_m004_s03.sh`, `scripts/lib/assert_postgres.sh`, `specs/sps/build-approved/fixtures/phase5/compliance.json`, `specs/sps/build-approved/fixtures/phase5/incentives.json`
  - Do: Clone the M004 S03 runbook structure; wire phase4/phase5 fixture overrides; clean fixture rows by fixture IDs; start uvicorn + worker; create case + start workflow; wait for COMPLIANCE_COMPLETE and INCENTIVES_COMPLETE; assert compliance/incentive rows + ledger transitions with containerized psql; fetch compliance/incentive APIs for readback.
  - Verify: `bash scripts/verify_m005_s03.sh`
  - Done when: Runbook exits 0 with explicit API + Postgres assertions confirming both artifacts and ledger transitions.

## Files Likely Touched
- `scripts/verify_m005_s03.sh`
- `scripts/verify_m004_s03.sh`
- `scripts/lib/assert_postgres.sh`
- `specs/sps/build-approved/fixtures/phase5/compliance.json`
- `specs/sps/build-approved/fixtures/phase5/incentives.json`
