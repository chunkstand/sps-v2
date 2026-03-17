---
estimated_steps: 7
estimated_files: 7
---

# T02: Implement governed incentive program intent/review/apply flow

**Slice:** M013-n6p1tg S02 — Governed admin changes for source rules + incentive programs with live runbook
**Milestone:** M013-n6p1tg

## Description
Introduce authoritative incentive program tables plus admin intent/review governance endpoints mirroring the portal support and source rules patterns, with reviewer-only approvals, audit events, and integration tests proving the governed workflow.

## Steps
1. Add ORM models for `incentive_programs`, `admin_incentive_program_intents`, and `admin_incentive_program_reviews` with idempotency constraints.
2. Add Alembic migration for incentive program governance tables.
3. Implement contracts, services, and routes for incentive program intents, reviewer approvals, and governed apply, including audit event emission and fail-closed review checks.
4. Register the incentive program router in `src/sps/api/main.py` (if not already registered).
5. Add integration tests for intent → review → apply success, apply-before-review denial, reviewer-only enforcement, and audit event assertions.

## Must-Haves
- [ ] Incentive program admin intent/review/apply endpoints enforce reviewer-only approvals and fail-closed apply.
- [ ] Integration tests assert audit events and denial behaviors for incentive programs.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_incentive_programs_governance_test.py -v`
- API responses include 409 review_required and 403 role_denied when expected.

## Observability Impact
- Signals added/changed: audit events for ADMIN_INCENTIVE_PROGRAM_INTENT_CREATED / REVIEW_RECORDED / APPLIED.
- How a future agent inspects this: query `audit_events`, `admin_incentive_program_intents`, and `admin_incentive_program_reviews` tables.
- Failure state exposed: missing audit rows or 409 review_required responses indicate failure paths.

## Inputs
- `src/sps/services/admin_portal_support.py` — existing intent/review/apply pattern to mirror.
- `tests/m013_s01_admin_portal_support_governance_test.py` — integration test pattern and audit assertions.

## Expected Output
- `src/sps/db/models.py` — incentive program governance tables.
- `src/sps/api/contracts/admin_incentive_programs.py` — incentive program intent/review/apply contracts.
- `src/sps/services/admin_incentive_programs.py` — service helpers for gating and idempotency.
- `src/sps/api/routes/admin_incentive_programs.py` — governed endpoints with audit events.
- `tests/m013_s02_admin_incentive_programs_governance_test.py` — integration tests for incentive programs governance.
