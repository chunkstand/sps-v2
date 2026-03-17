---
id: T03
parent: S02
milestone: M013-n6p1tg
provides:
  - Docker-compose runbook covering governed admin intent→review→apply flows with audit assertions for portal support, source rules, and incentive programs.
key_files:
  - scripts/verify_m013_s02.sh
  - tests/m013_s02_admin_source_rules_governance_test.py
  - .gsd/milestones/M013-n6p1tg/slices/S02/S02-PLAN.md
key_decisions:
  - None
patterns_established:
  - Runbook uses assert_postgres helpers with deterministic IDs + cleanup for repeatable governance checks.
observability_surfaces:
  - runbook outputs audit_event/table assertions via docker compose exec
  - audit_events, admin_* intent/review tables, source_rules, incentive_programs, portal_support_metadata
duration: 1.4h
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T03: Add docker-compose runbook for admin governance across all change types

**Added a docker-compose runbook that exercises portal support, source rule, and incentive program governance flows with Postgres audit assertions.**

## What Happened
- Implemented `scripts/verify_m013_s02.sh` to start the compose stack, launch the API, run intent→review→apply for all three admin change types, and assert audit_event/table state via containerized psql.
- Ensured runbook repeatability by deleting deterministic intent/review rows and related audit events before running.
- Updated source-rule test names to include `role_denied` so the slice verification filter is meaningful.
- Added role-denied verification coverage to the slice plan verification checklist.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_source_rules_governance_test.py -v`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_incentive_programs_governance_test.py -v`
- `bash scripts/verify_m013_s02.sh`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_source_rules_governance_test.py -v -k review_required`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_incentive_programs_governance_test.py -v -k review_required`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_source_rules_governance_test.py -v -k role_denied`

## Diagnostics
- Run `bash scripts/verify_m013_s02.sh` and inspect `audit_events`, `admin_*_intents`, `admin_*_reviews`, `source_rules`, `incentive_programs`, and `portal_support_metadata` for the runbook correlation IDs.

## Deviations
- None.

## Known Issues
- None.

## Files Created/Modified
- `scripts/verify_m013_s02.sh` — runbook for governed admin intent/review/apply flows with Postgres audit assertions.
- `tests/m013_s02_admin_source_rules_governance_test.py` — renamed role-denied tests to satisfy verification filter.
- `.gsd/milestones/M013-n6p1tg/slices/S02/S02-PLAN.md` — added role-denied verification step and marked T03 complete.
