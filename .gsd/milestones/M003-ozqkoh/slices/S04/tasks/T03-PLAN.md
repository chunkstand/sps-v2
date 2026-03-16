---
estimated_steps: 6
estimated_files: 2
---

# T03: Integration test and operator runbook

**Slice:** S04 — Dissent artifacts
**Milestone:** M003-ozqkoh

## Description

Prove R009 end-to-end against real Postgres. Two integration test scenarios: ACCEPT_WITH_DISSENT creates a queryable dissent artifact; ACCEPT does not. Operator runbook mirrors S03 pattern — docker-compose, migrations, API, curl scenarios, psql assertions.

## Steps

1. Write `tests/m003_s04_dissent_artifacts_test.py`:
   - Guard: `if os.getenv("SPS_RUN_TEMPORAL_INTEGRATION") != "1": pytest.skip(...)`
   - Inline helpers (no import from s03): `_wait_for_postgres_ready`, `_migrate_db`, `_reset_db` (TRUNCATE `dissent_artifacts, case_transition_ledger, review_decisions, contradiction_artifacts, permit_cases CASCADE`), `_seed_permit_case`
   - `@pytest.fixture(autouse=True)` that calls `_wait_for_postgres_ready()`, `_migrate_db()`, then `_reset_db()` as teardown (yield pattern)
   - **Scenario (a)** `test_accept_with_dissent_creates_artifact`: POST `{"outcome": "ACCEPT_WITH_DISSENT", "dissent_scope": "structural", "dissent_rationale": "reviewer notes structural concern", ...}` → assert 201; assert `response.json()["dissent_artifact_id"]` is not None; capture `dissent_id`; GET `/api/v1/dissents/{dissent_id}` → assert 200; assert `linked_review_id == decision_id`; assert `case_id` matches; assert `scope == "structural"`; assert `resolution_state == "OPEN"`. Also verify via DB: `db.get(DissentArtifact, dissent_id)` row exists.
   - **Scenario (b)** `test_accept_does_not_create_artifact`: POST `{"outcome": "ACCEPT", ...}` → assert 201; assert `response.json().get("dissent_artifact_id") is None`; DB query confirms no row with `linked_review_id == decision_id`.
   - Use `httpx.ASGITransport(app=app)` + `AsyncClient(transport=...)` pattern throughout (DECISIONS #30).

2. Write `scripts/verify_m003_s04.sh` following `verify_m003_s03.sh` structure:
   - Header comment documenting scenarios covered
   - Source `scripts/lib/assert_postgres.sh`
   - Check docker-compose services up (postgres + api — no temporal worker)
   - Apply migrations via alembic
   - Start uvicorn in background; wait for readiness (`curl --retry 10 ...`)
   - Seed permit_case via psql
   - POST ACCEPT_WITH_DISSENT decision → assert HTTP 201; capture dissent_id from response
   - GET `/api/v1/dissents/{dissent_id}` → assert HTTP 200
   - psql assert: `SELECT resolution_state FROM dissent_artifacts WHERE linked_review_id = '${DECISION_ID}'` → `OPEN`
   - POST ACCEPT decision (new decision_id/idempotency_key, same case) → assert HTTP 201
   - psql assert: `SELECT COUNT(*) FROM dissent_artifacts WHERE linked_review_id = '${DECISION_ID_2}'` → `0`
   - Assert 401 on missing key
   - Cleanup: kill uvicorn
   - Use `mktemp /tmp/sps-s04.XXXXXX` (trailing X's, macOS-compatible)

3. Run integration test against real docker-compose Postgres.

4. Run runbook and verify exit 0.

## Must-Haves

- [ ] `tests/m003_s04_dissent_artifacts_test.py` — two passing scenarios: ACCEPT_WITH_DISSENT → dissent row queryable; ACCEPT → no row
- [ ] `scripts/verify_m003_s04.sh` exits 0 against docker-compose
- [ ] `_reset_db()` truncates `dissent_artifacts` explicitly (before `permit_cases`) to avoid FK violation — OR relies on `ondelete="CASCADE"` from `case_id` FK being triggered by the permit_cases TRUNCATE; verify the chosen approach works cleanly
- [ ] DB query in test confirms row existence/absence — not just HTTP response assertions

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s04_dissent_artifacts_test.py -v -s` → 2 passed, 0 failed
- `bash scripts/verify_m003_s04.sh` → exits 0; no assertion failures printed
- `pytest tests/ -k "not (integration or temporal)" -x -q` → existing tests unaffected

## Inputs

- T01 + T02 output: `DissentArtifact` model, dissent creation in POST endpoint, GET dissent router registered
- `tests/m003_s03_contradiction_blocking_test.py` — `_seed_permit_case`, `_reset_db`, `_wait_for_postgres_ready`, `_migrate_db` helper patterns; `httpx.ASGITransport` usage
- `scripts/verify_m003_s03.sh` — runbook structure: docker-compose checks, migration, uvicorn start, curl scenarios, psql assertions, cleanup
- `scripts/lib/assert_postgres.sh` — shared assertion helper

## Expected Output

- `tests/m003_s04_dissent_artifacts_test.py` (new) — 2-scenario integration test, R009 proof
- `scripts/verify_m003_s04.sh` (new) — operator runbook, exits 0 on success

## Observability Impact

**New signals after this task:**
- Integration test exercises `reviewer_api.dissent_artifact_created` log line — confirmed present in scenario (a) by the successful flush path through the endpoint.
- Runbook emits `runbook.dissent_id_captured dissent_id=...` when `dissent_artifact_id` is captured from POST response — confirms the field propagates end-to-end.
- Runbook emits `postgres_summary` table dump showing `dissent_id | linked_review_id | resolution_state` — inspectable at-a-glance without psql.

**How a future agent inspects this task's work:**
- Test pass: `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s04_dissent_artifacts_test.py -v -s`
- Runbook: `bash scripts/verify_m003_s04.sh` — exits 0 with structured log lines to stderr
- Log signal: `docker compose logs api | grep reviewer_api.dissent_artifact_created` — one line per ACCEPT_WITH_DISSENT decision
- DB: `SELECT dissent_id, linked_review_id, resolution_state FROM dissent_artifacts;`

**Bug found and fixed during this task:**
- `db.flush()` inserted between `db.add(review_decision_row)` and `db.add(dissent_row)` in `src/sps/api/routes/reviews.py`. Without an ORM `relationship()`, SQLAlchemy's unit-of-work cannot infer FK-safe INSERT ordering from column FK definitions alone. Without the flush, `dissent_artifacts.linked_review_id` FK violated because the ReviewDecision row wasn't yet visible to Postgres. The explicit flush inside the `if row.dissent_flag:` branch forces ReviewDecision to hit the DB first while keeping both rows in the same transaction.

**Failure state visibility:**
- FK violation without the flush → `sqlalchemy.exc.IntegrityError` → HTTP 500; look for `ForeignKeyViolation fk_dissent_artifacts_linked_review_id` in Postgres logs.
- If `reviewer_api.dissent_artifact_created` is absent from logs for an ACCEPT_WITH_DISSENT response → the `if row.dissent_flag:` branch didn't run — check `dissent_flag` on the `ReviewDecision` row in DB.
