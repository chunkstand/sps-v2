---
id: T02
parent: S02
milestone: M008-z1k9mp
provides:
  - docker-compose reviewer runbook covering queue → evidence → decisions with threshold enforcement assertions
key_files:
  - scripts/verify_m008_s02.sh
key_decisions:
  - reset review_decisions between threshold scenarios to keep rolling-quarter rates deterministic
patterns_established:
  - runbook seeds reviewer history with pg_exec + per-scenario truncation and asserts API + Postgres outcomes
observability_surfaces:
  - runbook stdout includes reviewer API responses and Postgres summary output
  - Postgres assertions via scripts/lib/assert_postgres.sh
  - blocked response payload in stdout
duration: 1.5h
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Add docker-compose runbook proving reviewer flow + thresholds

**Added a docker-compose runbook that exercises reviewer queue/evidence/decision flows and validates independence thresholds against live Postgres.**

## What Happened
- Implemented `scripts/verify_m008_s02.sh` to boot Postgres, apply migrations, seed queue cases, and start the reviewer API.
- Added deterministic reviewer-history seeding and per-scenario truncation so PASS/WARNING/ESCALATION_REQUIRED/BLOCKED thresholds are proven in one run.
- Script now asserts API responses and persisted `review_decisions` fields (including `subject_author_id`) and prints a Postgres summary at the end.

## Verification
- `bash scripts/verify_m008_s02.sh`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/python -m pytest tests/m008_s02_reviewer_independence_thresholds_test.py -v -s`

## Diagnostics
- Runbook prints reviewer queue/evidence responses, decision responses, and a Postgres summary table; failures emit HTTP response bodies via `set -euo pipefail`.

## Deviations
- Adjusted the runbook to truncate `review_decisions` between scenarios to keep rolling-window rates deterministic.

## Known Issues
- None.

## Files Created/Modified
- `scripts/verify_m008_s02.sh` — end-to-end reviewer runbook with threshold seeding, API calls, and Postgres assertions.
- `.gsd/milestones/M008-z1k9mp/slices/S02/tasks/T02-PLAN.md` — added Observability Impact section.
- `.gsd/milestones/M008-z1k9mp/slices/S02/S02-PLAN.md` — marked T02 complete.
- `.gsd/STATE.md` — updated next action.
