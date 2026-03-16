# S02: Jurisdiction + requirements fixtures, persistence, and workflow progression — UAT

**Milestone:** M004-lp1flz
**Written:** 2026-03-15

## UAT Type
- UAT mode: live-runtime
- Why this mode is sufficient: the slice requires real Temporal + Postgres behavior and fixture-backed artifacts persisted through the workflow; the docker-compose runbook exercises the authoritative runtime path.

## Preconditions
- Docker compose stack running (Postgres, Temporal, Temporal UI).
- Migrations applied (`alembic upgrade head`).
- Local venv active with deps installed.

## Smoke Test
Run `bash scripts/verify_m004_s02.sh` and confirm it prints `runbook: ok` without errors.

## Test Cases
### 1. Workflow progression with persisted artifacts
1. Run `bash scripts/verify_m004_s02.sh`.
2. Confirm the output shows `workflow_complete`, `waiting_for_jurisdiction_complete`, and `waiting_for_research_complete`.
3. **Expected:** The runbook prints `CASE_STATE_CHANGED|JURISDICTION_COMPLETE|1` and `CASE_STATE_CHANGED|RESEARCH_COMPLETE|1` along with `CASE-EXAMPLE-001|RESEARCH_COMPLETE`.

### 2. Jurisdiction artifact API inspection
1. After the runbook starts the API, call `GET /api/v1/cases/CASE-EXAMPLE-001/jurisdiction` (or use the runbook output).
2. **Expected:** Response includes at least one jurisdiction resolution with `support_level`, `evidence_ids`, `provenance`, and `evidence_payload` populated.

### 3. Requirement set API inspection
1. Call `GET /api/v1/cases/CASE-EXAMPLE-001/requirements`.
2. **Expected:** Response includes at least one requirement set with `source_rankings`, `freshness_state`, `evidence_ids`, and `provenance` populated.

## Edge Cases
### Guard denial visibility
1. Run the runbook (it forces a denied transition via `CASE-DENIAL-*`).
2. **Expected:** `case_transition_ledger` includes a denial row (visible in runbook postgres summary) without crashing the workflow.

## Failure Signals
- Runbook exits non-zero or does not print `runbook: ok`.
- API responses are 404/409 for the CASE-EXAMPLE-001 artifact endpoints.
- `case_transition_ledger` lacks JURISDICTION_COMPLETE or RESEARCH_COMPLETE rows.
- Persisted artifacts missing provenance/evidence fields.

## Requirements Proved By This UAT
- R011 — JurisdictionResolution persistence with provenance and workflow advancement to JURISDICTION_COMPLETE.
- R012 — RequirementSet persistence with provenance and workflow advancement to RESEARCH_COMPLETE.

## Not Proven By This UAT
- R010 intake normalization beyond creation of a fixture-backed case.
- Full docker-compose end-to-end proof across all services (reserved for S03).

## Notes for Tester
- The Temporal integration test is env-gated; the runbook is the canonical live-runtime proof for this slice.
- If the API port is busy, the runbook will fail; stop local services before running.
