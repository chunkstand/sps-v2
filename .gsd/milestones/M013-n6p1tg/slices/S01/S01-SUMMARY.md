---
id: S01
parent: M013-n6p1tg
milestone: M013-n6p1tg
provides:
  - Admin portal support metadata intent/review/apply governance with audit trail and RBAC enforcement
requires: []
affects:
  - S02
key_files:
  - src/sps/db/models.py
  - alembic/versions/e3a9c4b7d2f1_admin_portal_support_governance.py
  - src/sps/api/contracts/admin_portal_support.py
  - src/sps/services/admin_portal_support.py
  - src/sps/api/routes/admin_portal_support.py
  - src/sps/api/main.py
  - tests/m013_s01_admin_portal_support_governance_test.py
key_decisions:
  - Reviewer approval for admin portal support reviews requires reviewer role (admin-only tokens denied).
patterns_established:
  - Admin intent → reviewer approval → apply flow with audit events and 409 failures for review_required/idempotency conflicts.
observability_surfaces:
  - Postgres tables: admin_portal_support_intents, admin_portal_support_reviews, portal_support_metadata
  - audit_events rows for ADMIN_PORTAL_SUPPORT_INTENT_CREATED / REVIEW_RECORDED / APPLIED
  - HTTP 409 review_required and 403 role_denied failures
  - Diagnostic queries in tests/m013_s01_admin_portal_support_governance_test.py
  - alembic upgrade heads
  - pytest tests/m013_s01_admin_portal_support_governance_test.py

# Test task drill-down

drill_down_paths:
  - .gsd/milestones/M013-n6p1tg/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M013-n6p1tg/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M013-n6p1tg/slices/S01/tasks/T03-SUMMARY.md
duration: 4.5h
verification_result: passed
completed_at: 2026-03-16
---

# S01: Admin intent/review/apply for portal support metadata

**Governed admin intent → review → apply flow for portal support metadata with audit trails and RBAC enforcement, proven via Postgres-backed integration tests.**

## What Happened
Implemented portal support governance across schema, API contracts, service logic, and routes, wiring intent creation, reviewer approvals, and governed apply into the FastAPI app with audit event emission and fail-closed RBAC. Added integration tests that drive the end-to-end intent → review → apply flow, verify audit events and metadata updates, and assert denial behavior for apply-before-review and wrong-role access. Adjusted the test migration helper to upgrade all Alembic heads to support the multi-branch migration history.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s01_admin_portal_support_governance_test.py -v`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s01_admin_portal_support_governance_test.py -k "apply_before_review" -v`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s01_admin_portal_support_governance_test.py -k "apply_before_review and error_code" -v`

## Requirements Advanced
- R035 — Portal support metadata admin changes now flow through governed intent/review/apply endpoints with audit events and RBAC tests.

## Requirements Validated
- none

## New Requirements Surfaced
- none

## Requirements Invalidated or Re-scoped
- none

## Deviations
- Reviewer approval endpoint is reviewer-only (admin tokens are denied) to enforce separation of duties.

## Known Limitations
- Governed admin change workflow is only implemented for portal support metadata; source rules and incentive programs remain for S02.
- No docker-compose runbook proof yet (planned in S02).

## Follow-ups
- Extend the governed admin change workflow to source rules and incentive programs and add the docker-compose runbook proof (S02).

## Files Created/Modified
- `src/sps/db/models.py` — added portal support metadata + admin intent/review ORM models.
- `alembic/versions/e3a9c4b7d2f1_admin_portal_support_governance.py` — migration for portal support governance tables.
- `src/sps/api/contracts/admin_portal_support.py` — request/response contracts for intent/review/apply.
- `src/sps/services/admin_portal_support.py` — service helpers for intent/review/apply enforcement.
- `src/sps/api/routes/admin_portal_support.py` — admin portal support endpoints with RBAC and audit events.
- `src/sps/api/main.py` — router registration for admin portal support routes.
- `tests/m013_s01_admin_portal_support_governance_test.py` — Postgres-backed integration tests + alembic heads migration fix.

## Forward Intelligence
### What the next slice should know
- Tests migrate the database inside a fixture; use `alembic upgrade heads` to handle multi-head migration history.
- Audit event payloads are intentionally minimal (intent_id/review_id only) to avoid raw portal support payload leakage.

### What's fragile
- Alembic multi-head history — any new migration branch must keep test helper using `heads`, not `head`.

### Authoritative diagnostics
- `audit_events` filtered by correlation_id (intent_id) is the most reliable proof of intent/review/apply actions.

### What assumptions changed
- “Admins can review their own intents” — replaced with reviewer-only approval to enforce separation of duties.
