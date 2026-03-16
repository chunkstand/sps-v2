---
estimated_steps: 5
estimated_files: 5
---

# T01: API infrastructure — settings, models, key middleware, router skeleton

**Slice:** S01 — Reviewer API authority boundary
**Milestone:** M003-ozqkoh

## Description

Establishes all structural prerequisites before T02 implements behavior: the `SPS_REVIEWER_API_KEY` config field, Pydantic request/response models for the reviewer endpoint, a `require_reviewer_api_key` FastAPI dependency, the reviews router (stub), registration in main.py, and the `decision_id` field extension on `ReviewDecisionSignal`.

No business logic here — only contracts, configuration, and wiring.

## Steps

1. Add `reviewer_api_key: str` field to `sps.config.Settings` with env alias `SPS_REVIEWER_API_KEY` and a safe local default (`"dev-reviewer-key"`). The field must never be logged.
2. Create `src/sps/api/routes/reviews.py`: define `CreateReviewDecisionRequest` (Pydantic BaseModel with `decision_id`, `idempotency_key`, `case_id`, `reviewer_id`, `outcome` [ReviewDecisionOutcome enum], `notes`, `evidence_ids`); define `ReviewDecisionResponse` (Pydantic BaseModel with `decision_id`, `case_id`, `outcome`, `idempotency_key`, `created`); implement `require_reviewer_api_key` FastAPI dependency (reads `X-Reviewer-Api-Key` header, raises 401 if missing or mismatched); add stub `POST /decisions` endpoint that returns 501 (implementation in T02); add stub `GET /decisions/{decision_id}` endpoint that returns 501.
3. Register `reviews_router` in `src/sps/api/main.py` under prefix `/api/v1/reviews`.
4. Extend `ReviewDecisionSignal` in `src/sps/workflows/permit_case/contracts.py` with `decision_id: str | None = None` (optional/defaulted for backward compatibility — existing tests that build `ReviewDecisionSignal` without this field must still pass).
5. Smoke-test imports: `python -c "from sps.api.routes.reviews import router; from sps.config import get_settings; print(get_settings().reviewer_api_key)"`.

## Must-Haves

- [ ] `SPS_REVIEWER_API_KEY` in Settings; `get_settings().reviewer_api_key` returns a non-empty string
- [ ] `require_reviewer_api_key` dependency raises 401 for missing header and for wrong key
- [ ] `CreateReviewDecisionRequest` has all required fields with correct types; passes Pydantic v2 validation
- [ ] Reviews router registered in `sps.api.main` under `/api/v1/reviews`
- [ ] `ReviewDecisionSignal.decision_id` field is optional with `None` default; existing tests building `ReviewDecisionSignal` without it still pass
- [ ] No new Alembic migration needed (schema already has `review_decisions` table)

## Verification

- `python -c "from sps.api.main import app; print('ok')"` exits 0
- `python -c "from sps.api.routes.reviews import router, CreateReviewDecisionRequest, ReviewDecisionResponse; print('ok')"` exits 0
- `python -c "from sps.config import get_settings; s = get_settings(); assert s.reviewer_api_key; print(s.reviewer_api_key)"` exits 0 and prints the default key
- `python -c "from sps.workflows.permit_case.contracts import ReviewDecisionSignal; s = ReviewDecisionSignal(decision_outcome='ACCEPT', reviewer_id='r1'); assert s.decision_id is None; print('ok')"` exits 0
- Existing unit tests still pass: `pytest tests/ -k "not (integration or temporal)" -x`

## Observability Impact

- **New config field:** `reviewer_api_key` is readable via `get_settings().reviewer_api_key` — safe to assert in health checks; must NOT appear in logs (never log `settings` objects directly).
- **Auth failure surface:** `require_reviewer_api_key` raises `HTTPException(401)` with `{"error": "missing_api_key"}` or `{"error": "invalid_api_key"}` — these propagate as structured JSON responses visible in API logs and integration test assertions.
- **Stub endpoint visibility:** Both stub endpoints return `HTTPException(501)` with a `{"error": "not_implemented"}` body — a future agent or test that accidentally hits the stub gets a clear, actionable signal rather than a generic 500.
- **Import health check:** `python -c "from sps.api.main import app; print('ok')"` is the canonical bootstrap signal — if this fails, no endpoints are reachable.
- **Backward-compatible signal extension:** `ReviewDecisionSignal.decision_id` defaults to `None`; existing workflow replay logs that omit this field will deserialize without error, preserving Temporal determinism.

## Inputs

- `src/sps/config.py` — add `reviewer_api_key` field
- `src/sps/api/main.py` — register new router
- `src/sps/workflows/permit_case/contracts.py` — extend `ReviewDecisionSignal`

## Expected Output

- `src/sps/config.py` — extended with `SPS_REVIEWER_API_KEY`
- `src/sps/api/routes/reviews.py` (new) — request/response models, auth dependency, stub endpoints, router object
- `src/sps/api/main.py` — reviews router registered
- `src/sps/workflows/permit_case/contracts.py` — `ReviewDecisionSignal.decision_id` optional field added
