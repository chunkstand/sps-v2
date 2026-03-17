---
id: S02
parent: M013-n6p1tg
milestone: M013-n6p1tg
provides:
  - governed source rule + incentive program intent/review/apply flows with audit trails and a live runbook across all admin config types
requires:
  - slice: S01
    provides: portal support metadata intent/review/apply governance pattern
affects:
  - none
key_files:
  - src/sps/db/models.py
  - alembic/versions/b7c2d9e4f1a3_admin_source_rules_governance.py
  - alembic/versions/c8d1e2f3a4b5_admin_incentive_programs_governance.py
  - src/sps/services/admin_source_rules.py
  - src/sps/services/admin_incentive_programs.py
  - src/sps/api/routes/admin_source_rules.py
  - src/sps/api/routes/admin_incentive_programs.py
  - tests/m013_s02_admin_source_rules_governance_test.py
  - tests/m013_s02_admin_incentive_programs_governance_test.py
  - scripts/verify_m013_s02.sh
key_decisions:
  - none
patterns_established:
  - Admin config governance follows intent → review → apply with reviewer-only approvals, fail-closed apply, and audit event emission.
observability_surfaces:
  - audit_events plus admin_*_intents/admin_*_reviews/source_rules/incentive_programs tables; runbook assertions via docker compose exec
  - HTTP 409 review_required and 403 role_denied responses
  - scripts/verify_m013_s02.sh
drill_down_paths:
  - .gsd/milestones/M013-n6p1tg/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M013-n6p1tg/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M013-n6p1tg/slices/S02/tasks/T03-SUMMARY.md
duration: 5h
verification_result: passed
completed_at: 2026-03-16
---

# S02: Governed admin changes for source rules + incentive programs with live runbook

**Governed admin source rules and incentive programs now use intent → review → apply workflows with audit trails, proven by integration tests and a live docker-compose runbook across all admin change types.**

## What Happened
Implemented authoritative source rule and incentive program tables plus admin intent/review records, wired governed intent/review/apply endpoints with reviewer-only approvals and fail-closed apply behavior, and extended audit event emission across all admin change types. Added integration tests covering happy paths, review-required denials, and RBAC enforcement. Shipped a docker-compose runbook that provisions the stack, executes portal support/source rule/incentive program governance flows, and asserts audit rows and table state via Postgres.

## Verification
- SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_source_rules_governance_test.py -v
- SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_incentive_programs_governance_test.py -v
- SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_source_rules_governance_test.py -v -k review_required
- SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_incentive_programs_governance_test.py -v -k review_required
- SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_source_rules_governance_test.py -v -k role_denied
- bash scripts/verify_m013_s02.sh

## Requirements Advanced
- R035 — extended governed admin workflows to source rules + incentive programs with audit trails and operational proof.

## Requirements Validated
- R035 — integration tests plus docker-compose runbook prove intent → review → apply governance for portal support, source rules, and incentive programs.

## New Requirements Surfaced
- none

## Requirements Invalidated or Re-scoped
- none

## Deviations
- none

## Known Limitations
- none

## Follow-ups
- none

## Files Created/Modified
- `src/sps/db/models.py` — authoritative source rule and incentive program models plus admin intent/review tables.
- `alembic/versions/b7c2d9e4f1a3_admin_source_rules_governance.py` — source rule governance tables.
- `alembic/versions/c8d1e2f3a4b5_admin_incentive_programs_governance.py` — incentive program governance tables.
- `src/sps/services/admin_source_rules.py` — intent/review/apply helpers with audit emission.
- `src/sps/services/admin_incentive_programs.py` — incentive program governance helpers.
- `src/sps/api/routes/admin_source_rules.py` — governed source rule endpoints.
- `src/sps/api/routes/admin_incentive_programs.py` — governed incentive program endpoints.
- `tests/m013_s02_admin_source_rules_governance_test.py` — integration tests for source rule governance.
- `tests/m013_s02_admin_incentive_programs_governance_test.py` — integration tests for incentive program governance.
- `scripts/verify_m013_s02.sh` — docker-compose runbook proving governance + audit trails for all admin config types.

## Forward Intelligence
### What the next slice should know
- The runbook starts and tears down the docker-compose stack; ensure Postgres is running before filtered pytest runs.

### What's fragile
- Review-required and role-denied pytest filters depend on Postgres availability; start docker compose postgres before re-running individual tests.

### Authoritative diagnostics
- `scripts/verify_m013_s02.sh` — confirms intent/review/apply plus audit rows across portal support, source rules, and incentive programs.

### What assumptions changed
- "Governed admin changes required only for portal support metadata" — now applies to source rules and incentive programs with runbook proof.
