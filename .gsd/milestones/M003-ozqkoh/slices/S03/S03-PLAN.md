# S03: Contradiction artifacts + advancement blocking

**Goal:** A blocking contradiction prevents the `REVIEW_PENDING → APPROVED_FOR_SUBMISSION` transition with stable denial identifiers (`INV-SPS-CONTRA-001`, `INV-003`); resolving it via the HTTP API allows advancement to proceed.

**Demo:** Three integration tests pass against real Postgres (no Temporal worker required): (1) blocking contradiction denies advancement with `event_type=CONTRADICTION_ADVANCE_DENIED` and `guard_assertion_id=INV-SPS-CONTRA-001`; (2) resolving the contradiction allows the same case to advance; (3) a non-blocking contradiction is transparent — the guard passes through to the review check and returns `APPROVAL_GATE_DENIED`.

## Must-Haves

- `resolved_at` (nullable datetime) and `resolved_by` (nullable text) added to `contradiction_artifacts` via Alembic migration; `ContradictionArtifact` ORM model updated.
- `POST /api/v1/contradictions` — create with `blocking_effect`, `resolution_status=OPEN`; 409 on duplicate `contradiction_id`.
- `POST /api/v1/contradictions/{id}/resolve` — transition `OPEN → RESOLVED`; 409 if already resolved; 404 if unknown.
- `GET /api/v1/contradictions/{id}` — read-only inspection; 404 if unknown.
- All three endpoints gated with `require_reviewer_api_key`.
- `apply_state_transition` checks for blocking open contradictions before the ReviewDecision check; denies with `event_type=CONTRADICTION_ADVANCE_DENIED`, `guard_assertion_id=INV-SPS-CONTRA-001`, `normalized_business_invariants=["INV-003"]`.
- Contradiction check runs inside the existing `session.begin()` block, after the `FOR UPDATE` lock on `permit_cases`.
- `_EVENT_CONTRADICTION_ADVANCE_DENIED` constant added in `activities.py`; `_GUARD_ASSERTION_CONTRADICTION` constant alongside it.
- Integration tests in `tests/m003_s03_contradiction_blocking_test.py`: all three scenarios pass.
- Runbook `scripts/verify_m003_s03.sh` exits 0 against docker-compose Postgres.

## Proof Level

- This slice proves: contract
- Real runtime required: yes (real Postgres; no Temporal worker)
- Human/UAT required: no

## Verification

- `python -m pytest tests/m003_s03_contradiction_blocking_test.py -v -s` (with `SPS_RUN_TEMPORAL_INTEGRATION=1`) → 3 passed
- `pytest tests/ -k "not (integration or temporal)" -x -q` → still passes (no regressions)
- `bash scripts/verify_m003_s03.sh` → exits 0 (docker-compose Postgres scenario)
- **Failure-path diagnostic:** After a blocking contradiction is created but before resolve, `SELECT event_type, payload FROM case_transition_ledger WHERE case_id = '<id>' ORDER BY occurred_at` shows a row with `event_type='CONTRADICTION_ADVANCE_DENIED'` and `payload` containing `guard_assertion_id` and `normalized_business_invariants`; `GET /api/v1/contradictions/<id>` returns the artifact with `resolution_status='OPEN'` confirming the denial reason is inspectable without touching Temporal.

## Observability / Diagnostics

- Runtime signals: `contradiction_api.create` / `contradiction_api.resolve` log events; `apply_state_transition` already emits `activity.start`/`activity.ok` with `event_type` in payload
- Inspection surfaces:
  - `SELECT contradiction_id, blocking_effect, resolution_status, resolved_at, resolved_by FROM contradiction_artifacts WHERE case_id = '...';`
  - `SELECT event_type, payload FROM case_transition_ledger WHERE case_id = '...' ORDER BY occurred_at;`
  - `GET /api/v1/contradictions/{id}` — read-only endpoint
- Failure visibility: denial `event_type=CONTRADICTION_ADVANCE_DENIED` persisted to `case_transition_ledger.payload` with `guard_assertion_id` and `normalized_business_invariants`; stable identifiers enable cross-system correlation
- Redaction constraints: `X-Reviewer-Api-Key` is the only secret; never logged

## Integration Closure

- Upstream surfaces consumed: `src/sps/workflows/permit_case/activities.py` (`apply_state_transition`, `_deny()`, `_GUARD_ASSERTION_REVIEW_GATE` pattern), `src/sps/api/routes/reviews.py` (auth dependency + request/response model pattern), `src/sps/db/models.py` (`ContradictionArtifact`), `src/sps/guards/guard_assertions.py` (`get_normalized_business_invariants`)
- New wiring introduced: contradiction router registered in `main.py` under `/api/v1/contradictions`; contradiction check inserted into protected transition branch in `activities.py`
- What remains before milestone is end-to-end usable: S04 (dissent artifacts)

## Tasks

- [x] **T01: Migration, model update, and contradiction router stub** `est:30m`
  - Why: Lays schema and API skeleton; subsequent tasks depend on the migrated model and the registered router path.
  - Files: `src/sps/db/models.py`, `alembic/versions/<new_migration>.py`, `src/sps/api/routes/contradictions.py` (new), `src/sps/api/main.py`
  - Do: Add `resolved_at` (nullable datetime with timezone) and `resolved_by` (nullable text) to `contradiction_artifacts` via `alembic revision --autogenerate` (or hand-authored migration). Update `ContradictionArtifact` ORM with the two new `Mapped` fields. Create `src/sps/api/routes/contradictions.py` with Pydantic request models (`CreateContradictionRequest`, `ResolveContradictionRequest`, `ContradictionResponse`) and three stub endpoints (POST `/`, POST `/{contradiction_id}/resolve`, GET `/{contradiction_id}`) all returning 501, gated with `require_reviewer_api_key`. Register the router in `main.py` under prefix `/api/v1/contradictions`.
  - Verify: `python -c "from sps.api.routes.contradictions import router; print('ok')"` and `python -c "from sps.db.models import ContradictionArtifact; a = ContradictionArtifact(); assert hasattr(a, 'resolved_at') and hasattr(a, 'resolved_by'); print('ok')"` and `python -c "from sps.api.main import app; routes = [r.path for r in app.routes]; assert any('/contradictions' in p for p in routes), routes; print('ok')"`.
  - Done when: Import checks pass, model has the two new fields, router is registered, migration file exists and `alembic upgrade head` applies cleanly.

- [x] **T02: Contradiction guard in `apply_state_transition`** `est:25m`
  - Why: Core governance enforcement — without this, blocking contradictions have no effect on advancement. Must land before tests can prove the blocking behavior.
  - Files: `src/sps/workflows/permit_case/activities.py`
  - Do: Add two module-level constants: `_EVENT_CONTRADICTION_ADVANCE_DENIED = "CONTRADICTION_ADVANCE_DENIED"` and `_GUARD_ASSERTION_CONTRADICTION = "INV-SPS-CONTRA-001"`. Import `ContradictionArtifact` from `sps.db.models`. Inside `apply_state_transition`, in the `REVIEW_PENDING → APPROVED_FOR_SUBMISSION` branch, after the `case.case_state != req.from_state.value` check and *before* the `review_id = req.required_review_id` check, query for open blocking contradictions: `session.query(ContradictionArtifact).filter(ContradictionArtifact.case_id == req.case_id, ContradictionArtifact.blocking_effect.is_(True), ContradictionArtifact.resolution_status == "OPEN").first()`. If any row is found, deny with `event_type=_EVENT_CONTRADICTION_ADVANCE_DENIED`, `denial_reason="BLOCKING_CONTRADICTION_UNRESOLVED"`, `guard_assertion_id=_GUARD_ASSERTION_CONTRADICTION`, `normalized_business_invariants=get_normalized_business_invariants(_GUARD_ASSERTION_CONTRADICTION)`. This block must be inside `with session.begin()` after the `with_for_update=True` lock.
  - Verify: `python -c "from sps.workflows.permit_case.activities import _EVENT_CONTRADICTION_ADVANCE_DENIED, _GUARD_ASSERTION_CONTRADICTION; print(_EVENT_CONTRADICTION_ADVANCE_DENIED, _GUARD_ASSERTION_CONTRADICTION)"` → `CONTRADICTION_ADVANCE_DENIED INV-SPS-CONTRA-001`. `pytest tests/ -k "not (integration or temporal)" -x -q` still passes.
  - Done when: Constants exist, guard is wired inside the correct transaction block, non-integration tests still pass.

- [x] **T03: Contradiction endpoint implementations** `est:30m`
  - Why: Provides the HTTP surface to create and resolve contradictions — required for test scenario 2 (resolve allows advancement) and the runbook.
  - Files: `src/sps/api/routes/contradictions.py`
  - Do: Replace the three 501 stubs with full implementations. **POST `/`** — validate `CreateContradictionRequest`, insert `ContradictionArtifact` row with `resolution_status="OPEN"`, catch `IntegrityError` and return 409 `CONTRADICTION_ALREADY_EXISTS`, return 201. **POST `/{contradiction_id}/resolve`** — load by PK (404 if not found), check `resolution_status == "OPEN"` (409 `ALREADY_RESOLVED` if not), update to `RESOLVED` + set `resolved_at=utcnow()` + `resolved_by` from request body, commit, return 200. **GET `/{contradiction_id}`** — load by PK, return 200 or 404. Log `contradiction_api.create` and `contradiction_api.resolve` at INFO level with `contradiction_id` and `case_id`. Use `_utcnow()` helper (same pattern as `reviews.py`).
  - Verify: `python -c "from sps.api.routes.contradictions import router; routes = [r.path for r in router.routes]; print(routes)"` shows all three paths.
  - Done when: All three endpoints have real implementations; import check passes; existing non-integration tests still pass.

- [x] **T04: Integration tests and runbook** `est:45m`
  - Why: Closes R008 — proves blocking denial, resolve-then-advance, and non-blocking transparency against real Postgres.
  - Files: `tests/m003_s03_contradiction_blocking_test.py` (new), `scripts/verify_m003_s03.sh` (new)
  - Do: Write `tests/m003_s03_contradiction_blocking_test.py` mirroring `m003_s02_reviewer_independence_test.py` structure — inline `_wait_for_postgres_ready`, `_migrate_db`, `_reset_db` (truncates `case_transition_ledger, review_decisions, contradiction_artifacts, permit_cases CASCADE`), `_seed_permit_case`. Three test functions wrapped in `asyncio.run(...)`: (1) `test_blocking_contradiction_denies_advancement` — seed case; POST create contradiction (`blocking_effect=true`); call `apply_state_transition` with valid `required_review_id` (seed a `ReviewDecision` row too, so denial is attributable to contradiction not review); assert `DeniedStateTransitionResult` with `event_type=CONTRADICTION_ADVANCE_DENIED`, `guard_assertion_id=INV-SPS-CONTRA-001`, `normalized_business_invariants=["INV-003"]`. (2) `test_resolve_contradiction_allows_advancement` — same setup as (1); POST resolve contradiction; call `apply_state_transition` with new `request_id` and same valid `review_id`; assert `AppliedStateTransitionResult` with `event_type=CASE_STATE_CHANGED`. (3) `test_nonblocking_contradiction_is_transparent` — seed case + POST create contradiction with `blocking_effect=false`; call `apply_state_transition` without a valid review (no `required_review_id`); assert `DeniedStateTransitionResult` with `event_type=APPROVAL_GATE_DENIED` (not `CONTRADICTION_ADVANCE_DENIED`). Write `scripts/verify_m003_s03.sh` following the `verify_m003_s01.sh` pattern — bring up docker-compose Postgres only (no worker or uvicorn needed for DB-level verification), apply migrations, use `httpx`/`curl` via `python -c` one-liners against the ASGI app or direct `curl` if uvicorn is started; assert Postgres state after each step; use `assert_postgres` helper from `scripts/lib/assert_postgres.sh`.
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 python -m pytest tests/m003_s03_contradiction_blocking_test.py -v -s` → 3 passed. `bash scripts/verify_m003_s03.sh` → exits 0.
  - Done when: All three integration tests pass, runbook exits 0, `pytest tests/ -k "not (integration or temporal)" -x -q` still passes.

## Files Likely Touched

- `src/sps/db/models.py`
- `alembic/versions/<new_migration>.py`
- `src/sps/api/routes/contradictions.py` (new)
- `src/sps/api/main.py`
- `src/sps/workflows/permit_case/activities.py`
- `tests/m003_s03_contradiction_blocking_test.py` (new)
- `scripts/verify_m003_s03.sh` (new)
