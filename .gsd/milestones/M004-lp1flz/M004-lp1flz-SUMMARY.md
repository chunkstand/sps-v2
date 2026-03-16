---
id: M004-lp1flz
provides:
  - Intake, jurisdiction, and requirements workers wired into PermitCaseWorkflow with fixture-backed artifacts and end-to-end runbook proof to RESEARCH_COMPLETE
key_decisions:
  - Delete Phase 4 fixture artifact rows by fixture IDs before reuse to avoid idempotent conflicts during runbook overrides
patterns_established:
  - Fixture-backed jurisdiction/requirements activities persist JSONB provenance and advance workflow via guarded transitions
observability_surfaces:
  - case_transition_ledger rows plus jurisdiction_resolutions/requirement_sets tables; scripts/verify_m004_s01.sh, verify_m004_s02.sh, verify_m004_s03.sh output
requirement_outcomes:
  - id: R010
    from_status: active
    to_status: validated
    proof: tests/m004_s01_intake_api_workflow_test.py and scripts/verify_m004_s01.sh demonstrate intake persistence and INTAKE_COMPLETE transition
  - id: R011
    from_status: active
    to_status: validated
    proof: tests/m004_s02_jurisdiction_requirements_workflow_test.py and scripts/verify_m004_s02.sh show jurisdiction persistence and JURISDICTION_COMPLETE
  - id: R012
    from_status: active
    to_status: validated
    proof: tests/m004_s02_jurisdiction_requirements_workflow_test.py and scripts/verify_m004_s02.sh show requirements persistence with provenance and RESEARCH_COMPLETE
duration: 9h55m
verification_result: passed
completed_at: 2026-03-15
---

# M004-lp1flz: Phase 4 — intake, jurisdiction, and requirements workers

**Spec-derived intake now creates PermitCase + Project, fixture-backed jurisdiction/requirements persist with provenance, and live workflows reach RESEARCH_COMPLETE via docker-compose.**

## What Happened
The milestone introduced a spec-derived intake contract and API path that persist PermitCase + Project and advance the workflow to INTAKE_COMPLETE under guarded transitions. It then added Phase 4 jurisdiction/requirements fixtures, persistence models with JSONB provenance, and activities wired into PermitCaseWorkflow to reach JURISDICTION_COMPLETE and RESEARCH_COMPLETE. Finally, an end-to-end docker-compose runbook proved the full API → Temporal worker → Postgres path using fixture overrides with cleanup by fixture IDs to keep runs repeatable.

## Cross-Slice Verification
- **Intake → INTAKE_COMPLETE**: `tests/m004_s01_intake_api_workflow_test.py` and `scripts/verify_m004_s01.sh` show spec-derived intake creates PermitCase + Project and applies the guarded INTAKE_COMPLETE transition.
- **Jurisdiction + requirements persistence**: `tests/m004_s02_jurisdiction_requirements_workflow_test.py` and `scripts/verify_m004_s02.sh` confirm JurisdictionResolution/RequirementSet persistence with provenance and workflow progression through JURISDICTION_COMPLETE and RESEARCH_COMPLETE.
- **Live docker-compose progression to RESEARCH_COMPLETE**: `scripts/verify_m004_s03.sh` exercises real API + Temporal worker + Postgres and verifies persisted artifacts and ledger transitions for the runtime case.

## Requirement Changes
- R010: active → validated — `tests/m004_s01_intake_api_workflow_test.py` + `scripts/verify_m004_s01.sh`.
- R011: active → validated — `tests/m004_s02_jurisdiction_requirements_workflow_test.py` + `scripts/verify_m004_s02.sh`.
- R012: active → validated — `tests/m004_s02_jurisdiction_requirements_workflow_test.py` + `scripts/verify_m004_s02.sh`.

## Forward Intelligence
### What the next milestone should know
- The S03 runbook restarts the workflow after intake and relies on fixture case_id overrides; keep the cleanup-by-fixture-ID step to avoid idempotent skips.

### What's fragile
- Fixture ID reuse across runs — without deleting artifact rows by fixture ID, the runtime case_id may never receive new rows and guards will deny advancement.

### Authoritative diagnostics
- `case_transition_ledger` plus `jurisdiction_resolutions`/`requirement_sets` rows for the runtime case_id — definitive evidence of progression and persistence.

### What assumptions changed
- Clearing by fixture case_id alone was insufficient; fixture ID collisions required explicit deletion by fixture IDs.

## Files Created/Modified
- `src/sps/api/contracts/intake.py` — spec-derived intake request/response models.
- `src/sps/api/routes/cases.py` — intake + jurisdiction/requirements endpoints.
- `src/sps/workflows/permit_case/activities.py` — intake/jurisdiction/requirements persistence activities.
- `src/sps/workflows/permit_case/workflow.py` — workflow wiring to INTAKE/JURISDICTION/RESEARCH states.
- `src/sps/fixtures/phase4.py` — Phase 4 fixture loader/validators.
- `specs/sps/build-approved/fixtures/phase4/jurisdiction.json` — jurisdiction fixture dataset.
- `specs/sps/build-approved/fixtures/phase4/requirements.json` — requirements fixture dataset.
- `alembic/versions/b2c4f7e8a901_jurisdiction_requirements.py` — migration for artifact tables.
- `scripts/verify_m004_s01.sh` — intake runbook.
- `scripts/verify_m004_s02.sh` — jurisdiction/requirements runbook.
- `scripts/verify_m004_s03.sh` — docker-compose end-to-end runbook.
