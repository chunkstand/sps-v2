# S01: Audit Events and Minimal Dashboards

**Goal:** Persist audit events for critical review/state actions and expose minimal ops metrics via API and `/ops` dashboard.
**Demo:** Operator visits `/ops` and sees live queue depth, contradiction backlog, and stalled review counts. Audit events for review decisions and state transitions are queryable from Postgres.

## Decomposition Rationale
This slice crosses Postgres, API, and UI boundaries, so work is grouped to close each boundary in order: first persist audit events (critical for R022), then expose metrics via an API contract, and finally render the `/ops` UI. This keeps the integration risk low by proving data persistence before adding the dashboard layer, and matches the verification strategy (audit events test, dashboard/metrics test).

## Must-Haves
- Audit events persisted in Postgres for review decisions and state transitions with correlation fields.
- `GET /api/v1/ops/dashboard/metrics` returns queue depth, contradiction backlog, and stalled review counts.
- `/ops` Jinja dashboard renders and displays the metrics without errors.

## Proof Level
- This slice proves: integration
- Real runtime required: yes
- Human/UAT required: no

## Verification
- `pytest tests/m009_s01_audit_events_test.py`
- `pytest tests/m009_s01_dashboard_test.py`
- Inspect failure visibility: query `audit_events` for expected action/correlation_id and confirm missing rows surface as empty result (no silent fallback).

## Observability / Diagnostics
- Runtime signals: `audit_events` rows; ops metrics response payload.
- Inspection surfaces: Postgres `audit_events` table; `GET /api/v1/ops/dashboard/metrics`; `/ops` page render.
- Failure visibility: missing audit rows, zero/incorrect counts, or template render error with correlation IDs.
- Redaction constraints: avoid logging sensitive payloads; audit events store structured but non-secret metadata.

## Integration Closure
- Upstream surfaces consumed: review decision persistence, state transition guard/ledger, contradiction and dissent tables.
- New wiring introduced in this slice: ops metrics API + dashboard route + audit event emission hooks.
- What remains before the milestone is truly usable end-to-end: S02 release bundle gates and S03 rollback rehearsal/validation template.

## Tasks
- [x] **T01: Persist audit events for review decisions and transitions** `est:3h`
  - Why: R022 requires a queryable audit sink capturing critical actions with correlation fields.
  - Files: `src/sps/db/models/audit_events.py`, `src/sps/db/migrations/*`, `src/sps/audit/events.py`, `src/sps/api/routes/reviews.py`, `src/sps/workflows/permit_case/guards.py`, `tests/m009_s01_audit_events_test.py`
  - Do: Define AuditEvent model + migration; add lightweight emitter helper; emit events when review decisions are created and when state transitions are applied/denied; ensure correlation_id/request_id stored; add integration test asserting persisted rows with expected fields.
  - Verify: `pytest tests/m009_s01_audit_events_test.py`
  - Done when: audit events are inserted for review decision creation and transition outcomes with correlation fields asserted in tests.
- [x] **T02: Expose ops metrics API for queue/contradiction/stalled counts** `est:2h`
  - Why: R023 requires an operator-readable metrics endpoint backing the dashboard.
  - Files: `src/sps/api/routes/ops.py`, `src/sps/services/ops_metrics.py`, `src/sps/db/queries/ops_metrics.py`, `tests/m009_s01_dashboard_test.py`
  - Do: Implement query helpers for queue depth, contradiction backlog, stalled reviews; add `GET /api/v1/ops/dashboard/metrics` response schema; cover with integration test verifying structured counts and non-null timestamps.
  - Verify: `pytest tests/m009_s01_dashboard_test.py`
  - Done when: metrics endpoint returns expected fields and tests assert counts from seeded fixtures.
- [x] **T03: Render `/ops` dashboard page wired to metrics API** `est:2h`
  - Why: Demo requires a minimal operator UI using Jinja to display the metrics.
  - Files: `src/sps/api/routes/ops.py`, `src/sps/templates/ops/index.html`, `src/sps/static/ops.js`, `tests/m009_s01_dashboard_test.py`
  - Do: Add `/ops` route + template; wire frontend JS to call metrics endpoint and render cards; ensure template renders without JS errors in test; update dashboard test for page render and JSON fetch behavior.
  - Verify: `pytest tests/m009_s01_dashboard_test.py`
  - Done when: `/ops` renders and shows queue depth, contradiction backlog, and stalled review counts in the test harness.

## Files Likely Touched
- `src/sps/db/models/audit_events.py`
- `src/sps/db/migrations/*`
- `src/sps/audit/events.py`
- `src/sps/api/routes/reviews.py`
- `src/sps/workflows/permit_case/guards.py`
- `src/sps/api/routes/ops.py`
- `src/sps/services/ops_metrics.py`
- `src/sps/db/queries/ops_metrics.py`
- `src/sps/templates/ops/index.html`
- `src/sps/static/ops.js`
- `tests/m009_s01_audit_events_test.py`
- `tests/m009_s01_dashboard_test.py`
