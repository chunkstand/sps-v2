---
id: S04
parent: M003-ozqkoh
milestone: M003-ozqkoh
provides:
  - dissent_artifacts Alembic migration (d8e2a4c9b1f5)
  - DissentArtifact SQLAlchemy model
  - ACCEPT_WITH_DISSENT Pydantic cross-field validator on CreateReviewDecisionRequest
  - Inline DissentArtifact INSERT in POST /api/v1/reviews/decisions (same transaction as ReviewDecision)
  - GET /api/v1/dissents/{dissent_id} read endpoint gated by require_reviewer_api_key
  - dissent_artifact_id field in ReviewDecisionResponse (populated for ACCEPT_WITH_DISSENT)
  - reviewer_api.dissent_artifact_created structured log event
  - 2-scenario integration test proving R009 end-to-end (tests/m003_s04_dissent_artifacts_test.py)
  - Operator runbook scripts/verify_m003_s04.sh exits 0
  - db.flush() FK ordering fix in POST /api/v1/reviews/decisions
requires:
  - slice: S01
    provides: ReviewDecision persistence + auth dependency (require_reviewer_api_key)
affects: []
key_files:
  - alembic/versions/d8e2a4c9b1f5_dissent_artifacts.py
  - src/sps/db/models.py
  - src/sps/api/routes/reviews.py
  - src/sps/api/routes/dissents.py
  - src/sps/api/main.py
  - tests/m003_s04_dissent_artifacts_test.py
  - scripts/verify_m003_s04.sh
key_decisions:
  - model_validator(mode='after') on CreateReviewDecisionRequest — fires after field coercions; outcome is already a ReviewDecisionOutcome enum when the check runs
  - dissent_artifact_id derived as f"DISSENT-{decision_id}" — no extra DB query; same formula in INSERT and response
  - db.flush() before DissentArtifact INSERT — forces ReviewDecision to DB first; required because no ORM relationship() declared; both rows still commit atomically
  - Log scope_len (length) not scope value — redaction constraint: dissent scope/rationale are free-text reviewer content
  - dissents.py follows contradictions.py structure exactly (auth reuse, _row_to_response helper, sync GET)
  - ondelete=RESTRICT for linked_review_id FK (protect audit trail); ondelete=CASCADE for case_id FK (clean up with case)
patterns_established:
  - Pydantic cross-field validator on CreateReviewDecisionRequest using model_validator(mode='after')
  - DissentArtifact FK style: RESTRICT for parent decision, CASCADE for parent case
  - dissents.py router pattern: require_reviewer_api_key import from reviews, _row_to_response helper, sync GET endpoint
  - _reset_db() truncation ordering: dissent_artifacts first (RESTRICT FK), then case_transition_ledger, review_decisions, contradiction_artifacts, permit_cases
observability_surfaces:
  - "reviewer_api.dissent_artifact_created dissent_id=... linked_review_id=... case_id=... scope_len=..." — emitted after db.add(dissent_row) before db.commit()
  - "GET /api/v1/dissents/{dissent_id}" — 200 with full DissentArtifactResponse or 404 with {"error":"not_found","dissent_id":"..."}
  - "dissent_artifact_id" field in 201 ReviewDecisionResponse — non-null only for ACCEPT_WITH_DISSENT
  - "SELECT dissent_id, linked_review_id, resolution_state FROM dissent_artifacts;" — DB inspection
drill_down_paths:
  - .gsd/milestones/M003-ozqkoh/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M003-ozqkoh/slices/S04/tasks/T02-SUMMARY.md
  - .gsd/milestones/M003-ozqkoh/slices/S04/tasks/T03-SUMMARY.md
duration: ~55m
verification_result: passed
completed_at: 2026-03-16
---

# S04: Dissent artifacts

**ACCEPT_WITH_DISSENT decisions durably persist a linked dissent_artifacts row in the same transaction; queryable via GET /api/v1/dissents/{dissent_id}; ACCEPT decisions create no dissent row — R009 proved end-to-end.**

## What Happened

**T01 — Schema, model, and request extension:** Wrote Alembic migration `d8e2a4c9b1f5_dissent_artifacts.py` chaining from `f3a1b9c2d7e4`. The migration creates `dissent_artifacts` with inline `ForeignKeyConstraint` entries (named explicitly) for both FK relationships: `linked_review_id → review_decisions.decision_id` (RESTRICT) and `case_id → permit_cases.case_id` (CASCADE). Separate index on `case_id`. Added `DissentArtifact` SQLAlchemy model to `models.py` after `ContradictionArtifact`, following the same column style. Extended `CreateReviewDecisionRequest` with three optional fields (`dissent_scope`, `dissent_rationale`, `dissent_required_followup`) and a `model_validator(mode='after')` that raises `ValueError` when outcome is `ACCEPT_WITH_DISSENT` and either `dissent_scope` or `dissent_rationale` is None.

**T02 — Inline dissent creation and read endpoint:** Wired `DissentArtifact` INSERT into `create_review_decision` between `db.add(row)` and `db.commit()` — fires only when `row.dissent_flag=True`. Both rows commit atomically in the existing `db.commit()`. Added `dissent_artifact_id: str | None = None` to `ReviewDecisionResponse`, derived as `f"DISSENT-{row.decision_id}"` (no extra query). Created `src/sps/api/routes/dissents.py` following `contradictions.py` exactly: `require_reviewer_api_key` imported from `reviews`, `DissentArtifactResponse` Pydantic model, `_row_to_response` helper, sync `GET /{dissent_id}` returning 200/404. Registered `dissents_router` in `main.py` under `/api/v1/dissents`. Added `reviewer_api.dissent_artifact_created` structured log event (logs `scope_len`, not raw scope value, per redaction constraint).

**T03 — Integration test and operator runbook:** Wrote `tests/m003_s04_dissent_artifacts_test.py` (2 scenarios, guarded by `SPS_RUN_TEMPORAL_INTEGRATION=1`) and `scripts/verify_m003_s04.sh` following S03 runbook conventions. First test run revealed a `ForeignKeyViolation` on `fk_dissent_artifacts_linked_review_id` — the ReviewDecision INSERT was being emitted after the DissentArtifact INSERT by SQLAlchemy's unit-of-work because no `relationship()` is declared between the two models. Fixed by adding `db.flush()` after `db.add(review_decision_row)` inside the `if row.dissent_flag:` branch, forcing the ReviewDecision to reach Postgres before the DissentArtifact INSERT while keeping both rows in the same transaction. After the fix, both scenarios passed and the runbook exited 0.

## Verification

- `python -c "from sps.db.models import DissentArtifact; print('ok')"` → ok
- `python -c "from sps.api.main import app; print('ok')"` → ok
- `python -c "from sps.api.routes.dissents import router; print('ok')"` → ok
- Pydantic validator: ACCEPT_WITH_DISSENT without dissent fields → ValidationError "dissent_scope and dissent_rationale are required when outcome is ACCEPT_WITH_DISSENT"
- `pytest tests/ -k "not (integration or temporal)" -x -q` → 9 passed, 9 skipped (no regressions)
- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s04_dissent_artifacts_test.py -v -s` → 2 passed
- `bash scripts/verify_m003_s04.sh` → exits 0; psql confirms `resolution_state=OPEN` for ACCEPT_WITH_DISSENT row; `COUNT=0` for ACCEPT case; 401 on missing key confirmed

## Requirements Advanced

- R009 — Dissent artifacts recorded and queryable

## Requirements Validated

- R009 — Proved: ACCEPT_WITH_DISSENT → `dissent_artifacts` row linked to `ReviewDecision`, queryable via `GET /api/v1/dissents/{dissent_id}` with correct `linked_review_id`, `case_id`, `scope`, `rationale`, `resolution_state=OPEN`; ACCEPT → no dissent row. Proven by 2 Postgres integration tests + operator runbook exits 0.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- Added `db.flush()` in `src/sps/api/routes/reviews.py` inside the `ACCEPT_WITH_DISSENT` branch — not in the task plan. Required to fix a latent FK ordering bug discovered during integration testing: SQLAlchemy's unit-of-work cannot infer FK-safe INSERT ordering without an ORM `relationship()` declaration. Decision #36 in DECISIONS.md.
- Integration test request payloads: plan described a generic JSON shape; actual `CreateReviewDecisionRequest` excludes `object_type`, `object_id`, `reviewer_independence_status` (derived by endpoint) and requires `subject_author_id`. Corrected during test authoring.

## Known Limitations

- `resolution_state` is always `OPEN` after creation — no transition API is implemented. Release-blocking enforcement (acting on dissent state before release) is deferred to a future release gate milestone.
- No dissent list endpoint (`GET /api/v1/dissents/` or `GET /api/v1/cases/{case_id}/dissents`) — only point lookup by `dissent_id`.

## Follow-ups

- Release gate milestone will need to act on `dissent_artifacts.resolution_state` before allowing case advancement past submission
- A `PATCH /api/v1/dissents/{dissent_id}/resolve` transition endpoint will be needed when release gating lands
- Consider declaring ORM `relationship()` between `ReviewDecision` and `DissentArtifact` to remove the `db.flush()` workaround at its root cause

## Files Created/Modified

- `alembic/versions/d8e2a4c9b1f5_dissent_artifacts.py` — new: creates `dissent_artifacts` table with all columns, FK constraints (RESTRICT/CASCADE), and case_id index
- `src/sps/db/models.py` — `DissentArtifact` class added after `ContradictionArtifact`
- `src/sps/api/routes/reviews.py` — three new optional fields + model_validator on `CreateReviewDecisionRequest`; DissentArtifact import; db.flush() + dissent INSERT block in ACCEPT_WITH_DISSENT path; `dissent_artifact_id` on `ReviewDecisionResponse`; `reviewer_api.dissent_artifact_created` log event
- `src/sps/api/routes/dissents.py` — new: `DissentArtifactResponse` model, `_row_to_response` helper, `GET /{dissent_id}` endpoint
- `src/sps/api/main.py` — `dissents_router` registered under `/api/v1/dissents`
- `tests/m003_s04_dissent_artifacts_test.py` — new: 2-scenario R009 integration test
- `scripts/verify_m003_s04.sh` — new: operator runbook, exits 0 on success
- `.gsd/DECISIONS.md` — decision #36 appended (db.flush() FK ordering)

## Forward Intelligence

### What the next slice should know
- M003 is now complete. All four Active requirements (R006–R009) are validated. The reviewer service has full authority-boundary enforcement, independence guard, contradiction blocking, and dissent artifact persistence.
- The `dissent_artifacts.resolution_state` field is always `OPEN` post-creation — no resolution transition exists yet. The release gate milestone will need to design this lifecycle.

### What's fragile
- `db.flush()` before DissentArtifact INSERT — this is a workaround for the missing ORM `relationship()`. It works correctly but is a non-obvious pattern. If the ACCEPT_WITH_DISSENT branch is refactored, the flush ordering must be preserved or a proper `relationship()` added.
- No `dissent_artifacts` index on `case_id` other than the explicit one created in the migration — queries by case will be fast, but any future join from `review_decisions` to `dissent_artifacts` relies on the `linked_review_id` UNIQUE index.

### Authoritative diagnostics
- `reviewer_api.dissent_artifact_created` log line — fires once per ACCEPT_WITH_DISSENT before db.commit(); includes `dissent_id`, `linked_review_id`, `case_id`, `scope_len`
- `GET /api/v1/dissents/{dissent_id}` with `X-Reviewer-Api-Key` — 200 + full artifact or 404
- `SELECT dissent_id, linked_review_id, resolution_state FROM dissent_artifacts;` — direct DB inspection

### What assumptions changed
- Initial plan assumed SQLAlchemy would order the two INSERTs correctly given only FK column references — in practice, without an ORM `relationship()`, INSERT ordering is unspecified and the FK violation surfaced immediately in integration testing.
