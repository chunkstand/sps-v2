---
id: T01
parent: S01
milestone: M009-ct4p0u
provides:
  - audit event persistence for review decisions and state transitions
key_files:
  - src/sps/db/models.py
  - src/sps/audit/events.py
  - src/sps/workflows/permit_case/activities.py
  - src/sps/api/routes/reviews.py
  - alembic/versions/a9b3c2d4e6f7_audit_events.py
  - tests/m009_s01_audit_events_test.py
key_decisions:
  - Kept AuditEvent in the shared models.py module to match existing ORM layout.
patterns_established:
  - emit_audit_event helper for transactional audit writes
observability_surfaces:
  - Postgres audit_events table (action, correlation_id, request_id)
duration: 1h
verification_result: failed (pytest missing)
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Persist audit events for review decisions and transitions

**Added audit_events persistence with transactional emission hooks for review decisions and state transitions.**

## What Happened
- Added AuditEvent ORM model and Alembic migration for the audit_events table with correlation/request metadata.
- Implemented emit_audit_event helper and wired it into review decision creation and state transition apply/deny paths.
- Added integration test coverage for review decision and transition audit rows.

## Verification
- `pytest tests/m009_s01_audit_events_test.py` (failed: pytest not installed in current environment)
- `python3 -m pytest tests/m009_s01_audit_events_test.py` (failed: pytest module missing)

## Diagnostics
- Query `audit_events` by `action`, `correlation_id`, or `request_id` to verify persisted audit rows.

## Deviations
- Stored AuditEvent in `src/sps/db/models.py` instead of creating a new `src/sps/db/models/audit_events.py` module to match existing ORM layout.

## Known Issues
- Verification is blocked because pytest is not installed in the current environment.

## Files Created/Modified
- `src/sps/db/models.py` — added AuditEvent ORM model.
- `src/sps/audit/__init__.py` — created audit module package.
- `src/sps/audit/events.py` — emit_audit_event helper for transactional audit rows.
- `src/sps/api/routes/reviews.py` — emits audit event on review decision creation.
- `src/sps/workflows/permit_case/activities.py` — emits audit event on state transition apply/deny.
- `alembic/versions/a9b3c2d4e6f7_audit_events.py` — migration creating audit_events table.
- `tests/m009_s01_audit_events_test.py` — integration tests for audit event persistence.
