---
id: M005-j3c8qk
provides:
  - Compliance and incentive artifacts persisted with guarded workflow advancement to INCENTIVES_COMPLETE plus docker-compose runbook proof
key_decisions:
  - None
patterns_established:
  - Fixture override + cleanup runbook pattern for end-to-end proof of new artifacts
  - Guarded freshness checks for evaluation/assessment with ledgered denials and API readbacks
observability_surfaces:
  - compliance_activity.persisted / incentives_activity.persisted logs
  - GET /api/v1/cases/{case_id}/compliance
  - GET /api/v1/cases/{case_id}/incentives
  - case_transition_ledger COMPLIANCE_* and INCENTIVES_* events
requirement_outcomes:
  - id: R013
    from_status: active
    to_status: validated
    proof: "tests/m005_s01_compliance_workflow_test.py integration run + scripts/verify_m005_s03.sh runbook"
  - id: R014
    from_status: active
    to_status: validated
    proof: "tests/m005_s02_incentives_workflow_test.py integration run + scripts/verify_m005_s03.sh runbook"
duration: 7.6h
verification_result: passed
completed_at: 2026-03-16
---

# M005-j3c8qk: Phase 5 — compliance and incentives workers

**Fixture-backed compliance evaluation and incentive assessment now persist to Postgres, advance the workflow through INCENTIVES_COMPLETE, and are proven end-to-end via docker-compose.**

## What Happened

Phase 5 introduced fixture-backed compliance and incentive evaluation workers that persist authoritative artifacts with provenance/evidence payloads. Compliance evaluation now runs deterministically in an activity, writes ComplianceEvaluation rows, and advances the workflow to COMPLIANCE_COMPLETE behind a 30-day freshness guard. Incentive assessment mirrors this pattern with IncentiveAssessment persistence, a 3-day freshness guard, and transition to INCENTIVES_COMPLETE. Both artifacts are exposed through new case read endpoints. The milestone concludes with a docker-compose runbook that drives the live API + worker to INCENTIVES_COMPLETE, confirms ledger transitions, and reads back persisted artifacts via API and Postgres.

## Cross-Slice Verification

- Compliance evaluation persistence + COMPLIANCE_COMPLETE advancement verified via `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s01_compliance_workflow_test.py -v -s`.
- Incentive assessment persistence + INCENTIVES_COMPLETE advancement verified via `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -v -s`.
- End-to-end operational proof verified via `bash scripts/verify_m005_s03.sh`, including Postgres assertions and API readbacks for both artifacts.

## Requirement Changes

- R013: active → validated — compliance evaluation persistence and readback proven by integration tests + runbook (`tests/m005_s01_compliance_workflow_test.py`, `scripts/verify_m005_s03.sh`).
- R014: active → validated — incentive assessment persistence and readback proven by integration tests + runbook (`tests/m005_s02_incentives_workflow_test.py`, `scripts/verify_m005_s03.sh`).

## Forward Intelligence

### What the next milestone should know
- The runbook relies on fixture override IDs and explicit cleanup by fixture IDs to avoid idempotency conflicts; reuse this pattern for Phase 6 end-to-end proofs.

### What's fragile
- Compliance/incentive freshness guards depend on evaluated_at timestamps in fixtures; stale fixtures will deny COMPLIANCE_COMPLETE or INCENTIVES_COMPLETE.

### Authoritative diagnostics
- `.gsd/runbook/m005_s03_worker_*.log` — contains `compliance_activity.persisted` and `incentives_activity.persisted` structured logs proving artifact persistence.

### What assumptions changed
- Operational proof is required (not optional); runbook validation now gates requirement validation for Phase 5 artifacts.

## Files Created/Modified

- `src/sps/fixtures/phase5.py` — compliance + incentive fixture schema and loaders.
- `src/sps/db/models.py` — ComplianceEvaluation and IncentiveAssessment ORM mappings.
- `src/sps/workflows/permit_case/workflow.py` — workflow wiring to COMPLIANCE_COMPLETE and INCENTIVES_COMPLETE.
- `scripts/verify_m005_s03.sh` — docker-compose runbook proving compliance + incentives persistence.
