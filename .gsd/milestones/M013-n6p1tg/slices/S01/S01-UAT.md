# S01: Admin intent/review/apply for portal support metadata — UAT

**Milestone:** M013-n6p1tg
**Written:** 2026-03-16

## UAT Type
- UAT mode: live-runtime
- Why this mode is sufficient: The slice is governed by runtime RBAC, audit-event emission, and Postgres persistence; live API + Postgres checks prove the authority boundary and audit trail.

## Preconditions
- `docker-compose up -d postgres` is running.
- `alembic upgrade heads` has been applied to the Postgres instance.
- API is running with JWT auth configured (issuer, audience, secret).

## Smoke Test
- Run `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s01_admin_portal_support_governance_test.py -k "happy_path" -v` and confirm it passes.

## Test Cases
### 1. Intent → review → apply updates portal support metadata
1. POST `/api/v1/admin/portal-support/intents` as an admin with `intent_id=INTENT-PSM-UAT-001` and `portal_family=PACIFIC_GAS`.
2. POST `/api/v1/admin/portal-support/reviews` as a reviewer with `review_id=REVIEW-PSM-UAT-001` approving the intent.
3. POST `/api/v1/admin/portal-support/apply/INTENT-PSM-UAT-001` as admin.
4. **Expected:** API returns 200 with `portal_support_metadata_id`, and Postgres `portal_support_metadata` row exists for `PACIFIC_GAS` with the requested support level.

### 2. Apply before review is denied and no apply audit event exists
1. POST `/api/v1/admin/portal-support/intents` as admin with `intent_id=INTENT-PSM-UAT-002`.
2. POST `/api/v1/admin/portal-support/apply/INTENT-PSM-UAT-002` as admin without a review.
3. **Expected:** HTTP 409 with `error_code=review_required`, and no `ADMIN_PORTAL_SUPPORT_APPLIED` audit_events row exists for the intent.

### 3. Reviewer cannot apply an intent
1. Create an intent + approval using admin + reviewer roles.
2. POST `/api/v1/admin/portal-support/apply/<intent_id>` with a reviewer token.
3. **Expected:** HTTP 403 with `error_code=role_denied` and `required_roles` including `admin`.

### 4. Admin cannot record a review
1. Create an intent with an admin token.
2. POST `/api/v1/admin/portal-support/reviews` with the admin token.
3. **Expected:** HTTP 403 with `error_code=role_denied` and `required_roles` including `reviewer`.

## Edge Cases
### Duplicate review idempotency
1. POST the same review twice with different `review_id` but the same `idempotency_key`.
2. **Expected:** HTTP 409 with `error_code=review_idempotency_conflict` and no additional audit event for the duplicate.

## Failure Signals
- Missing `ADMIN_PORTAL_SUPPORT_INTENT_CREATED/REVIEW_RECORDED/APPLIED` audit_events rows after successful API responses.
- `portal_support_metadata` row not updated after apply.
- Apply-before-review does not return 409 `review_required`.
- Reviewer/admin role denials do not return 403 `role_denied`.

## Requirements Proved By This UAT
- R035 — Admin portal support metadata changes require intent/review/apply with audit trails.

## Not Proven By This UAT
- Governed changes for source rules or incentive programs.
- Docker-compose runbook proof for all three admin change types (S02).

## Notes for Tester
- Audit event payloads intentionally exclude raw portal support payloads; expect only intent/review IDs.
- Use `SELECT action, correlation_id FROM audit_events WHERE correlation_id = <intent_id>` for quick audit inspection.
