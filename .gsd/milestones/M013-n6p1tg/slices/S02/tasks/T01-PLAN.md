---
estimated_steps: 7
estimated_files: 7
---

# T01: Implement governed source rules intent/review/apply flow

**Slice:** M013-n6p1tg S02 — Governed admin changes for source rules + incentive programs with live runbook
**Milestone:** M013-n6p1tg

## Description
Create authoritative source rules tables and admin intent/review governance surfaces mirroring the portal support pattern, with reviewer-only approvals, fail-closed apply, audit event emission, and integration tests that assert success and denial behavior.

## Steps
1. Add ORM models for `source_rules`, `admin_source_rule_intents`, and `admin_source_rule_reviews` with idempotency constraints and indexes aligned to portal support governance.
2. Add Alembic migration for the new tables and ensure upgrade uses `heads` compatibility.
3. Implement contracts, service helpers, and routes for source rule intent creation, reviewer approval (reviewer-only), and governed apply with audit events.
4. Register the new router in `src/sps/api/main.py`.
5. Add integration tests that exercise intent → review → apply, apply-before-review denials, reviewer-only enforcement, and audit event presence.

## Must-Haves
- [ ] Source rule admin intent/review/apply endpoints enforce reviewer-only approvals and fail-closed apply.
- [ ] Integration tests assert audit events and denial behaviors for source rules.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_source_rules_governance_test.py -v`
- API responses include 409 review_required and 403 role_denied when expected.

## Observability Impact
- Signals added/changed: audit events for ADMIN_SOURCE_RULE_INTENT_CREATED / REVIEW_RECORDED / APPLIED.
- How a future agent inspects this: query `audit_events`, `admin_source_rule_intents`, and `admin_source_rule_reviews` tables for correlation_id/intents.
- Failure state exposed: missing audit rows or 409 review_required responses indicate failure paths.

## Inputs
- `src/sps/services/admin_portal_support.py` — existing intent/review/apply pattern to mirror.
- `tests/m013_s01_admin_portal_support_governance_test.py` — integration test pattern and audit assertions.

## Expected Output
- `src/sps/db/models.py` — source rules governance tables.
- `src/sps/api/contracts/admin_source_rules.py` — source rule intent/review/apply contracts.
- `src/sps/services/admin_source_rules.py` — service helpers for gating and idempotency.
- `src/sps/api/routes/admin_source_rules.py` — governed endpoints with audit events.
- `tests/m013_s02_admin_source_rules_governance_test.py` — integration tests for source rules governance.
