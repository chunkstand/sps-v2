# S03: End-to-end docker-compose proof (API + worker + Postgres + Temporal)

**Goal:** Prove a real intake API request can drive a live Temporal worker to RESEARCH_COMPLETE under docker-compose with persisted jurisdiction/requirements artifacts.

**Demo:** `bash scripts/verify_m004_s03.sh` brings up infra, posts `/api/v1/cases`, waits for INTAKE_COMPLETE → JURISDICTION_COMPLETE → RESEARCH_COMPLETE, and prints API + Postgres evidence for the persisted artifacts.

This slice is mostly integration glue: we need a minimal fixture override to bridge intake-generated case IDs to the Phase 4 fixture dataset, then a runbook that exercises the full path. The override should be strictly runbook/test scoped to avoid altering the intake contract, so the work is split into a small fixture/activities adjustment plus the operational script that proves the end-to-end path.

## Must-Haves
- Fixture lookup can map a runtime intake case_id to the Phase 4 fixture dataset while persisting artifacts under the runtime case_id.
- A new S03 runbook exercises the real API + worker + Postgres + Temporal path through RESEARCH_COMPLETE and asserts DB + API evidence.
- Automated verification covers the fixture override behavior to prevent silent regressions.

## Proof Level
- This slice proves: operational
- Real runtime required: yes
- Human/UAT required: no

## Verification
- `./.venv/bin/pytest tests/m004_s03_fixture_override_test.py`
- `bash scripts/verify_m004_s03.sh`
- `docker compose logs worker | grep -E "LookupError|fixture_case_id"` (diagnostic surface check)

## Observability / Diagnostics
- Runtime signals: structured activity logs (`jurisdiction_activity.persisted`, `requirements_activity.persisted`) + `case_transition_ledger` rows.
- Inspection surfaces: `docker compose logs worker`, `docker compose logs api`, `case_transition_ledger`, `jurisdiction_resolutions`, `requirement_sets` tables.
- Failure visibility: Lookup errors in worker logs, missing ledger transitions, or missing artifact rows.
- Redaction constraints: runbooks must avoid printing DB credentials; use `scripts/lib/assert_postgres.sh`.

## Integration Closure
- Upstream surfaces consumed: intake API (`src/sps/api/routes/cases.py`), phase4 fixtures (`src/sps/fixtures/phase4.py`), workflow activities (`src/sps/workflows/permit_case/activities.py`).
- New wiring introduced in this slice: fixture override selection for activities + S03 runbook composition.
- What remains before the milestone is truly usable end-to-end: nothing.

## Tasks
- [x] **T01: Add fixture override selection for Phase 4 activities** `est:1.5h`
  - Why: Intake generates new case IDs, so activities need a controlled override to load fixtures without changing the intake contract.
  - Files: `src/sps/fixtures/phase4.py`, `src/sps/workflows/permit_case/activities.py`, `tests/m004_s03_fixture_override_test.py`
  - Do: Add an env-gated fixture case_id override helper, select fixtures by the override case_id, and persist artifacts with the runtime case_id; update activity logging to include both case IDs; add tests that confirm override selection + case_id rewrite.
  - Verify: `./.venv/bin/pytest tests/m004_s03_fixture_override_test.py`
  - Done when: activities can load fixtures via override without changing the intake case_id, and tests prove the mapping.
- [x] **T02: Build the S03 end-to-end docker-compose runbook** `est:1h`
  - Why: The milestone needs an operator proof that the full intake → RESEARCH_COMPLETE path works with live services.
  - Files: `scripts/verify_m004_s03.sh`
  - Do: Create a runbook patterned on S01/S02 that posts intake, captures the case_id, starts the worker with the fixture override, waits for ledger transitions, asserts artifact persistence and API reads, and prints diagnostic hints on failure.
  - Verify: `bash scripts/verify_m004_s03.sh`
  - Done when: the runbook exits 0 and prints RESEARCH_COMPLETE ledger + artifact evidence for the intake-created case.

## Files Likely Touched
- `src/sps/fixtures/phase4.py`
- `src/sps/workflows/permit_case/activities.py`
- `tests/m004_s03_fixture_override_test.py`
- `scripts/verify_m004_s03.sh`
