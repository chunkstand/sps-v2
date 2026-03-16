---
id: T02
parent: S03
milestone: M004-lp1flz
provides:
  - End-to-end S03 runbook to drive intake → RESEARCH_COMPLETE with fixture override artifacts
key_files:
  - scripts/verify_m004_s03.sh
key_decisions:
  - Restart the PermitCaseWorkflow after INTAKE_COMPLETE to advance jurisdiction + requirements for intake-created cases.
patterns_established:
  - Runbook clears fixture artifacts by fixture case_id before using the override to avoid idempotent fixture collisions.
observability_surfaces:
  - runbook stdout (postgres_summary + structured_log_hint), worker/api log tails + ledger snapshot on failure
  - case_transition_ledger, jurisdiction_resolutions, requirement_sets tables via assert_postgres
  - docker compose logs worker (expected when worker is containerized)
duration: 1h
verification_result: partial
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Build the S03 end-to-end docker-compose runbook

**Added the S03 runbook that posts intake, restarts the workflow for research, and validates fixture-backed artifacts through RESEARCH_COMPLETE.**

## What Happened
- Added `scripts/verify_m004_s03.sh` patterned on the S01/S02 runbooks to bring up infra, start the API, POST intake, start the worker with `SPS_PHASE4_FIXTURE_CASE_ID_OVERRIDE`, restart the workflow for jurisdiction/research, and assert ledger + artifact + API outputs.
- Added fixture artifact cleanup for the fixture case_id to prevent idempotent inserts from blocking the jurisdiction transition.
- Included API read surface fetches and postgres summaries plus failure diagnostics consistent with existing runbooks.

## Verification
- `bash scripts/verify_m004_s03.sh`
- `./.venv/bin/pytest tests/m004_s03_fixture_override_test.py`
- `docker compose logs worker | grep -E "LookupError|fixture_case_id"` (fails locally because worker is not a docker-compose service; use the runbook worker log file instead).

## Diagnostics
- Run `bash scripts/verify_m004_s03.sh` and inspect its `postgres_summary`, `structured_log_hint`, and ledger snapshot output.
- Use the worker log path printed by the runbook (e.g., `.gsd/runbook/m004_s03_worker_*.log`) for activity-level traces.

## Deviations
- Restarted the workflow after INTAKE_COMPLETE to reach JURISDICTION_COMPLETE/RESEARCH_COMPLETE because the intake-started workflow returns after the initial transition.
- Cleared fixture artifact rows by fixture case_id before running the workflow to avoid idempotent fixture collisions.

## Known Issues
- `docker compose logs worker` is not available because the worker runs as a local process, not a compose service.

## Files Created/Modified
- `scripts/verify_m004_s03.sh` — end-to-end docker-compose runbook for intake → RESEARCH_COMPLETE with fixture override.
