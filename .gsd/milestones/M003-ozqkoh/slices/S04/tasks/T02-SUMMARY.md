---
id: T02
parent: S04
milestone: M003-ozqkoh
provides:
  - DissentArtifact INSERT wired into POST /api/v1/reviews/decisions (same transaction as ReviewDecision)
  - ReviewDecisionResponse.dissent_artifact_id field (populated for ACCEPT_WITH_DISSENT)
  - GET /api/v1/dissents/{dissent_id} endpoint with 200/404 responses, gated by require_reviewer_api_key
  - reviewer_api.dissent_artifact_created structured log event
key_files:
  - src/sps/api/routes/reviews.py
  - src/sps/api/routes/dissents.py
  - src/sps/api/main.py
key_decisions:
  - Log scope_len (length) not scope value to avoid logging free-text reviewer content (redaction constraint from S04 plan)
  - dissent_artifact_id in ReviewDecisionResponse derived from f"DISSENT-{decision_id}" — same formula used in INSERT, no extra DB query
patterns_established:
  - dissents.py follows contradictions.py structure exactly: require_reviewer_api_key import, _row_to_response helper, sync GET endpoint, 404 detail includes artifact ID
observability_surfaces:
  - "reviewer_api.dissent_artifact_created dissent_id=... linked_review_id=... case_id=... scope_len=..." — emitted after db.add(dissent_row) before db.commit()
  - "GET /api/v1/dissents/{dissent_id}" — 200 with full DissentArtifactResponse or 404 with {"error": "not_found", "dissent_id": "..."}
  - "python -c 'from sps.api.main import app; print(\"ok\")'" → confirms all routers importable
  - "python -c 'from sps.api.routes.dissents import router; print(\"ok\")'" → confirms dissents router importable
duration: ~15m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Inline dissent creation and read endpoint

**DissentArtifact INSERT wired into the POST /api/v1/reviews/decisions transaction; GET /api/v1/dissents/{dissent_id} endpoint live.**

## What Happened

Added `DissentArtifact` to the import in `reviews.py` and inserted the dissent block between `db.add(row)` and `db.commit()`. The block fires only when `row.dissent_flag=True` (ACCEPT_WITH_DISSENT). `dissent_scope` and `dissent_rationale` are guaranteed non-null at this point by the `model_validator` from T01. Both rows commit atomically in the existing `db.commit()` call — no new transaction boundary.

Added `dissent_artifact_id: str | None = None` to `ReviewDecisionResponse` and updated `_row_to_response` to derive it via `f"DISSENT-{row.decision_id}"` when `row.dissent_flag=True`. Callers now get the linked artifact ID directly in the 201 response without a second query.

Created `src/sps/api/routes/dissents.py` following the `contradictions.py` structure: `require_reviewer_api_key` imported from `sps.api.routes.reviews`, `DissentArtifactResponse` Pydantic model covering all columns, `_row_to_response` helper, and a sync `GET /{dissent_id}` endpoint using `db.get(DissentArtifact, dissent_id)` with 200/404 responses.

Registered `dissents_router` in `main.py` under `prefix="/api/v1/dissents"` alongside existing routers.

Added `reviewer_api.dissent_artifact_created` structured log line. Logs `dissent_id`, `linked_review_id`, `case_id`, and `scope_len` (length only — not the scope value itself, per the S04 redaction constraint on free-text reviewer fields).

## Verification

- `python -c "from sps.api.main import app; print('ok')"` → `ok`
- `python -c "from sps.api.routes.dissents import router; print('ok')"` → `ok`
- `pytest tests/ -k "not (integration or temporal)" -x -q` → 9 passed, 8 skipped (no regressions)
- Code review: `db.add(dissent_row)` at line 292, `db.commit()` at line 301 — dissent INSERT is before commit
- Manual Python: ACCEPT_WITH_DISSENT with valid fields → parses OK; ACCEPT_WITH_DISSENT missing dissent fields → ValidationError; ReviewDecisionResponse.dissent_artifact_id=`DISSENT-D-001` for ACCEPT_WITH_DISSENT; `None` for ACCEPT

## Diagnostics

- **Dissent log signal:** grep application logs for `reviewer_api.dissent_artifact_created` — fires once per ACCEPT_WITH_DISSENT decision, before commit. Includes `dissent_id`, `linked_review_id`, `case_id`, `scope_len`.
- **Read surface:** `GET /api/v1/dissents/{dissent_id}` with `X-Reviewer-Api-Key` header → 200 + full artifact, or 404 + `{"error": "not_found", "dissent_id": "..."}`.
- **Transaction failure:** if `db.commit()` fails with both rows queued, both ReviewDecision and DissentArtifact are rolled back (same session). Neither row persists. Endpoint returns 500.
- **DB inspect:** `SELECT dissent_id, linked_review_id, resolution_state FROM dissent_artifacts;`

## Deviations

None. Plan followed exactly. Log field `scope_len` (vs no scope logging) is a deliberate observability choice consistent with the S04 redaction constraint — not a deviation.

## Known Issues

None.

## Files Created/Modified

- `src/sps/api/routes/reviews.py` — DissentArtifact import; dissent INSERT block after `db.add(row)`; `dissent_artifact_id` field on `ReviewDecisionResponse`; `_row_to_response` updated; `reviewer_api.dissent_artifact_created` log event
- `src/sps/api/routes/dissents.py` — new file: `DissentArtifactResponse` model, `_row_to_response` helper, `GET /{dissent_id}` endpoint
- `src/sps/api/main.py` — `dissents_router` imported and registered under `/api/v1/dissents`
