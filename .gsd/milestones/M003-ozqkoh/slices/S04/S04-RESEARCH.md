# M003-ozqkoh / S04 — Research

**Date:** 2026-03-16

## Summary

S04 is the simplest slice in M003: persist a `DisssentArtifact` row whenever a `ReviewDecision` with `outcome=ACCEPT_WITH_DISSENT` is recorded, link it to the originating `decision_id`, and expose it via a read endpoint. No DB guard changes, no Temporal involvement, no new auth pattern — every piece of infrastructure this slice needs already exists.

The key finding is that **no `DisssentArtifact` model or table exists yet**. The `ReviewDecision` row already carries a `dissent_flag` boolean (set to `True` in `create_review_decision` when `outcome == ACCEPT_WITH_DISSENT`), but no separate artifact row is created. S04's only schema work is adding a new `dissent_artifacts` table via a new Alembic migration. The required fields come directly from the spec artifact contract matrix (row for "dissent artifact"): `dissent_id`, `linked_review_id`, `scope`, `rationale`, `required_followup`, `resolution_state`, `created_at` — plus `case_id` for case-scoped queries (derivable from the linked review, but useful as a denormalized FK for index and audit purposes).

The implementation shape mirrors the `ContradictionArtifact` lifecycle exactly: a new SQLAlchemy model, a new FastAPI router (`dissents.py`), registered in `main.py`, with sync endpoints (no Temporal I/O), gated by the existing `require_reviewer_api_key` dependency. The dissent artifact is created inline in `POST /api/v1/reviews/decisions` whenever `dissent_flag` is True — no separate "create dissent" endpoint needed by the spec for this phase. A `GET /api/v1/dissents/{dissent_id}` read endpoint provides the queryable surface required by R009.

## Recommendation

Implement in this order:

1. **Alembic migration** — new `dissent_artifacts` table with columns: `dissent_id` (PK text), `linked_review_id` (text FK → `review_decisions.decision_id`), `case_id` (text FK → `permit_cases.case_id`, index), `scope` (text), `rationale` (text), `required_followup` (text nullable), `resolution_state` (text, default `"OPEN"`), `created_at` (timestamptz).

2. **SQLAlchemy model** — `DissentArtifact` class in `src/sps/db/models.py` following the `ContradictionArtifact` pattern.

3. **Inline dissent creation in `POST /api/v1/reviews/decisions`** — after the `ReviewDecision` INSERT succeeds, and before the Temporal signal, check `dissent_flag` and if True INSERT a `DisssentArtifact` row in the same transaction (same `db.commit()` covers both, or commit decision first and create dissent in a second operation — same-transaction is cleaner and prevents a "decision without dissent artifact" partial state).

4. **Read endpoint** — `GET /api/v1/dissents/{dissent_id}` in a new `src/sps/api/routes/dissents.py` router, gated by `require_reviewer_api_key`, sync, following the `contradictions.py` pattern exactly.

5. **Integration test** — `tests/m003_s04_dissent_artifacts_test.py` — two scenarios: (a) ACCEPT_WITH_DISSENT decision creates a linked dissent artifact row queryable via GET; (b) ACCEPT decision does not create a dissent artifact. Guard with `SPS_RUN_TEMPORAL_INTEGRATION=1` (real Postgres, no Temporal worker needed).

6. **Operator runbook** — `scripts/verify_m003_s04.sh` following the S03 runbook pattern: POST decision with ACCEPT_WITH_DISSENT outcome, GET dissent artifact, assert DB row.

The key design choice for `scope` and `rationale`: since `CreateReviewDecisionRequest` does not currently include dissent-specific fields, the POST request must be extended with optional `dissent_scope` and `dissent_rationale` fields that are required (validated) when `outcome == ACCEPT_WITH_DISSENT`. This is a pure Pydantic validation concern — a custom model validator on `CreateReviewDecisionRequest` that raises `ValueError` if `outcome == ACCEPT_WITH_DISSENT` and `dissent_scope` or `dissent_rationale` is None.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Dissent artifact DB persistence | Follow `ContradictionArtifact` pattern in `models.py` | Identical structural pattern: nullable FK, text PK, timestamptz created_at; no need to reinvent column choices |
| Reviewer endpoint auth | `require_reviewer_api_key` from `sps.api.routes.reviews` | Already imported into `contradictions.py`; same import pattern works for `dissents.py` (documented in DECISIONS #33) |
| Sync endpoint pattern | All three `contradictions.py` endpoints are `def` (not `async`) | No Temporal I/O in dissent lifecycle; sync is simpler and consistent |
| In-process FastAPI test client | `httpx.ASGITransport(app=app)` + `AsyncClient(transport=...)` | Established in DECISIONS #30; `httpx.AsyncClient(app=app)` was removed in httpx 0.20 |
| DB seeding for test isolation | `_seed_review_decision` helper from `m003_s03_contradiction_blocking_test.py` | Canonical ORM insert pattern for seeding ReviewDecision rows in integration tests; reuse directly |
| Idempotency / no duplicates | Dissent artifact is created in the same DB transaction as the ReviewDecision, keyed on `linked_review_id` (unique) | Prevents double-creation under API retry if the endpoint is called twice with the same idempotency key — the idempotency check on `review_decisions.idempotency_key` returns the existing row (200) before reaching the dissent insert |

## Existing Code and Patterns

- `src/sps/db/models.py` — no `DissentArtifact` model exists yet; `ContradictionArtifact` (lines 108–128) is the structural reference: text PK, case_id FK, nullable fields, `created_at` timestamptz. Add `DissentArtifact` here.
- `src/sps/api/routes/reviews.py` — `POST /api/v1/reviews/decisions` currently sets `dissent_flag` from outcome (line 254) but does not create any artifact. The dissent INSERT should go here after the `db.commit()` (or restructured into a single transaction covering both rows).
- `src/sps/api/routes/contradictions.py` — reference implementation for a reviewer-gated artifact router: `require_reviewer_api_key` import, sync endpoints, `_utcnow()` helper, `_row_to_response()`, `IntegrityError` → 409 pattern.
- `src/sps/api/main.py` — registers routers at `include_router(..., prefix="/api/v1/...")`. Add `dissents_router` here.
- `alembic/versions/f3a1b9c2d7e4_contradiction_artifacts_resolved_fields.py` — migration pattern reference: hand-authored revision ID, `down_revision` chaining, `op.create_table()` / `op.add_column()` style.
- `tests/m003_s03_contradiction_blocking_test.py` — `_seed_review_decision()` helper (ORM insert with all required ReviewDecision fields) and `_reset_db()` teardown pattern (TRUNCATE via CASCADE from `permit_cases`). Reuse both in S04 tests.
- `scripts/verify_m003_s03.sh` — operator runbook template: docker compose up, apply migrations, start API, curl scenario, psql assertions, cleanup. Follow identically for S04.

## Constraints

- `linked_review_id` must be a FK to `review_decisions.decision_id` — enforces the spec requirement that "linked review existence" is validated. An orphaned dissent artifact (pointing to a nonexistent review) is structurally invalid.
- `dissent_artifacts.linked_review_id` should have a UNIQUE constraint — one dissent artifact per review decision. The spec does not say "one per review" explicitly, but it refers to "a dissent artifact" (singular) linked to a review, and allowing multiple would create ambiguity in the audit trail.
- Dissent artifact creation must be atomic with (or immediately follow) the `ReviewDecision` commit. The idempotency check on `review_decisions.idempotency_key` short-circuits the endpoint on retry (returns 200), so a failed dissent INSERT on first attempt that leaves a ReviewDecision without an artifact is a data consistency gap. Putting both INSERTs in the same `session.begin()` block eliminates this risk.
- `resolution_state` enum values should be `"OPEN"` and `"RESOLVED"` — matching `ContradictionArtifact.resolution_status` for consistency; the spec says "active until resolved."
- S04 scope is **record + query only**: no release gating, no resolver endpoint, no second-review escalation enforcement. Resolution state is always `"OPEN"` at creation; the resolve lifecycle is explicitly out of scope per DECISIONS #23.
- Workflow determinism is not involved — dissent persistence happens entirely in the FastAPI reviewer endpoint, not in Temporal activities.
- `required_followup` is nullable — the spec says it's a field, but a dissent without a specific followup requirement is valid (e.g., a minor note-level dissent).

## Common Pitfalls

- **Dissent artifact without linked review** — If the dissent INSERT is in a separate transaction and the first transaction (ReviewDecision) commits but the process dies before the second, you get a ReviewDecision with `dissent_flag=True` but no artifact row. Avoid by inserting both in the same `session.begin()` block, or by checking for a missing artifact on the idempotent 200 path and creating it then.
- **Missing `dissent_scope` / `dissent_rationale` when outcome is ACCEPT_WITH_DISSENT** — If the Pydantic model doesn't validate this, you'll get a dissent artifact with null `scope` and `rationale`, which is structurally invalid per spec. Use a `model_validator(mode='after')` on `CreateReviewDecisionRequest` to enforce: if `outcome == ACCEPT_WITH_DISSENT` then `dissent_scope` and `dissent_rationale` must be non-null.
- **TRUNCATE ordering in test teardown** — `_reset_db()` from S03 tests truncates via `permit_cases CASCADE`. If `dissent_artifacts.case_id` FK is `ondelete="CASCADE"`, dissent rows are cleaned automatically. If not, the TRUNCATE will fail with an FK violation. Set `ondelete="CASCADE"` on the `case_id` FK (same as `contradiction_artifacts`), OR explicitly truncate `dissent_artifacts` before `permit_cases` in the test teardown.
- **`linked_review_id` FK ondelete policy** — `review_decisions` uses `ondelete="RESTRICT"` on its FK to `permit_cases`. The dissent artifact FK to `review_decisions` should also be `ondelete="RESTRICT"` — prevents deleting a review with linked dissents (which are audit-required).
- **psql boolean format in runbook assertions** — S03 discovered `psql -A -t` outputs `"t"` not `"true"` for boolean True. S04 runbook doesn't need boolean assertions directly (resolution_state is text), but worth noting.
- **`mktemp` template on macOS** — requires trailing X's: `mktemp /tmp/sps-s04.XXXXXX`. S03 discovered this during runbook iteration.

## Open Risks

- **`scope` field semantics are underspecified** — the spec names `scope` as a required field but does not enumerate allowed values. Using free-text (same as `ContradictionArtifact.scope`) is the safest choice for Phase 3. No enum constraint.
- **Dissent artifact not included in `_row_to_response` in reviews route** — the existing `ReviewDecisionResponse` does not expose whether a dissent artifact was created. This is acceptable for S04 scope (the GET dissent endpoint provides that), but API consumers need to know to call `GET /api/v1/dissents/...` separately. A `dissent_artifact_id` field could be added to `ReviewDecisionResponse` in the future, but it's not required by R009.
- **Test isolation dependency on `linked_review_id` uniqueness** — if two tests create a dissent artifact for the same `decision_id` without resetting DB state, the second will fail with a UNIQUE constraint violation. The `_reset_db()` teardown from S03 (run as `autouse` fixture) should handle this, but test ordering matters.
- **No resolver/update endpoint** — DECISIONS #23 explicitly defers resolution state updates. If a future slice adds resolve-dissent, it will need a new endpoint. S04 only needs `resolution_state = "OPEN"` at creation and a read endpoint; no state mutations in scope.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | `wshobson/agents@fastapi-templates` | available (noted in M003 research; not needed — patterns fully established in codebase) |
| SQLAlchemy/Alembic | `wispbit-ai/skills@sqlalchemy-alembic-expert-best-practices-code-review` | available (not needed — migration pattern clear from existing versions) |
| Pydantic v2 | `bobmatnyc/claude-mpm-skills@pydantic` | available (not needed — model_validator usage is standard Pydantic v2) |

## Sources

- Dissent artifact required fields: `dissent_id`, `linked_review_id`, `scope`, `rationale`, `required_followup`, `resolution_state`, `created_at` (source: `specs/sps/build-approved/spec.md` section "10A.2 Artifact Contract Matrix", dissent artifact row)
- Dissent rules: ACCEPT_WITH_DISSENT preserved indefinitely with linked resolution artifact; release-blocking when unresolved on high-risk surfaces (source: `specs/sps/build-approved/spec.md` section "17.6 Dissent Rules")
- S04 scope: record + query only; no release gating (source: DECISIONS #23, M003-CONTEXT.md "In Scope" section)
- `ContradictionArtifact` ORM pattern and `contradictions.py` endpoint pattern — structural reference for DisssentArtifact (source: `src/sps/db/models.py` lines 108–128; `src/sps/api/routes/contradictions.py`)
- Reviewer endpoint auth reuse pattern: `require_reviewer_api_key` importable across routers (source: DECISIONS #33; `src/sps/api/routes/contradictions.py` line 11)
- S03 `_seed_review_decision` helper and `_reset_db()` teardown — canonical test seeding pattern for dissent tests (source: `tests/m003_s03_contradiction_blocking_test.py`)
- `dissent_flag` already set in `create_review_decision` (source: `src/sps/api/routes/reviews.py` line 254)
- Dissent conditionally required artifact path: `/dissent/sps/*.yaml` (source: `specs/sps/build-approved/artifact-obligations.yaml`)
