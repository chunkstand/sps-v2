---
id: T02
parent: S02
milestone: M013-n6p1tg
provides:
  - governed incentive program intent/review/apply workflow with authoritative tables, audit events, and RBAC enforcement
key_files:
  - src/sps/db/models.py
  - alembic/versions/c8d1e2f3a4b5_admin_incentive_programs_governance.py
  - src/sps/api/routes/admin_incentive_programs.py
  - src/sps/services/admin_incentive_programs.py
  - tests/m013_s02_admin_incentive_programs_governance_test.py
key_decisions:
  - None
patterns_established:
  - Incentive program governance mirrors portal support/source rules intent→review→apply with reviewer-only approvals and fail-closed apply
observability_surfaces:
  - audit_events rows plus admin_incentive_program_intents/admin_incentive_program_reviews/incentive_programs tables for correlation_id inspection
  - HTTP 409 review_required and 403 role_denied responses for failure states
duration: 2h 10m
verification_result: partial
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Implement governed incentive program intent/review/apply flow

**Added governed incentive program intent/review/apply endpoints with authoritative tables, audit events, and RBAC gating.**

## What Happened
- Added incentive program ORM models and governance tables with idempotency constraints plus Alembic migration.
- Implemented incentive program contracts, services, and API routes mirroring portal support/source rules governance with reviewer-only approvals and fail-closed apply.
- Added integration tests for happy path, review-required denial, reviewer/admin RBAC enforcement, and audit event payloads; aligned review-required test naming for slice diagnostics.
- Registered the incentive program router in the API main wiring.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_incentive_programs_governance_test.py -v`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_source_rules_governance_test.py -v`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_source_rules_governance_test.py -v -k review_required`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_incentive_programs_governance_test.py -v -k review_required`
- `bash scripts/verify_m013_s02.sh` (failed: script missing)

## Diagnostics
- Query `admin_incentive_program_intents`, `admin_incentive_program_reviews`, `incentive_programs`, and `audit_events` by `correlation_id` to confirm intent/review/apply audit coverage.
- Failure surfaces: 409 `review_required` or 403 `role_denied` responses; missing `ADMIN_INCENTIVE_PROGRAM_APPLIED` audit rows.

## Deviations
- None.

## Known Issues
- `scripts/verify_m013_s02.sh` is missing; slice-level runbook verification still fails until T03 provides the script.

## Files Created/Modified
- `src/sps/db/models.py` — added incentive program governance ORM models.
- `alembic/versions/c8d1e2f3a4b5_admin_incentive_programs_governance.py` — migration for incentive program tables.
- `src/sps/api/contracts/admin_incentive_programs.py` — request/response contracts for incentive program governance.
- `src/sps/services/admin_incentive_programs.py` — service helpers for intents, reviews, and apply.
- `src/sps/api/routes/admin_incentive_programs.py` — governed incentive program endpoints with audit events.
- `src/sps/api/main.py` — registered incentive program router.
- `tests/m013_s02_admin_incentive_programs_governance_test.py` — integration tests for incentive program governance.
- `tests/m013_s02_admin_source_rules_governance_test.py` — renamed review-required test for slice diagnostics.
