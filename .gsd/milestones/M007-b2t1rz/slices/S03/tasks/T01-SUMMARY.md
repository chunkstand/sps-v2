---
id: T01
parent: S03
milestone: M007-b2t1rz
provides:
  - Phase 7 live submission + tracking runbook with receipt + status assertions
key_files:
  - scripts/verify_m007_s03.sh
  - src/sps/workflows/permit_case/workflow.py
key_decisions:
  - none
patterns_established:
  - Runbook fixtures: parse fixture case IDs + deterministic cleanup before workflow execution
observability_surfaces:
  - scripts/verify_m007_s03.sh output (PASS/FAIL lines, API payloads, Postgres assertions)
duration: 2.5h
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Build Phase 7 runbook for live submission + tracking

**Built a full Phase 7 runbook that boots the stack, drives intake → review decision → submission, captures receipt evidence, ingests external status, and asserts Postgres persistence.**

## What Happened
- Added `scripts/verify_m007_s03.sh` by cloning the M005 lifecycle scaffolding, then layered Phase 4–7 fixture overrides, deterministic fixture cleanup, and the Phase 7 flow (intake → reviewer decision → workflow submission).
- Extended the runbook to fetch submission attempts, read receipt evidence metadata + download URL, ingest a known external status, and assert the corresponding Postgres rows via `scripts/lib/assert_postgres.sh`.
- Fixed a runtime validation bug in `PermitCaseWorkflow` so submission adapter results that already implement `model_dump` are normalized consistently in the workflow sandbox.
- Verified the runbook end-to-end; it now prints explicit PASS lines for receipt evidence + external status assertions.

## Verification
- `bash scripts/verify_m007_s03.sh`
- `rg "runbook.fail" scripts/verify_m007_s03.sh`

## Diagnostics
- Run `bash scripts/verify_m007_s03.sh` and inspect the PASS/FAIL lines.
- Worker/API tails are emitted automatically on failure; ledger snapshots are printed when errors occur.

## Deviations
- Fixed `PermitCaseWorkflow` adapter result normalization to unblock submission execution (not in original task plan but required for runbook verification).

## Known Issues
- None.

## Files Created/Modified
- `scripts/verify_m007_s03.sh` — Phase 7 runbook driving intake, submission, receipt evidence, external status ingestion, and Postgres assertions.
- `src/sps/workflows/permit_case/workflow.py` — Normalize submission adapter activity results via `model_dump` before validation.
- `.gsd/milestones/M007-b2t1rz/slices/S03/S03-PLAN.md` — Marked T01 complete and added failure-path verification check.
- `.gsd/STATE.md` — Updated phase and next action.
