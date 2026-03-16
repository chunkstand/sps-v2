---
id: S02
parent: M004-lp1flz
milestone: M004-lp1flz
provides:
  - Fixture-backed jurisdiction + requirements persistence with provenance and workflow progression to RESEARCH_COMPLETE
requires:
  - slice: S01
    provides: Intake API + Project persistence with INTAKE_COMPLETE workflow state
affects:
  - S03
key_files:
  - specs/sps/build-approved/fixtures/phase4/jurisdiction.json
  - specs/sps/build-approved/fixtures/phase4/requirements.json
  - src/sps/fixtures/phase4.py
  - src/sps/db/models.py
  - alembic/versions/b2c4f7e8a901_jurisdiction_requirements.py
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/workflow.py
  - src/sps/workflows/worker.py
  - src/sps/api/contracts/cases.py
  - src/sps/api/routes/cases.py
  - tests/m004_s02_jurisdiction_requirements_workflow_test.py
  - scripts/verify_m004_s02.sh
key_decisions:
  - none
patterns_established:
  - Fixture-backed jurisdiction/requirements activities persist JSONB provenance and emit structured activity logs
observability_surfaces:
  - case_transition_ledger guard denial rows, jurisdiction_resolutions/requirement_sets tables, workflow.transition_* logs, GET /api/v1/cases/{case_id}/jurisdiction|requirements
  - scripts/verify_m004_s02.sh runbook output for end-to-end workflow + API checks
  - logs: jurisdiction_activity.persisted, requirements_activity.persisted, cases.jurisdiction_fetched, cases.requirements_fetched
drill_down_paths:
  - .gsd/milestones/M004-lp1flz/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M004-lp1flz/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M004-lp1flz/slices/S02/tasks/T03-SUMMARY.md
duration: 3h 40m
verification_result: passed
completed_at: 2026-03-15
---

# S02: Jurisdiction + requirements fixtures, persistence, and workflow progression

**Fixture-backed jurisdiction + requirements artifacts now persist with provenance/evidence, and workflows advance through JURISDICTION_COMPLETE and RESEARCH_COMPLETE with API read surfaces.**

## What Happened
Added Phase 4 fixture datasets and validators, persisted JurisdictionResolution and RequirementSet artifacts with JSONB provenance, wired new activities into PermitCaseWorkflow with guarded transitions, exposed GET endpoints for case jurisdiction/requirements, and shipped an end-to-end docker-compose runbook plus integration coverage that validates workflow progression and guard-denial visibility.

## Verification
- `./.venv/bin/pytest tests/m004_s02_jurisdiction_requirements_workflow_test.py`
- `bash scripts/verify_m004_s02.sh`

## Requirements Advanced
- none

## Requirements Validated
- R011 — proved via pytest + runbook showing JurisdictionResolution persistence and workflow progression to JURISDICTION_COMPLETE.
- R012 — proved via pytest + runbook showing RequirementSet persistence with provenance and workflow progression to RESEARCH_COMPLETE.

## New Requirements Surfaced
- none

## Requirements Invalidated or Re-scoped
- none

## Deviations
- none

## Known Limitations
- Temporal integration test coverage remains opt-in (`SPS_RUN_TEMPORAL_INTEGRATION=1`); runbook provides the live-runtime proof.

## Follow-ups
- Execute S03 docker-compose end-to-end proof (API + worker + Temporal) for milestone closure.

## Files Created/Modified
- `specs/sps/build-approved/fixtures/phase4/jurisdiction.json` — jurisdiction fixture dataset with support/evidence metadata.
- `specs/sps/build-approved/fixtures/phase4/requirements.json` — requirements fixture dataset with rankings, freshness, and provenance.
- `src/sps/fixtures/phase4.py` — Phase 4 fixture loader/validator models.
- `src/sps/db/models.py` — JurisdictionResolution and RequirementSet ORM models with JSONB provenance.
- `alembic/versions/b2c4f7e8a901_jurisdiction_requirements.py` — migration for new artifact tables and indexes.
- `src/sps/workflows/permit_case/activities.py` — persistence activities for jurisdiction/requirements.
- `src/sps/workflows/permit_case/workflow.py` — workflow path to JURISDICTION_COMPLETE and RESEARCH_COMPLETE.
- `src/sps/workflows/worker.py` — activity registration updates.
- `src/sps/api/contracts/cases.py` — response contracts for jurisdiction/requirements endpoints.
- `src/sps/api/routes/cases.py` — GET endpoints for artifact inspection.
- `tests/m004_s02_jurisdiction_requirements_workflow_test.py` — fixture schema + API/DB assertions.
- `scripts/verify_m004_s02.sh` — docker-compose runbook for workflow progression and artifact inspection.

## Forward Intelligence
### What the next slice should know
- The S02 runbook seeds CASE-EXAMPLE-001 and validates API responses plus guard denial rows; reuse this for S03 when wiring full docker-compose proof.

### What's fragile
- Temporal integration tests are env-gated; forgetting `SPS_RUN_TEMPORAL_INTEGRATION=1` leaves some workflow coverage skipped.

### Authoritative diagnostics
- `case_transition_ledger` rows + `jurisdiction_resolutions`/`requirement_sets` tables confirm activity writes; runbook logs show state transitions and API payloads.

### What assumptions changed
- Assumed workflow progression proof would be entirely in pytest; in practice the docker-compose runbook is the authoritative integration proof right now.
