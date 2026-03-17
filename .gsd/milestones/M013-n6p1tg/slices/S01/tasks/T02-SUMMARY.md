---
id: T02
parent: S01
milestone: M013-n6p1tg
provides:
  - Admin portal support intent/review/apply API, service helpers, and audit event emission
key_files:
  - src/sps/services/admin_portal_support.py
  - src/sps/api/routes/admin_portal_support.py
  - src/sps/api/main.py
  - .gsd/milestones/M013-n6p1tg/slices/S01/S01-PLAN.md
key_decisions:
  - None
patterns_established:
  - Admin intent/review/apply workflow with RBAC + audit events and 409 failure codes
observability_surfaces:
  - audit_events rows for ADMIN_PORTAL_SUPPORT_* actions; 409 error_code review_required/review_idempotency_conflict
duration: 1.2h
verification_result: failed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Wire admin intent/review/apply API with audit events

**Added admin portal support intent/review/apply endpoints with service helpers, RBAC, and audit-event emission.**

## What Happened
- Added admin portal support service helpers for intent loading, review checks, and metadata upsert behavior.
- Implemented admin portal support router with intent creation (ADMIN), review recording (REVIEWER), and apply (ADMIN) endpoints, including 409 error handling and audit events.
- Wired the new router into the API main entrypoint and updated slice verification checklist for failure-path coverage.

## Verification
- `uv run pytest tests/m013_s01_admin_portal_support_governance_test.py -k "rbac" -v` (deselected; no matching tests yet, exit code 5)
- `uv run pytest tests/m013_s01_admin_portal_support_governance_test.py -v` (failed: placeholder test asserts false)
- `uv run pytest tests/m013_s01_admin_portal_support_governance_test.py -k "apply_before_review" -v` (deselected; no matching tests yet, exit code 5)
- `uv run pytest tests/m013_s01_admin_portal_support_governance_test.py -k "apply_before_review and error_code" -v` (deselected; no matching tests yet, exit code 5)

## Diagnostics
- Inspect `audit_events` for actions `ADMIN_PORTAL_SUPPORT_INTENT_CREATED`, `ADMIN_PORTAL_SUPPORT_REVIEW_RECORDED`, `ADMIN_PORTAL_SUPPORT_APPLIED` keyed by intent_id correlation_id.
- Apply-before-review failure returns HTTP 409 with `error_code=review_required` and no apply audit event.

## Deviations
- None.

## Known Issues
- Portal support governance tests are still placeholders; slice-level verification remains red until T03.
- Audit-event persistence and metadata updates were not directly validated against a live Postgres instance in this task.

## Files Created/Modified
- `src/sps/services/admin_portal_support.py` — service helpers for intent lookup, review validation, and metadata upsert.
- `src/sps/api/routes/admin_portal_support.py` — admin portal support endpoints with RBAC and audit events.
- `src/sps/api/main.py` — registered admin portal support router under `/api/v1/admin/portal-support`.
- `.gsd/milestones/M013-n6p1tg/slices/S01/S01-PLAN.md` — added failure-path verification step and marked T02 complete.
- `.gsd/STATE.md` — advanced next action to T03.
