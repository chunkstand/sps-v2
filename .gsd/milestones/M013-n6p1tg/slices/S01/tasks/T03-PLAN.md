---
estimated_steps: 5
estimated_files: 2
---

# T03: Prove intent → review → apply with audit trail

**Slice:** S01 — Admin intent/review/apply for portal support metadata
**Milestone:** M013-n6p1tg

## Description
Add a Postgres-backed integration test that exercises the full admin governance flow and asserts audit evidence, RBAC, and fail-closed apply behavior.

## Steps
1. Create `tests/m013_s01_admin_portal_support_governance_test.py` using the existing Postgres-backed test pattern (`_wait_for_postgres_ready`, `_migrate_db`, `_reset_db`).
2. Configure auth env fixtures and build admin/reviewer JWTs via `tests.helpers.auth_tokens.build_jwt`.
3. Test happy path: create intent → review approve → apply; assert portal_support_metadata row and three audit_events rows.
4. Test denial path: apply before review returns 409 with `error_code=review_required` and no apply audit event.
5. Test RBAC path: reviewer cannot apply; admin cannot review (403 with role_denied).

## Must-Haves
- [ ] Tests assert authoritative metadata update and audit_events entries for intent/review/apply.
- [ ] Tests cover RBAC and apply-before-review denial behavior.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m013_s01_admin_portal_support_governance_test.py -v`

## Observability Impact
- Signals exercised: `audit_events` rows for `ADMIN_PORTAL_SUPPORT_INTENT_CREATED`, `ADMIN_PORTAL_SUPPORT_REVIEW_RECORDED`, `ADMIN_PORTAL_SUPPORT_APPLIED` with `intent_id`/`review_id` references (no raw payloads).
- Inspection path: query `admin_portal_support_intents`, `admin_portal_support_reviews`, `portal_support_metadata`, and `audit_events` to confirm workflow state transitions.
- Failure visibility: apply-before-review returns HTTP 409 `error_code=review_required` and emits no apply audit event; RBAC failures return 403 `role_denied`.

## Inputs
- `src/sps/api/routes/admin_portal_support.py` — admin portal support endpoints.
- `tests/helpers/auth_tokens.py` — JWT helpers for role-based access.

## Expected Output
- `tests/m013_s01_admin_portal_support_governance_test.py` — integration tests for admin governance flow.
