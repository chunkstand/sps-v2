---
id: T01
parent: S01
milestone: M003-ozqkoh
provides:
  - SPS_REVIEWER_API_KEY config field with dev-reviewer-key default
  - CreateReviewDecisionRequest and ReviewDecisionResponse Pydantic models
  - require_reviewer_api_key FastAPI dependency (401 on missing/wrong key)
  - reviews router with stub POST /decisions and GET /decisions/{decision_id} (501)
  - reviews router registered in sps.api.main under /api/v1/reviews
  - ReviewDecisionSignal.decision_id optional field (None default, backward-compatible)
key_files:
  - src/sps/config.py
  - src/sps/api/routes/reviews.py
  - src/sps/api/main.py
  - src/sps/workflows/permit_case/contracts.py
key_decisions:
  - reviewer_api_key placed as the last field in Settings with a comment forbidding logging; follows existing pattern of sensitive fields (db_password, s3_secret_key)
  - decision_id appended as last field in ReviewDecisionSignal so all required fields stay before defaulted ones; this preserves Pydantic v2 ordering contract
  - Stub endpoints raise HTTPException(501) rather than returning a placeholder body, giving T02 a clear "not yet wired" signal distinct from a 500
  - require_reviewer_api_key reads via Header(alias="X-Reviewer-Api-Key") to match the canonical header casing from the slice spec
patterns_established:
  - ReviewDecisionOutcome enum imported directly into reviews.py from contracts.py — avoids re-defining it in the API layer
  - Auth dependency injected via dependencies=[Depends(...)] on the router decorator, not in the function signature, keeping stub body minimal
observability_surfaces:
  - "python -c 'from sps.api.main import app; print(ok)' — canonical import health check"
  - "401 responses on /api/v1/reviews/* with {error: missing_api_key} or {error: invalid_api_key} body — visible in API access logs"
  - "501 responses on stub endpoints with {error: not_implemented} body — unambiguous signal for T02"
  - "get_settings().reviewer_api_key — safe to assert in health checks; must not appear in log output"
duration: 25m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: API infrastructure — settings, models, key middleware, router skeleton

**All structural prerequisites for T02 wired and verified: config field, Pydantic models, auth dependency, stub router, and backward-compatible signal extension.**

## What Happened

Pre-flight fixes applied first: S01-PLAN.md lacked failure-path verification steps (added auth 401 check, signal-failure log inspection, and Postgres row persistence check); T01-PLAN.md was missing an `## Observability Impact` section (added, covering key redaction, auth failure surface, stub 501 shape, and backward-compatible signal extension).

Implementation followed the plan exactly:

1. `sps.config.Settings` extended with `reviewer_api_key: str` aliased to `SPS_REVIEWER_API_KEY`, default `"dev-reviewer-key"`. Field placed last with an explicit redaction warning in the comment.

2. `src/sps/api/routes/reviews.py` created with:
   - `CreateReviewDecisionRequest` (decision_id, idempotency_key, case_id, reviewer_id, outcome, notes, evidence_ids)
   - `ReviewDecisionResponse` (decision_id, case_id, outcome, idempotency_key, created)
   - `require_reviewer_api_key` dependency — reads `X-Reviewer-Api-Key` header, raises 401 with `{error: missing_api_key}` or `{error: invalid_api_key}`; key never echoed
   - Stub `POST /decisions` (501) and `GET /decisions/{decision_id}` (501), both gated by the dependency

3. `sps.api.main` updated — `reviews_router` registered under `/api/v1/reviews`.

4. `ReviewDecisionSignal.decision_id: str | None = None` appended with backward-compatibility note. `extra="forbid"` is preserved; existing callers that omit `decision_id` still validate cleanly.

## Verification

All four import/smoke checks passed:
```
.venv/bin/python -c "from sps.api.main import app; print('ok')"                                          → ok
.venv/bin/python -c "from sps.api.routes.reviews import router, CreateReviewDecisionRequest, ReviewDecisionResponse; print('ok')"  → ok
.venv/bin/python -c "from sps.config import get_settings; s = get_settings(); assert s.reviewer_api_key; print(s.reviewer_api_key)"  → dev-reviewer-key
.venv/bin/python -c "from sps.workflows.permit_case.contracts import ReviewDecisionSignal; s = ReviewDecisionSignal(decision_outcome='ACCEPT', reviewer_id='r1'); assert s.decision_id is None; print('ok')"  → ok
```

Unit test suite: `pytest tests/ -k "not (integration or temporal)" -x -q` → **9 passed, 5 skipped**

Slice-level verification (T01 partial — stubs in place, full behavior in T02/T03):
- `tests/m003_s01_reviewer_api_boundary_test.py` — not yet created (T03 work)
- `bash scripts/verify_m003_s01.sh` — not yet created (T03 work)
- Auth failure path (401) — middleware wired, will be confirmed end-to-end in T02/T03

## Diagnostics

- **Config:** `get_settings().reviewer_api_key` returns the configured key; never log `settings` objects.
- **Auth failures:** 401 responses on `POST /api/v1/reviews/decisions` are the observable signal for auth misconfiguration.
- **Stub signals:** 501 on either reviews endpoint means T02 hasn't run — unambiguous from logs.
- **Signal extension:** `ReviewDecisionSignal` deserialization with `decision_id` absent → `None` (no replay hazard).

## Deviations

None — implementation matched the plan exactly.

## Known Issues

None.

## Files Created/Modified

- `src/sps/config.py` — added `reviewer_api_key` field with `SPS_REVIEWER_API_KEY` alias and redaction warning
- `src/sps/api/routes/reviews.py` (new) — Pydantic models, auth dependency, stub endpoints, router object
- `src/sps/api/main.py` — registered reviews_router under `/api/v1/reviews`
- `src/sps/workflows/permit_case/contracts.py` — added `decision_id: str | None = None` to `ReviewDecisionSignal`
- `.gsd/milestones/M003-ozqkoh/slices/S01/S01-PLAN.md` — pre-flight: added failure-path verification steps
- `.gsd/milestones/M003-ozqkoh/slices/S01/tasks/T01-PLAN.md` — pre-flight: added `## Observability Impact` section
