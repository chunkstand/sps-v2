# S01: Admin intent/review/apply for portal support metadata

**Goal:** Admins can create an intent for portal support metadata changes, reviewers can approve them, and the governed apply endpoint updates the authoritative portal support metadata with audit events.

**Demo:** POST an admin portal-support intent, POST a reviewer approval, then POST apply; the portal support metadata row is updated and three audit_events rows (intent/review/apply) are persisted.

**Decomposition reasoning:** This slice is governance-heavy and crosses DB → API → audit boundaries, so the plan front-loads schema/contracts, then wires the API + audit events, then proves behavior with a single integration test that exercises intent → review → apply end-to-end. This ordering retires the highest risk (authority boundaries and audit trail) before polishing ergonomics.

## Requirements
- R035 — Admin policy/config governance (owned)

## Must-Haves
- Admin intent + review + apply persistence for portal support metadata changes (admin-specific artifacts; no ReviewDecision reuse).
- Governed apply endpoint updates an authoritative portal support metadata store only when an approved review exists.
- Audit events are emitted for admin intent creation, review decision, and apply actions.
- Integration test proves intent → review → apply with RBAC enforcement and audit evidence.

## Proof Level
- This slice proves: integration
- Real runtime required: yes (Postgres)
- Human/UAT required: no

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m013_s01_admin_portal_support_governance_test.py -v`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m013_s01_admin_portal_support_governance_test.py -k "apply_before_review" -v`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m013_s01_admin_portal_support_governance_test.py -k "apply_before_review and error_code" -v`

## Observability / Diagnostics
- Runtime signals: `audit_events` rows for `ADMIN_PORTAL_SUPPORT_INTENT_CREATED`, `ADMIN_PORTAL_SUPPORT_REVIEW_RECORDED`, `ADMIN_PORTAL_SUPPORT_APPLIED`.
- Inspection surfaces: Postgres tables `admin_portal_support_intents`, `admin_portal_support_reviews`, `portal_support_metadata`, `audit_events`.
- Failure visibility: apply without approval returns HTTP 409 with `error_code=review_required`; audit_events remains unchanged for denied apply.
- Redaction constraints: do not log raw portal support payloads; audit payload should reference intent/review IDs only.

## Integration Closure
- Upstream surfaces consumed: `sps.auth.rbac.require_roles`, `sps.audit.events.emit_audit_event`, `sps.db.session.get_db`.
- New wiring introduced in this slice: admin portal-support router added to `sps.api.main`.
- What remains before the milestone is truly usable end-to-end: S02 extends this governed workflow to source rules + incentive programs and adds docker-compose runbook proof.

## Tasks
- [x] **T01: Add portal support governance schema + contracts** `est:1.5h`
  - Why: Establishes authoritative tables and request/response shapes for admin intent/review/apply.
  - Files: `src/sps/db/models.py`, `alembic/versions/*_admin_portal_support_governance.py`, `src/sps/api/contracts/admin_portal_support.py`
  - Do: Add ORM models for `portal_support_metadata`, `admin_portal_support_intents`, `admin_portal_support_reviews`; define JSONB payload fields + status enums; create Alembic migration with indexes (intent_id, status, portal_family). Add Pydantic contracts for create intent, review decision, and apply response.
  - Verify: `alembic upgrade head` succeeds locally and models import cleanly.
  - Done when: Schema + contracts exist and migration defines all new tables with correct FK/index constraints.

- [x] **T02: Wire admin intent/review/apply API with audit events** `est:2h`
  - Why: Implements the governed authority boundary and audit trail for portal support metadata changes.
  - Files: `src/sps/api/routes/admin_portal_support.py`, `src/sps/api/main.py`, `src/sps/services/admin_portal_support.py`, `src/sps/audit/events.py`
  - Do: Add router with endpoints for create intent (ADMIN role), record review (REVIEWER role), apply intent (ADMIN role). Enforce “approved review required” before apply, and upsert portal_support_metadata in a single transaction. Emit audit events for each action. Return 409 on duplicate review idempotency or apply without approval.
  - Verify: `python -m pytest tests/m013_s01_admin_portal_support_governance_test.py -k "rbac" -v` (once tests exist).
  - Done when: Endpoints enforce RBAC, persist rows, and emit audit_events per request.

- [x] **T03: Prove intent → review → apply with audit trail** `est:1.5h`
  - Why: Validates the end-to-end governed workflow and audit trail for R035.
  - Files: `tests/m013_s01_admin_portal_support_governance_test.py`, `tests/helpers/auth_tokens.py`
  - Do: Write Postgres-backed integration tests using ASGITransport. Seed auth env + tokens for admin/reviewer, create intent, approve review, apply, and assert portal_support_metadata row + audit_events entries. Add denial checks for apply-before-review and wrong-role access.
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m013_s01_admin_portal_support_governance_test.py -v`
  - Done when: Tests pass and assert audit events + authoritative metadata update.

## Files Likely Touched
- `src/sps/db/models.py`
- `alembic/versions/*_admin_portal_support_governance.py`
- `src/sps/api/contracts/admin_portal_support.py`
- `src/sps/services/admin_portal_support.py`
- `src/sps/api/routes/admin_portal_support.py`
- `src/sps/api/main.py`
- `tests/m013_s01_admin_portal_support_governance_test.py`
