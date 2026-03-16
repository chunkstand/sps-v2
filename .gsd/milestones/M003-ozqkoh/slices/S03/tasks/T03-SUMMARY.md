---
id: T03
parent: S03
milestone: M003-ozqkoh
provides:
  - Full implementations of all three contradiction endpoints (create, resolve, get) in contradictions.py
  - ContradictionResponse schema with all 11 fields; _utcnow() and _row_to_response() helpers
key_files:
  - src/sps/api/routes/contradictions.py
key_decisions:
  - IntegrityError caught after commit (not before) to let Postgres enforce PK uniqueness; rollback called before re-raising as 409
  - All three endpoints use sync def + Session dep — no async needed (no Temporal I/O in contradiction paths)
patterns_established:
  - Same _utcnow() / _row_to_response() pattern as reviews.py; 409 body always includes error string + contradiction_id
observability_surfaces:
  - contradiction_api.create contradiction_id=... case_id=... blocking_effect=... — INFO on create
  - contradiction_api.resolve contradiction_id=... case_id=... — INFO on resolve
  - GET /api/v1/contradictions/{id} returns full ContradictionResponse including resolution_status, resolved_at, resolved_by
duration: ~10m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T03: Contradiction endpoint implementations

**Three full endpoint implementations replacing the 501 stubs in contradictions.py.**

## What Happened

Replaced all three 501 stub endpoints with working implementations following the reviews.py pattern exactly. Added `_utcnow()` and `_row_to_response()` helpers. 

- **POST /**: Instantiates `ContradictionArtifact` with `resolution_status="OPEN"`, `resolved_at=None`, `resolved_by=None`. Wraps commit in `try/except IntegrityError` → rollback + 409 `CONTRADICTION_ALREADY_EXISTS`. Returns 201 + full response on success.
- **POST /{contradiction_id}/resolve**: Loads by PK (404 if missing). Checks `resolution_status == "OPEN"` (409 `ALREADY_RESOLVED` if not). Sets `RESOLVED`, `resolved_at`, `resolved_by`; commits; returns 200.
- **GET /{contradiction_id}**: Loads by PK (404 if missing); returns 200 with full `ContradictionResponse`.

All endpoints use `db: Session = Depends(get_db)` (sync). Auth gate via `require_reviewer_api_key` inherited from router dependencies.

## Verification

- `python -c "from sps.api.routes.contradictions import create_contradiction, resolve_contradiction, get_contradiction; print('ok')"` → `ok`
- `.venv/bin/pytest tests/ -k "not (integration or temporal)" -x -q` → 9 passed, 7 skipped (no regressions)

## Diagnostics

After create: `SELECT contradiction_id, resolution_status, resolved_at, resolved_by FROM contradiction_artifacts WHERE contradiction_id = '...';` → row with `resolution_status='OPEN'`, nulls for resolved fields.

After resolve: same query shows `resolution_status='RESOLVED'`, `resolved_at` populated, `resolved_by` populated.

GET endpoint: `GET /api/v1/contradictions/{id}` returns full `ContradictionResponse` — usable without DB access to confirm artifact state.

409 body shapes:
- Duplicate create: `{"error": "CONTRADICTION_ALREADY_EXISTS", "contradiction_id": "..."}`
- Already resolved: `{"error": "ALREADY_RESOLVED", "contradiction_id": "...", "resolution_status": "RESOLVED"}`
- Not found: `{"error": "not_found", "contradiction_id": "..."}`

## Deviations

None — implementation followed the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `src/sps/api/routes/contradictions.py` — all three endpoints fully implemented; two structured log events; no 501 stubs remaining
