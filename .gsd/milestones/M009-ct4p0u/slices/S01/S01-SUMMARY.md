---
id: S01
parent: M009-ct4p0u
milestone: M009-ct4p0u
provides:
  - audit event persistence for review decisions and state transition outcomes with correlation metadata
  - ops metrics API + /ops dashboard for queue depth, contradiction backlog, and stalled review counts
requires:
  - none
affects:
  - S02
key_files:
  - src/sps/db/models.py
  - alembic/versions/a9b3c2d4e6f7_audit_events.py
  - src/sps/audit/events.py
  - src/sps/api/routes/reviews.py
  - src/sps/workflows/permit_case/activities.py
  - src/sps/db/queries/ops_metrics.py
  - src/sps/services/ops_metrics.py
  - src/sps/api/routes/ops.py
  - src/sps/api/templates/ops/index.html
  - src/sps/api/static/ops.js
  - tests/m009_s01_audit_events_test.py
  - tests/m009_s01_dashboard_test.py
key_decisions:
  - keep AuditEvent ORM model in shared src/sps/db/models.py module
  - split ops routes into authenticated metrics API + unauthenticated /ops page router
patterns_established:
  - emit_audit_event helper for transactional audit event writes
  - ops metrics assembled via query helpers + service response builder
  - /ops Jinja template passes metrics endpoint via data attribute consumed by static JS
observability_surfaces:
  - Postgres audit_events table (action, correlation_id, request_id)
  - GET /api/v1/ops/dashboard/metrics payload + ops_metrics.snapshot log
  - /ops dashboard status panel + console error on metrics fetch failure
  - /static/ops.js for UI wiring
  
drill_down_paths:
  - .gsd/milestones/M009-ct4p0u/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009-ct4p0u/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M009-ct4p0u/slices/S01/tasks/T03-SUMMARY.md
duration: 2.9h
verification_result: passed
completed_at: 2026-03-16
---

# S01: Audit Events and Minimal Dashboards

**Persisted audit events for review/state actions and shipped a minimal ops dashboard with a metrics API for queue health.**

## What Happened
We added the `audit_events` table and emit audit rows on review decision creation and state transition apply/deny paths with correlation/request metadata. Ops metrics queries now compute queue depth, contradiction backlog, and stalled review counts, exposed via `GET /api/v1/ops/dashboard/metrics` and wired into a new `/ops` Jinja dashboard that fetches and renders the metrics via static JS. Tests were updated to use httpx ASGI transport with async clients to match current httpx behavior.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m009_s01_audit_events_test.py`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m009_s01_dashboard_test.py`

## Requirements Advanced
- none

## Requirements Validated
- R022 — Validated via audit event integration tests proving persisted rows with correlation/request metadata.
- R023 — Validated via ops metrics + dashboard integration tests proving API contract and page render.

## New Requirements Surfaced
- none

## Requirements Invalidated or Re-scoped
- none

## Deviations
- AuditEvent ORM model lives in `src/sps/db/models.py` instead of a new module.
- Ops template/static assets are under `src/sps/api/templates/ops` and `src/sps/api/static` to match existing reviewer console layout.

## Known Limitations
- Ops dashboard still relies on the reviewer API key for metrics; auth/RBAC hardening is deferred to M010.

## Follow-ups
- none

## Files Created/Modified
- `src/sps/db/models.py` — AuditEvent ORM model definition.
- `alembic/versions/a9b3c2d4e6f7_audit_events.py` — audit_events migration.
- `src/sps/audit/events.py` — emit_audit_event helper.
- `src/sps/api/routes/reviews.py` — review decision audit emission.
- `src/sps/workflows/permit_case/activities.py` — state transition audit emission.
- `src/sps/db/queries/ops_metrics.py` — queue/contradiction/stalled query helpers.
- `src/sps/services/ops_metrics.py` — metrics response builder.
- `src/sps/api/routes/ops.py` — metrics API + /ops page router.
- `src/sps/api/templates/ops/index.html` — ops dashboard template.
- `src/sps/api/static/ops.js` — metrics fetch/render logic.
- `tests/m009_s01_audit_events_test.py` — audit event integration tests.
- `tests/m009_s01_dashboard_test.py` — dashboard + metrics integration tests.

## Forward Intelligence
### What the next slice should know
- Ops API routes are authenticated but `/ops` renders without auth; metrics fetch requires `X-Reviewer-Api-Key`.
- Integration tests are env-gated via `SPS_RUN_TEMPORAL_INTEGRATION=1` and require async httpx clients.

### What's fragile
- The /ops JS relies on the `data-metrics-endpoint` attribute; template changes must preserve it or the dashboard silently fails.

### Authoritative diagnostics
- `audit_events` table rows filtered by action/request_id — definitive proof of audit emission.
- `GET /api/v1/ops/dashboard/metrics` — authoritative metrics payload used by the UI.

### What assumptions changed
- httpx ASGI transport requires `AsyncClient` (sync client context manager fails in current httpx).
