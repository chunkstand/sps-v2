# M003-ozqkoh/S03 — Research

**Date:** 2026-03-16

## Summary

S03 is primarily a guard extension and a small CRUD API surface. The `ContradictionArtifact` table and ORM model already exist from Phase 1. The blocking logic just needs to be inserted into `apply_state_transition` before the `ReviewDecision` check. The HTTP endpoints for create/resolve are new but follow the same pattern as the reviews router from S01/S02.

Two constraints drive the design:
1. The contradiction check must live inside the Postgres transaction in `apply_state_transition` — same transaction that locks `permit_cases` with `FOR UPDATE`. This keeps the "no blocking contradictions" invariant atomic with the state mutation.
2. The test does not need a Temporal worker — the guard is in a DB activity callable as plain Python, and the contradiction API is a standalone HTTP surface. The S02 pattern (Postgres-only, `httpx.ASGITransport`) applies directly.

The one schema gap: `contradiction_artifacts` has no `resolved_at` / `resolved_by` columns. These need a new Alembic migration. The model already has all spec-required fields (`blocking_effect`, `resolution_status`).

## Recommendation

**Four tasks in order:**

1. **T01 — Migration + model + contradiction router (stub):** Add `resolved_at` (nullable datetime) and `resolved_by` (nullable text) to `contradiction_artifacts` via a new Alembic migration. Update the ORM model. Create `src/sps/api/routes/contradictions.py` with `POST /` (create), `POST /{contradiction_id}/resolve`, and `GET /{contradiction_id}` stubs (501). Register the router in `main.py` under `/api/v1/contradictions`. Gate with `require_reviewer_api_key`.

2. **T02 — Guard extension in `apply_state_transition`:** Inside the `REVIEW_PENDING → APPROVED_FOR_SUBMISSION` branch (before the existing `ReviewDecision` check), query `contradiction_artifacts` for rows matching `case_id=req.case_id AND blocking_effect=True AND resolution_status='OPEN'`. If any exist, deny with `event_type=CONTRADICTION_ADVANCE_DENIED`, `guard_assertion_id=INV-SPS-CONTRA-001`, `normalized_business_invariants=get_normalized_business_invariants("INV-SPS-CONTRA-001")` → `["INV-003"]`. Only proceed to the ReviewDecision check if no blocking contradictions exist.

3. **T03 — Contradiction endpoint implementations:** Replace stubs with full implementations. POST create: validate Pydantic model, insert `ContradictionArtifact` row (`resolution_status="OPEN"`), return 201. POST resolve: load by ID, check `resolution_status == "OPEN"` (409 if already resolved), update to `RESOLVED` + set `resolved_at=now()` + `resolved_by` from request, commit. GET: load + return or 404.

4. **T04 — Integration tests + runbook:** Write `tests/m003_s03_contradiction_blocking_test.py` with three tests (blocking contradiction denies advancement, resolving allows advancement, non-blocking contradiction does not deny). Write `scripts/verify_m003_s03.sh` proving the full HTTP-API-driven scenario against docker-compose Postgres.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Stable denial identifiers | `get_normalized_business_invariants("INV-SPS-CONTRA-001")` in `src/sps/guards/guard_assertions.py` | Returns `["INV-003"]` from the registry; consistent with the pattern already used for `INV-SPS-STATE-002` and `INV-SPS-REV-001` |
| Denial result construction | `_deny(event_type=..., guard_assertion_id=..., ...)` helper in `activities.py:111-125` | Builds `DeniedStateTransitionResult` correctly; all guard denials go through this path |
| Auth dependency | `require_reviewer_api_key` in `reviews.py` | Already tested and wired; contradictions are a reviewer-managed surface |
| HTTP test client | `httpx.ASGITransport(app=app)` + `AsyncClient(transport=...)` | Decision #30; `httpx.AsyncClient(app=...)` was removed in httpx 0.20 |
| DB session in tests | `get_sessionmaker()` / `get_engine()` from `sps.db.session` | Consistent with S01 and S02 test patterns; picks up env config automatically |

## Existing Code and Patterns

- `src/sps/db/models.py:108-126` — `ContradictionArtifact` model: has `contradiction_id` (PK), `case_id` (FK), `scope`, `source_a`, `source_b`, `ranking_relation`, `blocking_effect` (bool), `resolution_status` (text), `created_at`. Missing: `resolved_at`, `resolved_by`. Migration must add these.
- `src/sps/workflows/permit_case/activities.py:189-218` — canonical protected transition branch. Contradiction check goes between the `case.case_state != req.from_state.value` state check and the `review_id = req.required_review_id` review check. Uses the `_deny()` helper and `_GUARD_ASSERTION_*` constants pattern.
- `src/sps/api/routes/reviews.py` — full reference implementation: Pydantic models with `ConfigDict(extra="forbid")`, `require_reviewer_api_key` dependency, `_utcnow()` helper, async POST + sync GET pattern. Contradiction router should mirror this structure.
- `tests/m003_s02_reviewer_independence_test.py` — canonical no-Temporal-worker integration test template: `_wait_for_postgres_ready`, `_migrate_db`, `_reset_db`, `_seed_permit_case` inlined helpers; `asyncio.run(_run_..._test())` wrapper; `httpx.ASGITransport` test client.
- `invariants/sps/guard-assertions.yaml:84-88` — `INV-SPS-CONTRA-001` mapped to `linked_control: CTL-14A`, `normalized_business_invariants: [INV-003]`. Statement: "Same-rank blocking contradiction forbids advancement until reviewer resolution."
- `scripts/verify_m003_s01.sh` — runbook template: docker-compose up, alembic upgrade, worker + uvicorn in background, curl assertions, cleanup trap, assert_postgres helper.

## Constraints

- **Transactional atomicity:** The contradiction query in `apply_state_transition` must run inside the existing `with session.begin()` block, after the `session.get(PermitCase, ..., with_for_update=True)` lock acquisition. This prevents a race where a contradiction is resolved concurrently with the transition attempt.
- **Guard ordering:** Contradiction check comes before the ReviewDecision check. A case can have both a blocking contradiction AND a missing review — the denial reason should be `CONTRADICTION_ADVANCE_DENIED` (not `REVIEW_DECISION_REQUIRED`). This keeps the audit trail semantically meaningful.
- **Idempotency on `apply_state_transition`:** Adding the contradiction check does not affect the existing `request_id` idempotency path — if a ledger row already exists for `request_id`, the activity returns the persisted payload without re-executing any guard logic. No change needed there.
- **Schema gap is backward-compatible:** `resolved_at` and `resolved_by` are nullable — existing rows are unaffected by the migration. Alembic handles this with `nullable=True` + no `server_default`.
- **No workflow changes required for S03 verification:** The test proves the guard behavior via direct activity invocation + Postgres assertions. The workflow would raise `RuntimeError` on a `CONTRADICTION_ADVANCE_DENIED` (existing catch-all: "guarded transition did not apply after review"), which is loud and visible — acceptable for now. Workflow looping on contradiction denial is deferred.
- **Event type string:** `"CONTRADICTION_ADVANCE_DENIED"` — spec CTL-14A name. Add a named constant in `activities.py` alongside `_EVENT_APPROVAL_GATE_DENIED`.
- **`resolution_status` values:** Use `"OPEN"` (initial) and `"RESOLVED"` (after resolution). These must be consistent between the guard query, the create endpoint, and the resolve endpoint.

## Common Pitfalls

- **Contradiction check inside `begin()` block — not before:** If the query runs outside the transaction, a concurrent resolution between the query and the write is possible. Must be inside `with session.begin()` after the `FOR UPDATE` lock.
- **Non-blocking contradictions must not block:** The query filter is `blocking_effect=True AND resolution_status='OPEN'`. A contradiction with `blocking_effect=False` (informational) must not affect advancement. Test explicitly.
- **`_deny()` + ledger write still happen on contradiction denial:** The denial result must be persisted to `case_transition_ledger` with `event_type=CONTRADICTION_ADVANCE_DENIED`, same as `APPROVAL_GATE_DENIED`. The ledger is the audit trail — denials must be durable. The existing `session.add(CaseTransitionLedger(...))` block runs for all non-idempotent results, so no change needed in the outer structure.
- **Contradiction ID uniqueness:** `contradiction_id` is a client-provided PK with no uniqueness constraint beyond the primary key. Unlike `review_decisions.idempotency_key`, there's no separate idempotency mechanism. For S03, client provides a stable ID (e.g. `CON-<ULID>`); duplicate INSERT will raise `IntegrityError` — return 409. Keep it simple: catch `IntegrityError` in the create endpoint and return 409 `CONTRADICTION_ALREADY_EXISTS`.
- **Resolve endpoint idempotency:** If the contradiction is already `RESOLVED`, the resolve endpoint should return 409 `ALREADY_RESOLVED` (or 200 if idempotent is preferred — lean toward 409 to match spec fail-closed semantics; a resolver seeing a 409 knows the state).
- **`TRUNCATE ... CASCADE` in test teardown** must include `contradiction_artifacts`. The S02 `_reset_db` truncates `case_transition_ledger, review_decisions, permit_cases CASCADE`. S03 tests must also truncate `contradiction_artifacts`, or the CASCADE from `permit_cases` must cover it (it does, via FK ON DELETE RESTRICT — but TRUNCATE CASCADE will cascade).

## Schema: What to Add

**New migration columns on `contradiction_artifacts`:**
```python
sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True)
sa.Column('resolved_by', sa.Text(), nullable=True)
```

**ORM model additions:**
```python
resolved_at: Mapped[dt.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
resolved_by: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
```

**No new table needed for S03.** (Dissent artifacts land in S04.)

## New Endpoints

```
POST   /api/v1/contradictions                   — create contradiction artifact
POST   /api/v1/contradictions/{id}/resolve      — mark OPEN → RESOLVED
GET    /api/v1/contradictions/{id}              — read
```

All three gated with `require_reviewer_api_key`.

**Create request body** (spec-aligned, from 18.3):
- `contradiction_id: str` (client-provided stable ID)
- `case_id: str`
- `scope: str`
- `source_a: str`
- `source_b: str`
- `ranking_relation: str` (e.g. `"same_rank"`, `"higher_rank"`)
- `blocking_effect: bool`

**Resolve request body:**
- `resolved_by: str` (reviewer ID performing resolution)

## Test Scenarios for T04

| # | Scenario | Setup | Expected result |
|---|----------|-------|----------------|
| 1 | Blocking contradiction denies advancement | Seed case; POST create contradiction (`blocking_effect=true`, `resolution_status=OPEN`); call `apply_state_transition` with valid review ID | `DeniedStateTransitionResult` with `event_type=CONTRADICTION_ADVANCE_DENIED`, `guard_assertion_id=INV-SPS-CONTRA-001`, `normalized_business_invariants=["INV-003"]` |
| 2 | Resolving contradiction allows advancement | Scenario 1 setup; POST resolve; call `apply_state_transition` (new `request_id`) with valid review ID | `AppliedStateTransitionResult` with `event_type=CASE_STATE_CHANGED` |
| 3 | Non-blocking contradiction does not deny | Seed case + contradiction with `blocking_effect=false`; call `apply_state_transition` with valid review | `APPROVAL_GATE_DENIED` (not contradiction denial — review check still fires normally) |

**Note on test 3:** The non-blocking case still gets denied because no valid review exists (no `required_review_id`). The test verifies the _event type_ is `APPROVAL_GATE_DENIED` (not `CONTRADICTION_ADVANCE_DENIED`) — proving non-blocking contradictions are transparent to the advancement guard.

## Open Risks

- **`apply_state_transition` idempotency + contradiction interaction:** If a request was initially denied with `CONTRADICTION_ADVANCE_DENIED`, the ledger row has that event type. If the caller retries the same `request_id` after resolving the contradiction, the activity short-circuits to the ledger and returns `CONTRADICTION_ADVANCE_DENIED` again (the old denial is the authoritative record for that `request_id`). The workflow/caller must use a fresh `request_id` for the post-resolution attempt. This is correct per the current idempotency contract and documented in Decision #9. The workflow already does this (pre-computed `request_id_2` is distinct from `request_id_1`). The integration test must also use distinct `request_id` values.
- **Contradiction router prefix collision:** The contradiction router should be registered as `prefix="/api/v1/contradictions"` in `main.py` — distinct from the reviews router at `/api/v1/reviews`. Verify no route shadowing.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | `wshobson/agents@fastapi-templates` | available (from M003 research) |
| SQLAlchemy/Alembic | `wispbit-ai/skills@sqlalchemy-alembic-expert-best-practices-code-review` | available (from M003 research) |
| Pydantic v2 | `bobmatnyc/claude-mpm-skills@pydantic` | available (from M003 research) |

No new skills discovered beyond what M003 research identified. All three are available but not installed; patterns are well-established from existing codebase.

## Sources

- Contradiction artifact schema and same-rank blocking rule (source: `specs/sps/build-approved/spec.md` sections 18.2–18.3)
- CTL-14A denial semantics: event type `CONTRADICTION_ADVANCE_DENIED`, guard assertion `INV-SPS-CONTRA-001`, linked invariant `INV-003` (source: `specs/sps/build-approved/spec.md` section "20A. Guard Placement Matrix"; `invariants/sps/guard-assertions.yaml:84-88`)
- ContradictionArtifact ORM + migration (source: `src/sps/db/models.py:108-126`; `alembic/versions/02b39bad0a95_phase1_schema.py`)
- Guard structure and `_deny()` helper (source: `src/sps/workflows/permit_case/activities.py:111-218`)
- Reviewer endpoint patterns (source: `src/sps/api/routes/reviews.py`)
- S02 no-Temporal-worker integration test pattern (source: `tests/m003_s02_reviewer_independence_test.py`)
- `get_normalized_business_invariants` utility (source: `src/sps/guards/guard_assertions.py`)
