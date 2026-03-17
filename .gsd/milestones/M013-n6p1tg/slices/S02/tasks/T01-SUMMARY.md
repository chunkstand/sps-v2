---
id: T01
parent: S02
milestone: M013-n6p1tg
provides:
  - governed source rules intent/review/apply workflow with audit trail
key_files:
  - src/sps/db/models.py
  - alembic/versions/b7c2d9e4f1a3_admin_source_rules_governance.py
  - src/sps/api/routes/admin_source_rules.py
  - tests/m013_s02_admin_source_rules_governance_test.py
key_decisions:
  - None
patterns_established:
  - Admin source rule governance mirrors portal support intent/review/apply flow with reviewer-only approvals
observability_surfaces:
  - audit_events rows plus admin_source_rule_intents/admin_source_rule_reviews/source_rules tables
  - API error codes: 409 review_required, 403 role_denied
duration: 1.5h
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Implement governed source rules intent/review/apply flow

**Added governed source rules intent/review/apply endpoints with authoritative tables, reviewer-only gating, and audit event coverage.**

## What Happened
- Added source rule models plus admin intent/review tables with indexes and idempotency constraints.
- Created Alembic migration merging existing heads and provisioning source rule governance tables.
- Implemented contracts, service helpers, and API routes for intent creation, reviewer approvals, and fail-closed apply with audit events.
- Registered the new admin source rules router and added integration tests covering success and denial paths.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_source_rules_governance_test.py -v`
- Slice verification still pending for incentive program tests and runbook (T02/T03).

## Diagnostics
- Inspect `admin_source_rule_intents`, `admin_source_rule_reviews`, `source_rules`, and `audit_events` for correlation_id.
- Failure surfaces: HTTP 409 `review_required`, HTTP 403 `role_denied`, missing `ADMIN_SOURCE_RULE_APPLIED` audit rows.

## Deviations
- None.

## Known Issues
- None.

## Files Created/Modified
- `src/sps/db/models.py` — added source rule and admin governance ORM models.
- `alembic/versions/b7c2d9e4f1a3_admin_source_rules_governance.py` — migration for source rule governance tables (merge heads).
- `src/sps/services/admin_source_rules.py` — intent/review/apply helpers with gating and upsert logic.
- `src/sps/api/contracts/admin_source_rules.py` — request/response schemas for source rule governance.
- `src/sps/api/routes/admin_source_rules.py` — governed admin endpoints with audit events.
- `src/sps/api/main.py` — router registration for admin source rules.
- `tests/m013_s02_admin_source_rules_governance_test.py` — integration coverage for success, review-required, and RBAC denial paths.
