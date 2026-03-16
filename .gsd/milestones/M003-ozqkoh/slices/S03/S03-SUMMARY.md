---
id: S03
parent: M003-ozqkoh
milestone: M003-ozqkoh
provides:
  - Alembic migration adding resolved_at and resolved_by to contradiction_artifacts
  - ContradictionArtifact ORM updated with two new nullable Mapped fields
  - POST /api/v1/contradictions — create with blocking_effect, 409 on duplicate
  - POST /api/v1/contradictions/{id}/resolve — OPEN→RESOLVED; 409 if already resolved; 404 if unknown
  - GET /api/v1/contradictions/{id} — read-only inspection; 404 if unknown
  - All three endpoints gated with require_reviewer_api_key
  - Contradiction guard in apply_state_transition — blocking open contradictions deny REVIEW_PENDING→APPROVED_FOR_SUBMISSION before review gate
  - event_type=CONTRADICTION_ADVANCE_DENIED, guard_assertion_id=INV-SPS-CONTRA-001, normalized_business_invariants=["INV-003"]
  - 3 integration tests covering: blocking denial, resolve-then-advance, non-blocking transparency
  - Operator runbook scripts/verify_m003_s03.sh exits 0 against docker-compose Postgres
requires:
  - slice: S01
    provides: apply_state_transition guard structure; reviewer API key auth pattern; httpx ASGI test pattern
affects:
  - S04
key_files:
  - alembic/versions/f3a1b9c2d7e4_contradiction_artifacts_resolved_fields.py
  - src/sps/db/models.py
  - src/sps/api/routes/contradictions.py
  - src/sps/api/main.py
  - src/sps/workflows/permit_case/activities.py
  - tests/m003_s03_contradiction_blocking_test.py
  - scripts/verify_m003_s03.sh
key_decisions:
  - Contradiction guard runs before ReviewDecision check in the REVIEW_PENDING→APPROVED_FOR_SUBMISSION branch — contradiction is the more fundamental governance signal; audit trail stays semantically precise
  - Contradiction endpoints are sync (no Temporal I/O); require_reviewer_api_key imported directly from sps.api.routes.reviews
  - _seed_review_decision in tests uses direct ORM insert (not HTTP API) with all required non-nullable fields — avoids running a full API client inside sync seeder
  - Runbook seeds via inline python -c scripts to avoid psql JSONB/boolean quoting friction
patterns_established:
  - Guard precedence: contradiction denial → review gate denial → approval; each guard has its own event_type/guard_assertion_id constant pair
  - _seed_review_decision helper: direct ORM insert with all required ReviewDecision fields — reusable for tests needing a valid review gate bypass
  - 409 body always includes error string + contradiction_id; resolve 409 also includes resolution_status
observability_surfaces:
  - contradiction_api.create contradiction_id=... case_id=... blocking_effect=... — INFO on create
  - contradiction_api.resolve contradiction_id=... case_id=... — INFO on resolve
  - SELECT contradiction_id, blocking_effect, resolution_status, resolved_at, resolved_by FROM contradiction_artifacts WHERE case_id='...';
  - SELECT event_type, payload FROM case_transition_ledger WHERE case_id='...' ORDER BY occurred_at;
  - GET /api/v1/contradictions/{id} — read-only endpoint for contradiction artifact state without DB access
drill_down_paths:
  - .gsd/milestones/M003-ozqkoh/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M003-ozqkoh/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M003-ozqkoh/slices/S03/tasks/T03-SUMMARY.md
  - .gsd/milestones/M003-ozqkoh/slices/S03/tasks/T04-SUMMARY.md
duration: ~60m
verification_result: passed
completed_at: 2026-03-15
---

# S03: Contradiction artifacts + advancement blocking

**Blocking contradiction denies REVIEW_PENDING→APPROVED_FOR_SUBMISSION with stable identifiers; resolving via HTTP API allows advancement — proven by 3 integration tests and operator runbook against docker-compose Postgres.**

## What Happened

T01 laid the schema foundation: hand-authored Alembic migration `f3a1b9c2d7e4` adds `resolved_at` (nullable timestamptz) and `resolved_by` (nullable text) to `contradiction_artifacts`. `ContradictionArtifact` ORM gained two new `Mapped` fields. New `src/sps/api/routes/contradictions.py` defined `CreateContradictionRequest`, `ResolveContradictionRequest`, and `ContradictionResponse` Pydantic models, then registered three stub endpoints (all 501) gated by `require_reviewer_api_key` imported from `sps.api.routes.reviews`. Router wired into `main.py` under `/api/v1/contradictions`.

T02 inserted the contradiction guard into `apply_state_transition`. Two module-level constants added: `_EVENT_CONTRADICTION_ADVANCE_DENIED = "CONTRADICTION_ADVANCE_DENIED"` and `_GUARD_ASSERTION_CONTRADICTION = "INV-SPS-CONTRA-001"`. Inside the `REVIEW_PENDING → APPROVED_FOR_SUBMISSION` branch, after the `with_for_update=True` lock and `FROM_STATE_MISMATCH` check, a `session.query(ContradictionArtifact)` filters on `case_id`, `blocking_effect IS TRUE`, `resolution_status == 'OPEN'`. Any matching row triggers `_deny()` with the contradiction constants and `normalized_business_invariants=["INV-003"]`. The ReviewDecision check becomes the `else` branch — preserving its behavior unchanged. The race between a concurrent resolve and the guard check is closed by running the query inside the existing `with_for_update=True` transaction.

T03 replaced the three 501 stubs with full implementations following the `reviews.py` pattern. `_utcnow()` and `_row_to_response()` helpers keep the code DRY. `POST /` inserts with `resolution_status="OPEN"` and wraps commit in `try/except IntegrityError` → rollback + 409. `POST /{id}/resolve` loads by PK (404 if missing), checks `resolution_status == "OPEN"` (409 if not), sets `RESOLVED` + `resolved_at` + `resolved_by`, commits. `GET /{id}` loads by PK and returns full `ContradictionResponse`.

T04 wrote `tests/m003_s03_contradiction_blocking_test.py` with three integration tests: (1) blocking contradiction denies advancement — seeds case + ReviewDecision (proving denial is from contradiction guard, not missing review), POSTs blocking contradiction, asserts `DeniedStateTransitionResult` with `event_type=CONTRADICTION_ADVANCE_DENIED`, `guard_assertion_id=INV-SPS-CONTRA-001`, `normalized_business_invariants=["INV-003"]`, and verifies the ledger row payload in Postgres. (2) Resolve allows advancement — same setup, POSTs resolve, calls `apply_state_transition` with fresh `request_id`, asserts `AppliedStateTransitionResult` with `event_type=CASE_STATE_CHANGED`, DB-verifies `resolution_status=RESOLVED` and `case_state=APPROVED_FOR_SUBMISSION`. (3) Non-blocking transparency — seeds case only (no review), POSTs contradiction with `blocking_effect=false`, calls `apply_state_transition` without valid review_id, asserts `event_type=APPROVAL_GATE_DENIED` and `guard_assertion_id != INV-SPS-CONTRA-001`.

The operator runbook `scripts/verify_m003_s03.sh` drives the full scenario via HTTP against a live FastAPI server + docker-compose Postgres: create → 201, DB assert, resolve → 200, assert RESOLVED, apply transition → `CASE_STATE_CHANGED` in ledger, GET artifact → 200, 401 on missing/wrong key, 409 on duplicate create.

Two minor runbook fixes during T04 iteration: `mktemp` template required X's at end (macOS constraint), and psql boolean assertion needed `"t"` not `"true"` (psql `-A -t` raw output format).

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m003_s03_contradiction_blocking_test.py -v -s` → **3 passed**
- `.venv/bin/pytest tests/ -k "not (integration or temporal)" -x -q` → **9 passed, 8 skipped** (no regressions)
- `bash scripts/verify_m003_s03.sh` → **exits 0**, runbook: ok

## Requirements Advanced

- R008 — Contradiction blocking denial + resolve-allows-advance proven against real Postgres; moving to validated

## Requirements Validated

- R008 — Proved: blocking contradiction → `CONTRADICTION_ADVANCE_DENIED` with `guard_assertion_id=INV-SPS-CONTRA-001` + `normalized_business_invariants=["INV-003"]`; resolving via HTTP API → next `apply_state_transition` returns `CASE_STATE_CHANGED`; non-blocking contradictions are transparent to the guard

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- `_seed_review_decision` in tests uses direct ORM insert (not HTTP API) — required to avoid starting a full API client inside the sync seeder; all required ReviewDecision fields populated explicitly including `schema_version`, `object_type`, `object_id`, `dissent_flag`, `decision_at`.
- Runbook uses inline `python -c` for seeding and `apply_state_transition` invocation instead of a standalone helper script — simpler, no additional script to maintain.

## Known Limitations

- Contradiction detector is not yet implemented — contradictions are created manually via the HTTP API. The spec notes a detector can arrive later; manual API create/resolve is intentional Phase 3 scope.
- No pagination on contradiction listing — no `GET /api/v1/contradictions?case_id=...` endpoint; individual lookup only. Deferred to when query surfaces are needed by downstream slices.

## Follow-ups

- S04 (dissent artifacts) is the only remaining M003 requirement.

## Files Created/Modified

- `alembic/versions/f3a1b9c2d7e4_contradiction_artifacts_resolved_fields.py` — new migration: adds resolved_at and resolved_by to contradiction_artifacts
- `src/sps/db/models.py` — ContradictionArtifact: added resolved_at and resolved_by Mapped fields
- `src/sps/api/routes/contradictions.py` — new router with full implementations of POST /, POST /{id}/resolve, GET /{id}
- `src/sps/api/main.py` — registered contradictions_router under /api/v1/contradictions
- `src/sps/workflows/permit_case/activities.py` — two new constants; ContradictionArtifact import; contradiction guard block before ReviewDecision check
- `tests/m003_s03_contradiction_blocking_test.py` — 3 integration tests for S03 scenarios
- `scripts/verify_m003_s03.sh` — operator runbook, exits 0 against docker-compose Postgres

## Forward Intelligence

### What the next slice should know

- S04 (dissent artifacts) follows the same structure: a new ORM model + new router + router registered in main.py + endpoint implementation + integration test. T01–T04 decomposition will apply.
- `_seed_review_decision` helper in `m003_s03_contradiction_blocking_test.py` is the canonical pattern for seeding `ReviewDecision` rows in integration tests — reuse it for S04 tests that need a valid review to dissent against.
- The `ContradictionResponse` schema (11 fields) and `_row_to_response()` helper in `contradictions.py` are the reference pattern for the `DissentsResponse` shape S04 will need.

### What's fragile

- `require_reviewer_api_key` is imported from `sps.api.routes.reviews` into `contradictions.py` — if the reviews router is ever refactored or split, this import will break. It's documented in DECISIONS.md (decision 33) but worth noting.
- The `_reset_db()` helper truncates `contradiction_artifacts` via `permit_cases CASCADE` — if test order matters and a test leaves uncommitted state (e.g. session not closed), the TRUNCATE might miss rows. Tests are currently ordered correctly and pass consistently.

### Authoritative diagnostics

- `SELECT event_type, payload FROM case_transition_ledger WHERE case_id='...' ORDER BY occurred_at` — shows exact guard firing sequence including `CONTRADICTION_ADVANCE_DENIED` payload with `guard_assertion_id` and `normalized_business_invariants`
- `GET /api/v1/contradictions/{id}` — confirms contradiction state without DB access; the denial reason is inspectable cross-system via this endpoint
- `docker compose logs api | grep contradiction_api` — structured create/resolve log events for operator-side correlation

### What assumptions changed

- Integration test T04 assumed `_seed_review_decision` could use the HTTP API for seeding — discovered during implementation that this requires starting a full async client inside a sync seeder. Direct ORM insert with explicit field population is the correct pattern.
- Runbook `mktemp` template and psql boolean assertion format (`"t"` not `"true"`) were discovered during runbook smoke-test iteration, not during planning.
