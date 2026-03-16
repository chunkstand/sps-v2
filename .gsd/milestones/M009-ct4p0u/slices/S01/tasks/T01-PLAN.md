---
estimated_steps: 6
estimated_files: 6
---
# T01: Persist audit events for review decisions and transitions

**Slice:** S01 — Audit Events and Minimal Dashboards
**Milestone:** M009-ct4p0u

## Description
Add the AuditEvent schema, persistence wiring, and emission hooks for review decisions and state transition outcomes so the audit trail is queryable from Postgres.

## Steps
1. Add an AuditEvent ORM model + migration with correlation_id/request_id, actor/action, and payload fields.
2. Implement a small audit emitter helper that writes events transactionally alongside the source action.
3. Emit audit events from review decision creation and state transition apply/deny paths.
4. Add integration tests asserting audit rows exist with expected correlation fields and action types.

## Must-Haves
- [ ] AuditEvent table/model exists with correlation fields and JSON payload.
- [ ] Review decision creation writes an audit event row.
- [ ] State transition apply/deny writes an audit event row.
- [ ] Integration tests assert persisted audit rows.

## Verification
- `pytest tests/m009_s01_audit_events_test.py`
- Audit events are queryable with expected correlation_id/request_id.

## Observability Impact
- Signals added/changed: audit_events rows with action and correlation metadata.
- How a future agent inspects this: query Postgres `audit_events` for action/correlation_id.
- Failure state exposed: missing rows or missing correlation metadata in queries.

## Inputs
- `src/sps/api/routes/reviews.py` — review decision write path to hook audit emission.
- `src/sps/workflows/permit_case/guards.py` — transition application/denial paths.

## Expected Output
- `src/sps/db/models/audit_events.py` — AuditEvent ORM model.
- `src/sps/db/migrations/*` — migration creating audit_events.
- `src/sps/audit/events.py` — audit emission helper.
- `tests/m009_s01_audit_events_test.py` — integration coverage for persistence.
