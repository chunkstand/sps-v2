---
id: T03
parent: S01
milestone: M013-n6p1tg
provides:
  - Postgres-backed integration tests covering admin portal support intent → review → apply with audit events
key_files:
  - tests/m013_s01_admin_portal_support_governance_test.py
  - src/sps/api/routes/admin_portal_support.py
key_decisions:
  - Admin portal support reviews require reviewer role (admin-only tokens denied).
patterns_established:
  - Postgres-backed ASGI integration test asserts audit_event actions and authoritative metadata rows.
observability_surfaces:
  - audit_events rows for ADMIN_PORTAL_SUPPORT_* actions; admin_portal_support_intents/reviews and portal_support_metadata tables; 409 review_required + 403 role_denied errors.
duration: 2h
verification_result: failed
completed_at: 2026-03-16
blocker_discovered: false
---

# T03: Prove intent → review → apply with audit trail

**Added end-to-end admin portal support governance integration tests plus reviewer-only RBAC enforcement for reviews.**

## What Happened
- Replaced the placeholder test with a Postgres-backed integration suite that exercises intent creation, reviewer approval, apply, and audit-event assertions.
- Added RBAC coverage for reviewer-only apply denial and admin-only review denial, including audit-event absence checks for denied actions.
- Tightened the review endpoint to require reviewer role even when admin is present, aligning governance separation of duties.
- Recorded the reviewer-only RBAC decision in the decisions register.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s01_admin_portal_support_governance_test.py -v` (failed: Postgres not ready).
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s01_admin_portal_support_governance_test.py -k "apply_before_review" -v` (failed: Postgres not ready).
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s01_admin_portal_support_governance_test.py -k "apply_before_review and error_code" -v` (failed: Postgres not ready).

## Diagnostics
- Inspect with `SELECT * FROM admin_portal_support_intents;`, `admin_portal_support_reviews;`, `portal_support_metadata;`, and `audit_events` filtered by correlation_id.
- Failure responses: HTTP 409 `review_required` for apply-before-review; HTTP 403 `role_denied` for wrong-role access.

## Deviations
- Enforced reviewer-only access for admin portal support reviews by adding a role check (plan did not explicitly call for runtime change).

## Known Issues
- Integration tests require a running Postgres instance; all verification commands failed with `Postgres not ready`.

## Files Created/Modified
- `tests/m013_s01_admin_portal_support_governance_test.py` — integration tests for intent/review/apply flow with audit assertions and RBAC denial checks.
- `src/sps/api/routes/admin_portal_support.py` — reviewer-only guard added to review endpoint.
- `.gsd/DECISIONS.md` — added reviewer-only admin portal support review RBAC decision.
