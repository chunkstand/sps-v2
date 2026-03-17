# M013-n6p1tg S02: Governed admin changes for source rules + incentive programs with live runbook

**Goal:** Extend the governed admin intent → review → apply workflow to source rules and incentive programs with authoritative tables, reviewer-only approvals, and audit events.
**Demo:** Run a docker-compose runbook that creates intents, records reviewer approvals, applies changes for portal support + source rules + incentives, and shows matching audit events in Postgres.

## Decomposition Rationale
This slice has two parallel governance surfaces (source rules and incentive programs) plus an operational runbook that proves the end-to-end workflow. Splitting the work by change type keeps each task within a single context window, mirrors the proven portal support pattern, and de-risks schema/route wiring before we invest in the runbook. The runbook is last because it depends on all governed endpoints and audit signals being in place.

## Must-Haves
- Governed admin intent/review/apply flow for source rules with authoritative tables and fail-closed apply behavior.
- Governed admin intent/review/apply flow for incentive programs with authoritative tables and fail-closed apply behavior.
- Audit events emitted for intent/review/apply across all three admin change types.
- Integration tests asserting intent → review → apply success and apply-before-review denials for source rules and incentive programs.
- Docker-compose runbook proving intent → review → apply → audit for portal support, source rules, and incentive programs.

## Proof Level
- This slice proves: operational
- Real runtime required: yes
- Human/UAT required: no

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_source_rules_governance_test.py -v`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_incentive_programs_governance_test.py -v`
- `bash scripts/verify_m013_s02.sh`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_source_rules_governance_test.py -v -k review_required`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_incentive_programs_governance_test.py -v -k review_required`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_source_rules_governance_test.py -v -k role_denied`

## Observability / Diagnostics
- Runtime signals: `audit_events` rows for intent/review/apply actions; HTTP 409/403 error codes for review-required and role-denied paths.
- Inspection surfaces: Postgres tables `admin_source_rule_intents`, `admin_source_rule_reviews`, `source_rules`, `admin_incentive_program_intents`, `admin_incentive_program_reviews`, `incentive_programs`, and `audit_events`.
- Failure visibility: missing audit rows for a correlation_id, 409 review_required responses, and role_denied errors surfaced by API responses/logs.
- Redaction constraints: audit payloads must not include raw policy payloads.

## Integration Closure
- Upstream surfaces consumed: `src/sps/services/admin_portal_support.py`, `src/sps/api/routes/admin_portal_support.py`, `emit_audit_event`, RBAC role helpers.
- New wiring introduced in this slice: new admin source rules + incentive program routers in `src/sps/api/main.py`, new governance tables + services.
- What remains before the milestone is truly usable end-to-end: nothing.

## Tasks
- [x] **T01: Implement governed source rules intent/review/apply flow** `est:3h`
  - Why: source rules are fixture-backed and need an authoritative, governed mutation path to meet R035.
  - Files: `src/sps/db/models.py`, `alembic/versions/*_admin_source_rules_governance.py`, `src/sps/api/contracts/admin_source_rules.py`, `src/sps/services/admin_source_rules.py`, `src/sps/api/routes/admin_source_rules.py`, `src/sps/api/main.py`, `tests/m013_s02_admin_source_rules_governance_test.py`
  - Do: add authoritative `source_rules` + admin intent/review tables with idempotency constraints; create contracts/services/routes mirroring portal support pattern with reviewer-only approval and audit events; ensure apply is fail-closed without approved review; add integration tests covering success + apply-before-review + role-denied + audit events.
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_source_rules_governance_test.py -v`
  - Done when: source rules changes can only be applied through the governed endpoints and tests assert audit events + denial behavior.
- [x] **T02: Implement governed incentive program intent/review/apply flow** `est:3h`
  - Why: incentive programs require the same governed admin workflow to prevent silent policy drift.
  - Files: `src/sps/db/models.py`, `alembic/versions/*_admin_incentive_programs_governance.py`, `src/sps/api/contracts/admin_incentive_programs.py`, `src/sps/services/admin_incentive_programs.py`, `src/sps/api/routes/admin_incentive_programs.py`, `src/sps/api/main.py`, `tests/m013_s02_admin_incentive_programs_governance_test.py`
  - Do: add authoritative `incentive_programs` + admin intent/review tables; implement contracts/services/routes with reviewer-only approval and audit events; ensure apply is fail-closed without approved review; add integration tests mirroring portal support flow.
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest tests/m013_s02_admin_incentive_programs_governance_test.py -v`
  - Done when: incentive program updates are governed by intent/review/apply with audit event assertions in tests.
- [x] **T03: Add docker-compose runbook for admin governance across all change types** `est:2h`
  - Why: the milestone requires operational proof that all three admin change types flow through the governed pathway.
  - Files: `scripts/verify_m013_s02.sh`, `docker-compose.yml`
  - Do: script intent → review → apply flows for portal support, source rules, and incentive programs; assert audit_events rows in Postgres using docker compose exec; reuse reviewer/admin API key flow from prior runbooks.
  - Verify: `bash scripts/verify_m013_s02.sh`
  - Done when: runbook exits 0 and shows audit events for all three change types.

## Files Likely Touched
- `src/sps/db/models.py`
- `alembic/versions/*_admin_source_rules_governance.py`
- `alembic/versions/*_admin_incentive_programs_governance.py`
- `src/sps/api/contracts/admin_source_rules.py`
- `src/sps/api/contracts/admin_incentive_programs.py`
- `src/sps/services/admin_source_rules.py`
- `src/sps/services/admin_incentive_programs.py`
- `src/sps/api/routes/admin_source_rules.py`
- `src/sps/api/routes/admin_incentive_programs.py`
- `src/sps/api/main.py`
- `tests/m013_s02_admin_source_rules_governance_test.py`
- `tests/m013_s02_admin_incentive_programs_governance_test.py`
- `scripts/verify_m013_s02.sh`
