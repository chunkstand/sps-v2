# S04: Dissent artifacts

**Goal:** `ACCEPT_WITH_DISSENT` decisions durably persist a linked `dissent_artifacts` row; the artifact is queryable via a read endpoint; `ACCEPT` decisions create no dissent row.

**Demo:** `POST /api/v1/reviews/decisions` with `outcome=ACCEPT_WITH_DISSENT` + `dissent_scope` + `dissent_rationale` → 201 + linked `dissent_artifacts` row; `GET /api/v1/dissents/{dissent_id}` → full artifact. Same POST with `outcome=ACCEPT` → 201, no dissent row. Proven by integration test against real Postgres (no Temporal worker needed).

## Must-Haves

- `dissent_artifacts` table exists with correct schema: `dissent_id` (PK), `linked_review_id` (FK → `review_decisions`, unique), `case_id` (FK → `permit_cases`, index), `scope`, `rationale`, `required_followup` (nullable), `resolution_state` (default `"OPEN"`), `created_at` (timestamptz)
- `CreateReviewDecisionRequest` validates that `dissent_scope` and `dissent_rationale` are non-null when `outcome == ACCEPT_WITH_DISSENT` (Pydantic `model_validator`)
- `DissentArtifact` row inserted in the **same DB transaction** as the `ReviewDecision` when `dissent_flag=True` — no partial state (decision without artifact) is possible
- `GET /api/v1/dissents/{dissent_id}` — gated by `require_reviewer_api_key`; returns full artifact; 404 on unknown
- Integration test proves both scenarios: ACCEPT_WITH_DISSENT → dissent row queryable; ACCEPT → no row
- Operator runbook (`scripts/verify_m003_s04.sh`) exits 0 against docker-compose

## Observability / Diagnostics

Runtime signals this slice emits:

- **`reviewer_api.dissent_artifact_created`** — structured log line emitted in `create_review_decision` immediately after `db.add(dissent_row)` and before `db.commit()`. Fields: `decision_id`, `dissent_id`, `case_id`, `scope`. Lets an operator grep the log to confirm artifact creation without hitting the DB.
- **`reviewer_api.dissent_validation_rejected`** — Pydantic `ValidationError` surfaced as HTTP 422 with a structured detail body listing which fields (`dissent_scope`, `dissent_rationale`) were missing. The FastAPI default unhandled-validation response already includes field paths; no extra handler needed.
- **`dissent_artifacts` table** — inspectable via `psql -c "SELECT dissent_id, linked_review_id, resolution_state FROM dissent_artifacts;"` for operator confirmation.
- **`GET /api/v1/dissents/{dissent_id}`** — read surface for a single artifact; 404 with `{"error": "not_found", "dissent_id": "..."}` if the ID is unknown. Both response shapes are safe to log (no PII, no secrets).
- **Redaction constraint:** `scope` and `rationale` fields may contain free-form text entered by the reviewer. Do not log full field values; log only `dissent_id`, `linked_review_id`, `case_id`, `resolution_state`.

Failure visibility:

- Missing dissent fields on `ACCEPT_WITH_DISSENT` → HTTP 422 + Pydantic error detail listing paths `dissent_scope` / `dissent_rationale`.
- FK violation (unknown `case_id` or `decision_id`) → DB `IntegrityError` → HTTP 500 with structured error; operator checks postgres logs for constraint name.
- Transaction partial failure: if `db.commit()` fails after `db.add(dissent_row)`, both the `ReviewDecision` and `DissentArtifact` are rolled back (same session). Log `reviewer_api.decision_commit_failed` at ERROR with `decision_id` and `exc_type`.

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s04_dissent_artifacts_test.py -v -s` — 2 scenarios pass
- `bash scripts/verify_m003_s04.sh` — exits 0; curl + psql assertions confirm dissent artifact row created for ACCEPT_WITH_DISSENT, absent for ACCEPT
- `pytest tests/ -k "not (integration or temporal)" -x -q` — existing unit tests unaffected
- **Diagnostic check:** `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s04_dissent_artifacts_test.py -v -s -k accept_with_dissent` and inspect log output for `reviewer_api.dissent_artifact_created` line — confirms observability signal fires on the happy path
- **Failure-path check:** `python -c "from sps.api.routes.reviews import CreateReviewDecisionRequest; from pydantic import ValidationError; [...]"` — ACCEPT_WITH_DISSENT without dissent fields raises `ValidationError` with paths `dissent_scope` and `dissent_rationale`

## Tasks

- [x] **T01: Schema, model, and request extension** `est:30m`
  - Why: New table + SQLAlchemy model establish the persistence layer; Pydantic validator enforces dissent field requirements at the API boundary before any DB write
  - Files: `alembic/versions/d8e2a4c9b1f5_dissent_artifacts.py` (new), `src/sps/db/models.py`, `src/sps/api/routes/reviews.py`
  - Do: (1) Write Alembic migration `d8e2a4c9b1f5` with `down_revision='f3a1b9c2d7e4'` — `op.create_table('dissent_artifacts', ...)` with all required columns + UNIQUE constraint on `linked_review_id` + index on `case_id`; `op.create_foreign_key` for both FKs (`ondelete="RESTRICT"` for `linked_review_id → review_decisions`, `ondelete="CASCADE"` for `case_id → permit_cases`). (2) Add `DissentArtifact` SQLAlchemy model to `models.py` following `ContradictionArtifact` pattern. (3) Add `dissent_scope: str | None = None` and `dissent_rationale: str | None = None` and `dissent_required_followup: str | None = None` optional fields to `CreateReviewDecisionRequest`; add `model_validator(mode='after')` that raises `ValueError` if `outcome == ACCEPT_WITH_DISSENT` and either `dissent_scope` or `dissent_rationale` is None.
  - Verify: `python -c "from sps.db.models import DissentArtifact; print('ok')"` → ok; `python -c "from sps.api.routes.reviews import CreateReviewDecisionRequest; ..."` imports cleanly; alembic `upgrade --sql` includes `dissent_artifacts` DDL
  - Done when: model imports cleanly, Pydantic validator rejects ACCEPT_WITH_DISSENT with missing dissent fields, and alembic upgrade would create the table

- [x] **T02: Inline dissent creation and read endpoint** `est:30m`
  - Why: Wires dissent persistence into the POST decision endpoint (same transaction) and exposes the GET read surface required by R009
  - Files: `src/sps/api/routes/reviews.py`, `src/sps/api/routes/dissents.py` (new), `src/sps/api/main.py`
  - Do: (1) In `create_review_decision` in `reviews.py`, immediately after `db.add(row)` and before `db.commit()`, check `if req.outcome == ReviewDecisionOutcome.ACCEPT_WITH_DISSENT:` → construct and `db.add()` a `DissentArtifact` row (same session, committed together). Import `DissentArtifact` and `ulid`/`uuid` for `dissent_id` generation. (2) Create `src/sps/api/routes/dissents.py`: import `require_reviewer_api_key` from `sps.api.routes.reviews`; define `DissentArtifactResponse` Pydantic model; sync `GET /dissents/{dissent_id}` endpoint returning 200 or 404; follow `contradictions.py` pattern exactly (sync def, `_row_to_response()` helper). (3) Register `dissents_router` in `src/sps/api/main.py` under `prefix="/api/v1"`.
  - Verify: `python -c "from sps.api.main import app; print('ok')"` → ok; `python -c "from sps.api.routes.dissents import router; print('ok')"` → ok; `pytest tests/ -k "not (integration or temporal)" -x -q` still passes
  - Done when: app imports cleanly, dissents router registered, inline dissent INSERT is in the same `db.add()` block as the ReviewDecision, and unit tests remain green

- [x] **T03: Integration test and operator runbook** `est:40m`
  - Why: Proves R009 end-to-end against real Postgres and provides an operator verification script following M003 runbook conventions
  - Files: `tests/m003_s04_dissent_artifacts_test.py` (new), `scripts/verify_m003_s04.sh` (new)
  - Do: (1) Write `tests/m003_s04_dissent_artifacts_test.py` guarded by `SPS_RUN_TEMPORAL_INTEGRATION=1`; reuse `_seed_permit_case`, `_wait_for_postgres_ready`, `_migrate_db`, `_reset_db` helpers (inline — no import from s03 test); two scenarios: (a) POST ACCEPT_WITH_DISSENT decision → 201, then GET `/api/v1/dissents/{dissent_id}` → 200 with correct `linked_review_id`, `case_id`, `scope`, `rationale`, `resolution_state="OPEN"`; (b) POST ACCEPT decision → 201, then confirm no dissent row via DB query. Use `httpx.ASGITransport(app=app)` + `AsyncClient(transport=...)` pattern. (2) Write `scripts/verify_m003_s04.sh` following `verify_m003_s03.sh` structure: docker-compose up (postgres + api), apply migrations, start uvicorn, POST ACCEPT_WITH_DISSENT → assert 201, GET dissent → assert 200, psql assert row exists with `resolution_state = 'OPEN'`, POST ACCEPT → psql assert no dissent row for that `linked_review_id`, assert 401 on missing key. Use `mktemp /tmp/sps-s04.XXXXXX` (trailing X's for macOS compatibility).
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s04_dissent_artifacts_test.py -v -s` → 2 passed; `bash scripts/verify_m003_s04.sh` → exits 0
  - Done when: both integration tests pass against real Postgres and runbook exits 0

## Files Likely Touched

- `alembic/versions/d8e2a4c9b1f5_dissent_artifacts.py` (new)
- `src/sps/db/models.py`
- `src/sps/api/routes/reviews.py`
- `src/sps/api/routes/dissents.py` (new)
- `src/sps/api/main.py`
- `tests/m003_s04_dissent_artifacts_test.py` (new)
- `scripts/verify_m003_s04.sh` (new)
