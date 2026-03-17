# S02: Governed admin changes for source rules + incentive programs with live runbook — UAT

**Milestone:** M013-n6p1tg
**Written:** 2026-03-16

## UAT Type
- UAT mode: live-runtime
- Why this mode is sufficient: the slice’s proof hinges on a docker-compose environment exercising real API + Postgres flows with audit-event verification.

## Preconditions
- Docker is running locally.
- Repo virtualenv is available at `.venv/` with dependencies installed.
- Ports 5432 and 8000 are free.
- `scripts/verify_m013_s02.sh` is executable.

## Smoke Test
Run `bash scripts/verify_m013_s02.sh` and confirm it exits 0 with `runbook.success` in the output.

## Test Cases
### 1. Portal support intent → review → apply with audit trail
1. Run `bash scripts/verify_m013_s02.sh`.
2. Inspect the output for `portal_support_intent_created`, `portal_support_review_recorded`, and `portal_support_applied` assertions.
3. **Expected:** The runbook reports `portal_support_audit_verified` and exits successfully.

### 2. Source rule intent → review → apply with audit trail
1. Run `bash scripts/verify_m013_s02.sh`.
2. Inspect the output for `source_rule_intent_created`, `source_rule_review_recorded`, and `source_rule_applied` assertions.
3. **Expected:** The runbook reports `source_rule_audit_verified` and exits successfully.

### 3. Incentive program intent → review → apply with audit trail
1. Run `bash scripts/verify_m013_s02.sh`.
2. Inspect the output for `incentive_program_intent_created`, `incentive_program_review_recorded`, and `incentive_program_applied` assertions.
3. **Expected:** The runbook reports `incentive_program_audit_verified` and exits successfully.

### 4. Review-required enforcement (source rules)
1. Run `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_source_rules_governance_test.py -v -k review_required`.
2. **Expected:** The review-required test passes with a 409 response and no apply recorded without review.

### 5. Review-required enforcement (incentive programs)
1. Run `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_incentive_programs_governance_test.py -v -k review_required`.
2. **Expected:** The review-required test passes with a 409 response and no apply recorded without review.

### 6. RBAC enforcement for admin/reviewer roles
1. Run `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_source_rules_governance_test.py -v -k role_denied`.
2. **Expected:** Tests confirm reviewer cannot apply and admin cannot review (403 role_denied).

## Edge Cases
### Apply without Postgres running
1. Stop docker compose services (`docker compose down -v`).
2. Run `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_incentive_programs_governance_test.py -v -k review_required`.
3. **Expected:** Test setup fails with Postgres readiness errors, indicating Postgres must be up for governance tests.

## Failure Signals
- `runbook.success` is missing or the runbook exits non-zero.
- Missing audit verification assertions (`*_audit_verified`) in the runbook output.
- Review-required tests return 200 or 201 instead of 409.
- RBAC tests return success instead of 403 `role_denied`.

## Requirements Proved By This UAT
- R035 — governed admin intent/review/apply flows for portal support, source rules, and incentive programs with audit trails.

## Not Proven By This UAT
- Any non-admin config governance beyond portal support/source rules/incentive programs.
- UI-only admin console behavior beyond API contracts.

## Notes for Tester
- The runbook performs cleanup and restarts docker-compose services; allow it to complete before running filtered pytest checks.
- Ensure Postgres is running (`docker compose up -d postgres`) before executing individual pytest cases.
