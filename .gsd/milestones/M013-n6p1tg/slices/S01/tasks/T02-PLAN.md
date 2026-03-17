---
estimated_steps: 5
estimated_files: 4
---

# T02: Wire admin intent/review/apply API with audit events

**Slice:** S01 — Admin intent/review/apply for portal support metadata
**Milestone:** M013-n6p1tg

## Description
Implement the admin API surface for portal support intent creation, review approval, and governed apply, with RBAC enforcement and audit-event emission.

## Steps
1. Create `src/sps/services/admin_portal_support.py` with helpers to load intents, validate approved reviews, and upsert portal_support_metadata inside a single DB transaction.
2. Add `src/sps/api/routes/admin_portal_support.py` with endpoints for intent creation (ADMIN), review decision (REVIEWER), and apply (ADMIN); wire to service helpers and emit audit events.
3. Return fail-closed responses for apply without approved review and review idempotency conflicts (HTTP 409 with stable error_code).
4. Emit audit_events for intent/review/apply actions using `emit_audit_event` with correlation/request IDs derived from intent IDs.
5. Register the router in `src/sps/api/main.py` under `/api/v1/admin/portal-support`.

## Must-Haves
- [ ] RBAC enforcement: ADMIN required for intent/apply, REVIEWER required for review.
- [ ] Apply endpoint updates portal_support_metadata only when an approved review exists.
- [ ] Audit events are persisted for intent, review, and apply actions.

## Verification
- `python -m pytest tests/m013_s01_admin_portal_support_governance_test.py -k "rbac" -v`

## Observability Impact
- Signals added/changed: audit events with actions `ADMIN_PORTAL_SUPPORT_INTENT_CREATED`, `ADMIN_PORTAL_SUPPORT_REVIEW_RECORDED`, `ADMIN_PORTAL_SUPPORT_APPLIED`.
- How a future agent inspects this: query `audit_events` and `portal_support_metadata` tables for intent/review/apply IDs.
- Failure state exposed: apply without approval returns HTTP 409 and no audit_event row is inserted for apply.

## Inputs
- `src/sps/db/models.py` — admin portal support ORM models.
- `src/sps/api/contracts/admin_portal_support.py` — request/response schema.

## Expected Output
- `src/sps/services/admin_portal_support.py` — domain helper for governed apply.
- `src/sps/api/routes/admin_portal_support.py` — admin portal support router.
- `src/sps/api/main.py` — router registration for admin endpoints.
