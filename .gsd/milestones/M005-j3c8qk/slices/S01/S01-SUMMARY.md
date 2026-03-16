---
id: S01
parent: M005-j3c8qk
milestone: M005-j3c8qk
provides:
  - ComplianceEvaluation fixtures, persistence, guarded workflow advancement, and compliance API read surface
requires:
  - none
affects:
  - S02
key_files:
  - src/sps/fixtures/phase5.py
  - specs/sps/build-approved/fixtures/phase5/compliance.json
  - src/sps/db/models.py
  - alembic/versions/e1c2f4b5a6c7_compliance_evaluations.py
  - src/sps/workflows/permit_case/contracts.py
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/workflow.py
  - src/sps/api/contracts/cases.py
  - src/sps/api/routes/cases.py
  - invariants/sps/guard-assertions.yaml
  - tests/m005_s01_compliance_workflow_test.py
key_decisions:
  - Enforce a 30-day compliance evaluation freshness window with guard assertion INV-SPS-COMP-001 on RESEARCH_COMPLETE → COMPLIANCE_COMPLETE
patterns_established:
  - Phase 5 fixture selector/override mirrors Phase 4 deterministic fixture loading
  - Compliance read endpoint mirrors jurisdiction/requirements 404/409 patterns
observability_surfaces:
  - compliance_activity.persisted log, cases.compliance_fetched log, compliance_evaluations table, case_transition_ledger denial events
  - GET /api/v1/cases/{case_id}/compliance
  - SELECT event_type, guard_assertion_id, normalized_business_invariants FROM case_transition_ledger WHERE event_type LIKE 'COMPLIANCE_%'
drill_down_paths:
  - .gsd/milestones/M005-j3c8qk/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M005-j3c8qk/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M005-j3c8qk/slices/S01/tasks/T03-SUMMARY.md
duration: 3h
verification_result: passed
completed_at: 2026-03-15
---

# S01: Compliance evaluation artifacts + workflow advance

**Fixture-backed ComplianceEvaluation persistence, guarded workflow advancement to COMPLIANCE_COMPLETE, and compliance read API proven via Temporal/Postgres integration tests.**

## What Happened
Added Phase 5 compliance fixtures and schema, a ComplianceEvaluation ORM + migration with provenance/evidence JSONB payloads, and a deterministic persistence activity. Wired the PermitCaseWorkflow to persist compliance evaluations, enforce a freshness guard on RESEARCH_COMPLETE → COMPLIANCE_COMPLETE, and exposed a compliance read endpoint. Completed integration tests validating fixture schema, workflow progression, API payload fidelity, and guard denials.

## Verification
- SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s01_compliance_workflow_test.py -v -s
- SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s01_compliance_workflow_test.py -k "guard_denial" -v -s

## Requirements Advanced
- R013 — Compliance evaluation artifacts persisted, guarded advancement added, and API read surface provided.

## Requirements Validated
- R013 — Temporal/Postgres integration tests prove compliance evaluation persistence, COMPLIANCE_COMPLETE transition, and API read-back.

## New Requirements Surfaced
- none

## Requirements Invalidated or Re-scoped
- none

## Deviations
- none

## Known Limitations
- Incentive assessment artifacts and runbook proof remain for S02/S03.

## Follow-ups
- Implement incentive assessment artifacts and COMPLIANCE_COMPLETE → INCENTIVES_COMPLETE progression (S02).

## Files Created/Modified
- `src/sps/fixtures/phase5.py` — Phase 5 compliance fixture schema + selector helpers.
- `specs/sps/build-approved/fixtures/phase5/compliance.json` — Fixture dataset with rule results, blockers, warnings, and provenance.
- `src/sps/db/models.py` — ComplianceEvaluation ORM mapping.
- `alembic/versions/e1c2f4b5a6c7_compliance_evaluations.py` — compliance_evaluations migration.
- `src/sps/workflows/permit_case/contracts.py` — compliance persistence contract.
- `src/sps/workflows/permit_case/activities.py` — compliance activity + guard branch.
- `src/sps/workflows/permit_case/workflow.py` — workflow wiring for compliance persistence + transition.
- `src/sps/api/contracts/cases.py` — compliance API response models.
- `src/sps/api/routes/cases.py` — compliance endpoint + logging.
- `tests/m005_s01_compliance_workflow_test.py` — fixture schema, progression, API, and guard denial tests.

## Forward Intelligence
### What the next slice should know
- Compliance evaluations are fixture-backed and idempotent; incentive assessment should mirror the same fixture override + provenance JSONB patterns to keep guard behavior deterministic.

### What's fragile
- Guard freshness relies on evaluated_at timestamps in fixtures; stale timestamps will deny COMPLIANCE_COMPLETE progression.

### Authoritative diagnostics
- `compliance_activity.persisted` logs and `compliance_evaluations` rows confirm persistence; `case_transition_ledger` COMPLIANCE_* events confirm guard decisions.

### What assumptions changed
- Compliance progression now requires a fresh evaluation; direct RESEARCH_COMPLETE → COMPLIANCE_COMPLETE without evaluation is denied.
