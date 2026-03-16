---
id: T02
parent: S01
milestone: M005-j3c8qk
provides:
  - compliance guard + workflow transition wiring + compliance API read surface
key_files:
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/workflow.py
  - src/sps/api/contracts/cases.py
  - src/sps/api/routes/cases.py
  - invariants/sps/guard-assertions.yaml
key_decisions:
  - Added guard assertion INV-SPS-COMP-001 with a 30-day compliance evaluation freshness window for RESEARCH_COMPLETE → COMPLIANCE_COMPLETE.
patterns_established:
  - Compliance read endpoint mirrors requirements/jurisdiction 404/409/log patterns and returns list wrappers.
observability_surfaces:
  - case_transition_ledger denial payloads include guard_assertion_id + normalized_business_invariants for COMPLIANCE_* denials
  - cases.compliance_* structured logs and GET /api/v1/cases/{case_id}/compliance
duration: 1h
verification_result: partial
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Wire compliance guard, workflow transition, and API read surface

**Added compliance guard enforcement, workflow compliance persistence/transition wiring, and a compliance read endpoint with structured logging.**

## What Happened
- Added COMPLIANCE_REQUIRED/COMPLIANCE_FRESHNESS guard logic to `apply_state_transition`, including guard assertion ID + normalized invariants and a 30‑day freshness window.
- Wired PermitCaseWorkflow to persist compliance evaluations and attempt RESEARCH_COMPLETE → COMPLIANCE_COMPLETE transitions with denial logging.
- Added ComplianceEvaluation API response models and `/api/v1/cases/{case_id}/compliance` endpoint with 404/409 behavior and cases.compliance_* logging.
- Registered new guard assertion metadata for compliance invariants.

## Verification
- `.venv/bin/python -m pytest tests/m005_s01_compliance_workflow_test.py -v -s` ✅ (passes fixture schema test)
- `.venv/bin/python -m pytest tests/m005_s01_compliance_workflow_test.py -k "progression" -v` ❌ (no tests selected)
- `.venv/bin/python -m pytest tests/m005_s01_compliance_workflow_test.py -k "guard_denial" -v -s` ❌ (no tests selected)

## Diagnostics
- Inspect denial ledger payloads: `SELECT event_type, guard_assertion_id, normalized_business_invariants FROM case_transition_ledger WHERE event_type LIKE 'COMPLIANCE_%' ORDER BY occurred_at DESC;`
- API surface: `GET /api/v1/cases/{case_id}/compliance` with `cases.compliance_*` logs for fetched/missing/failure states.

## Deviations
- None.

## Known Issues
- Progression/guard_denial pytest selectors currently find no tests; integration coverage for these cases remains to be added (planned in T03).

## Files Created/Modified
- `src/sps/workflows/permit_case/activities.py` — added compliance guard branch, event types, and guard assertion ID.
- `src/sps/workflows/permit_case/workflow.py` — persisted compliance evaluation and added COMPLIANCE_COMPLETE transition.
- `src/sps/api/contracts/cases.py` — added compliance response models + list wrapper.
- `src/sps/api/routes/cases.py` — added compliance endpoint + logging and row mapping.
- `invariants/sps/guard-assertions.yaml` — added INV-SPS-COMP-001 metadata.
- `.gsd/milestones/M005-j3c8qk/slices/S01/S01-PLAN.md` — marked T02 complete + verification diagnostic step.
- `.gsd/DECISIONS.md` — recorded compliance guard assertion/freshness window decision.
- `.gsd/STATE.md` — advanced next action to T03.
