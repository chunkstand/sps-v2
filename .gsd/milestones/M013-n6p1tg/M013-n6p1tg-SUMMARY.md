---
id: M013-n6p1tg
provides:
  - Governed admin policy/config mutations (portal support metadata, source rules, incentive programs) via intent → review → apply with audit trails and a live runbook proof
key_decisions:
  - Admin-specific intent/review artifacts replace ReviewDecision for config governance
  - Reviewer approvals are required for admin config changes (admin-only tokens denied)
patterns_established:
  - Fail-closed apply endpoints require approved review and emit audit events
  - Admin config governance follows intent → review → apply with 409 review_required denials
observability_surfaces:
  - Postgres tables: admin_*_intents/admin_*_reviews + portal_support_metadata/source_rules/incentive_programs
  - audit_events rows for ADMIN_PORTAL_SUPPORT_* / ADMIN_SOURCE_RULE_* / ADMIN_INCENTIVE_PROGRAM_* actions
  - scripts/verify_m013_s02.sh docker-compose runbook
requirement_outcomes:
  - id: R035
    from_status: active
    to_status: validated
    proof: pytest tests/m013_s01_admin_portal_support_governance_test.py + pytest tests/m013_s02_admin_source_rules_governance_test.py + pytest tests/m013_s02_admin_incentive_programs_governance_test.py + scripts/verify_m013_s02.sh
duration: 9.5h
verification_result: passed
completed_at: 2026-03-16
---

# M013-n6p1tg: Phase 13 — admin policy/config governance

**Admin policy/config changes now flow through intent → review → apply governance with reviewer-only approvals, durable audit trails, and a live docker-compose runbook proving portal support, source rules, and incentive program updates.**

## What Happened

Implemented governed admin change workflows for portal support metadata, source rules, and incentive programs, introducing intent and review artifacts, reviewer-only approvals, fail-closed apply endpoints, and audit event emission. The workflow pattern from portal support metadata was extended to source rules and incentive programs, with authoritative mutable tables and a docker-compose runbook that exercises intent → review → apply → audit across all three change types.

## Cross-Slice Verification

- Portal support metadata intent → review → apply governance is validated via `tests/m013_s01_admin_portal_support_governance_test.py`, including review-required and role-denied paths with audit assertions.
- Source rules and incentive program governance are validated via `tests/m013_s02_admin_source_rules_governance_test.py` and `tests/m013_s02_admin_incentive_programs_governance_test.py`, including review-required and RBAC denials.
- Audit event emission for intents, reviews, and applies is asserted in the S01/S02 integration tests and confirmed in the docker-compose runbook queries.
- End-to-end intent → review → apply → audit flows for all three change types are proven via `scripts/verify_m013_s02.sh`.

## Requirement Changes

- R035: active → validated — proved by `tests/m013_s01_admin_portal_support_governance_test.py`, `tests/m013_s02_admin_source_rules_governance_test.py`, `tests/m013_s02_admin_incentive_programs_governance_test.py`, and `scripts/verify_m013_s02.sh`.

## Forward Intelligence

### What the next milestone should know
- Admin governance tests and the runbook rely on `alembic upgrade heads` to handle multi-head migrations; keep this pattern when adding new migrations.

### What's fragile
- Review-required pytest filters assume Postgres is running; start docker compose Postgres before running focused tests.

### Authoritative diagnostics
- `audit_events` filtered by intent_id correlation provides the clearest proof of intent/review/apply actions across all admin change types.

### What assumptions changed
- None.

## Files Created/Modified

- `src/sps/db/models.py` — admin intent/review models plus authoritative config tables
- `alembic/versions/e3a9c4b7d2f1_admin_portal_support_governance.py` — portal support governance schema
- `alembic/versions/b7c2d9e4f1a3_admin_source_rules_governance.py` — source rules governance schema
- `alembic/versions/c8d1e2f3a4b5_admin_incentive_programs_governance.py` — incentive programs governance schema
- `src/sps/services/admin_portal_support.py` — portal support intent/review/apply helpers
- `src/sps/services/admin_source_rules.py` — source rule intent/review/apply helpers
- `src/sps/services/admin_incentive_programs.py` — incentive program intent/review/apply helpers
- `src/sps/api/routes/admin_portal_support.py` — portal support governance endpoints
- `src/sps/api/routes/admin_source_rules.py` — source rule governance endpoints
- `src/sps/api/routes/admin_incentive_programs.py` — incentive program governance endpoints
- `tests/m013_s01_admin_portal_support_governance_test.py` — portal support governance integration tests
- `tests/m013_s02_admin_source_rules_governance_test.py` — source rule governance integration tests
- `tests/m013_s02_admin_incentive_programs_governance_test.py` — incentive program governance integration tests
- `scripts/verify_m013_s02.sh` — docker-compose runbook proving governed admin changes
