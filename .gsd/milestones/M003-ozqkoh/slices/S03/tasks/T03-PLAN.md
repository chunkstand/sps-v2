---
estimated_steps: 5
estimated_files: 1
---

# T03: Contradiction endpoint implementations

**Slice:** S03 — Contradiction artifacts + advancement blocking  
**Milestone:** M003-ozqkoh

## Description

Replaces the three 501 stubs in `contradictions.py` with full implementations. The pattern follows `reviews.py` exactly: sync `Session` dependency, `_utcnow()` helper, structured log events, `ConfigDict(extra="forbid")` on all models.

Three endpoints:
- **POST `/`** — create a `ContradictionArtifact` row with `resolution_status="OPEN"`; catch `IntegrityError` for duplicate PK and return 409.
- **POST `/{contradiction_id}/resolve`** — load by PK (404 if missing), check `resolution_status == "OPEN"` (409 `ALREADY_RESOLVED` if not), update to `RESOLVED` + `resolved_at` + `resolved_by`, commit, return 200.
- **GET `/{contradiction_id}`** — load by PK, return 200 or 404.

All gated by `require_reviewer_api_key` (already on router from T01).

## Steps

1. Add `_utcnow()` helper (identical to `reviews.py`) and a `_row_to_response(row: ContradictionArtifact) -> ContradictionResponse` helper that maps all model fields to the response model. `ContradictionResponse` should include all fields: `contradiction_id`, `case_id`, `scope`, `source_a`, `source_b`, `ranking_relation`, `blocking_effect`, `resolution_status`, `resolved_at`, `resolved_by`, `created_at`.
2. Implement `POST /` (`create_contradiction`): validate `CreateContradictionRequest`; instantiate `ContradictionArtifact` with `resolution_status="OPEN"`, `resolved_at=None`, `resolved_by=None`; `db.add(row); db.commit()`. Wrap in `try/except IntegrityError` to return 409 `{"error": "CONTRADICTION_ALREADY_EXISTS", "contradiction_id": req.contradiction_id}`. Return 201 with `_row_to_response(row)`. Log `contradiction_api.create contradiction_id=... case_id=... blocking_effect=...` at INFO.
3. Implement `POST /{contradiction_id}/resolve` (`resolve_contradiction`): load by PK (404 if None). If `row.resolution_status != "OPEN"`: raise 409 `{"error": "ALREADY_RESOLVED", "contradiction_id": contradiction_id, "resolution_status": row.resolution_status}`. Otherwise: set `row.resolution_status = "RESOLVED"`, `row.resolved_at = _utcnow()`, `row.resolved_by = req.resolved_by`; `db.commit()`. Log `contradiction_api.resolve contradiction_id=... case_id=...` at INFO. Return 200 with `_row_to_response(row)`.
4. Implement `GET /{contradiction_id}` (`get_contradiction`): load by PK; if None raise 404 `{"error": "not_found", "contradiction_id": contradiction_id}`; return `_row_to_response(row)`.
5. Ensure all endpoints use `db: Session = Depends(get_db)` — sync session, same as `reviews.py` (no `async def` needed; no Temporal I/O in contradiction endpoints).

## Must-Haves

- [ ] POST create returns 201 on new contradiction, 409 on duplicate `contradiction_id`.
- [ ] POST resolve returns 200 on `OPEN → RESOLVED`, 409 on already-resolved, 404 on unknown.
- [ ] GET returns 200 with full row data, 404 on unknown.
- [ ] Structured log events at INFO for create and resolve.
- [ ] `resolved_at` and `resolved_by` are `None` on created rows, populated on resolve.
- [ ] Non-integration tests still pass.

## Verification

- `python -c "from sps.api.routes.contradictions import create_contradiction, resolve_contradiction, get_contradiction; print('ok')"`
- `pytest tests/ -k "not (integration or temporal)" -x -q` → still passes

## Observability Impact

- Signals added/changed:
  - `contradiction_api.create contradiction_id=... case_id=... blocking_effect=...` — INFO on create
  - `contradiction_api.resolve contradiction_id=... case_id=...` — INFO on resolve
- How a future agent inspects this: `SELECT contradiction_id, resolution_status, resolved_at, resolved_by FROM contradiction_artifacts ORDER BY created_at DESC LIMIT 5;`
- Failure state exposed: 409 body contains `error` and `contradiction_id`; 404 body identifies the unknown ID

## Inputs

- `src/sps/api/routes/contradictions.py` (T01 output) — stub module to fill in
- `src/sps/api/routes/reviews.py` — canonical pattern for sync endpoint, `_utcnow()`, error shapes
- `src/sps/db/models.py` (T01 output) — `ContradictionArtifact` with `resolved_at`, `resolved_by`
- `src/sps/db/session.py` — `get_db` session dependency

## Expected Output

- `src/sps/api/routes/contradictions.py` — all three endpoints fully implemented; two structured log events; no 501 stubs remaining
