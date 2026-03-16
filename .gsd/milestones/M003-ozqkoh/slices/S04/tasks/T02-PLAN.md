---
estimated_steps: 5
estimated_files: 3
---

# T02: Inline dissent creation and read endpoint

**Slice:** S04 — Dissent artifacts
**Milestone:** M003-ozqkoh

## Description

Wire dissent artifact persistence into the existing `POST /api/v1/reviews/decisions` endpoint (same DB transaction as the `ReviewDecision` row), then expose `GET /api/v1/dissents/{dissent_id}` in a new router. Both changes follow established codebase patterns — no new auth, no Temporal I/O.

## Steps

1. In `src/sps/api/routes/reviews.py`, import `DissentArtifact` from `sps.db.models`. After `db.add(row)` (the `ReviewDecision` insert) and before `db.commit()`, add a block:
   ```python
   if row.dissent_flag:
       dissent_row = DissentArtifact(
           dissent_id=f"DISSENT-{row.decision_id}",
           linked_review_id=row.decision_id,
           case_id=row.case_id,
           scope=req.dissent_scope,          # non-null guaranteed by model_validator
           rationale=req.dissent_rationale,  # non-null guaranteed by model_validator
           required_followup=req.dissent_required_followup,
           resolution_state="OPEN",
           created_at=now,
       )
       db.add(dissent_row)
   ```
   Both rows are committed in the existing `db.commit()` call that follows — single transaction.

2. Add `dissent_artifact_id: str | None = None` to `ReviewDecisionResponse` so callers can discover the linked artifact ID without a separate query. Set it when building the response from a row that has `dissent_flag=True` (construct the ID from `f"DISSENT-{row.decision_id}"`).

3. Create `src/sps/api/routes/dissents.py`:
   - Import `require_reviewer_api_key` from `sps.api.routes.reviews`
   - Import `DissentArtifact` from `sps.db.models`
   - Define `DissentArtifactResponse(BaseModel)` with all columns as fields
   - Define `_row_to_response(row: DissentArtifact) -> DissentArtifactResponse` helper
   - Define sync `GET /dissents/{dissent_id}` endpoint: `db.get(DissentArtifact, dissent_id)` → 200 or 404; gated by `dependencies=[Depends(require_reviewer_api_key)]`
   - Use `router = APIRouter(tags=["dissents"])`

4. Register `dissents_router` in `src/sps/api/main.py` with `prefix="/api/v1"` and `include_router(dissents_router)`.

5. Smoke-test imports and app startup.

## Must-Haves

- [ ] Dissent artifact INSERT is inside the **same `session.begin()`** as the `ReviewDecision` INSERT — both committed atomically
- [ ] `GET /api/v1/dissents/{dissent_id}` returns 200 with full artifact fields when found, 404 when not found
- [ ] Endpoint is gated by `require_reviewer_api_key` (same dep as contradictions router)
- [ ] `ReviewDecisionResponse.dissent_artifact_id` is populated for ACCEPT_WITH_DISSENT decisions
- [ ] Existing unit tests remain green after changes

## Verification

- `python -c "from sps.api.main import app; print('ok')"` → `ok`
- `python -c "from sps.api.routes.dissents import router; print('ok')"` → `ok`
- `pytest tests/ -k "not (integration or temporal)" -x -q` → all pass
- Code review: `db.add(dissent_row)` appears before the `db.commit()` call in `create_review_decision`

## Observability Impact

- Signals added/changed: POST decision endpoint now logs `reviewer_api.dissent_artifact_created dissent_id=... linked_review_id=... case_id=...` after the combined commit when `dissent_flag=True`
- How a future agent inspects this: `GET /api/v1/dissents/{dissent_id}` — returns full artifact; `SELECT * FROM dissent_artifacts WHERE linked_review_id = '...';`
- Failure state exposed: if `db.commit()` fails with a dissent row queued, the ReviewDecision is also not persisted (same transaction) — the endpoint returns 500 and no partial state exists

## Inputs

- `src/sps/api/routes/reviews.py` — `create_review_decision` endpoint; `ReviewDecision` insert block; `_row_to_response` helper pattern
- `src/sps/api/routes/contradictions.py` — full reference for dissents router structure (sync endpoints, `require_reviewer_api_key` import, `_row_to_response` helper, `IntegrityError` → 409 pattern)
- `src/sps/api/main.py` — router registration pattern (existing `include_router` calls)
- T01 output: `DissentArtifact` model + extended `CreateReviewDecisionRequest` with dissent fields

## Expected Output

- `src/sps/api/routes/reviews.py` — dissent artifact INSERT block + `dissent_artifact_id` field in response
- `src/sps/api/routes/dissents.py` (new) — full router with `DissentArtifactResponse` model and GET endpoint
- `src/sps/api/main.py` — `dissents_router` registered under `/api/v1`
