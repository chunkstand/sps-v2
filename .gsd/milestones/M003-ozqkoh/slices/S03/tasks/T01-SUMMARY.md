---
id: T01
parent: S03
milestone: M003-ozqkoh
provides:
  - Alembic migration adding resolved_at and resolved_by to contradiction_artifacts
  - ContradictionArtifact ORM model with two new nullable Mapped fields
  - contradictions.py router with three stub endpoints (POST /, POST /{id}/resolve, GET /{id}), all returning 501, gated by require_reviewer_api_key
  - Router registered in main.py under /api/v1/contradictions
key_files:
  - alembic/versions/f3a1b9c2d7e4_contradiction_artifacts_resolved_fields.py
  - src/sps/db/models.py
  - src/sps/api/routes/contradictions.py
  - src/sps/api/main.py
key_decisions:
  - Migration revision ID hand-authored as f3a1b9c2d7e4 with down_revision=a06baa922883 (latest prior migration)
  - Stub endpoints log warning at WARNING level with structured key=value format so they are findable before T03 lands
  - require_reviewer_api_key imported directly from sps.api.routes.reviews — no re-export needed
patterns_established:
  - Stub endpoints return JSONResponse(501) with error/hint payload rather than raising HTTPException, consistent with the 501 contract
observability_surfaces:
  - Stub calls emit contradiction_api.create.stub / contradiction_api.resolve.stub / contradiction_api.get.stub at WARNING level with contradiction_id and case_id — findable via grep in logs before T03 lands
  - alembic current + alembic history confirm migration applied when DB is available
  - "\d contradiction_artifacts" in psql confirms resolved_at and resolved_by columns post-migration
duration: 15m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Migration, model update, and contradiction router stub

**Laid schema and API skeleton for S03 — migration, ORM update, and three stub endpoints registered.**

## What Happened

Hand-authored Alembic migration `f3a1b9c2d7e4_contradiction_artifacts_resolved_fields.py` chaining off `a06baa922883` (legal_holds). `upgrade()` adds two nullable columns; `downgrade()` drops them. `ContradictionArtifact` ORM model gained `resolved_at: Mapped[dt.datetime | None]` and `resolved_by: Mapped[str | None]` after `resolution_status`. New `contradictions.py` router defines `CreateContradictionRequest`, `ResolveContradictionRequest`, and `ContradictionResponse` Pydantic models (all `extra="forbid"`), then registers three stub endpoints all returning 501 JSON. All three take `dependencies=[Depends(require_reviewer_api_key)]` imported from `sps.api.routes.reviews`. Router registered in `main.py` under prefix `/api/v1/contradictions`.

Pre-flight fix: S03-PLAN.md lacked a failure-path diagnostic check in the Verification section — added a concrete SQL + HTTP inspection step covering the `CONTRADICTION_ADVANCE_DENIED` ledger row and `GET /api/v1/contradictions/{id}` as the inspectable denial surface.

## Verification

- `python -c "from sps.db.models import ContradictionArtifact; a = ContradictionArtifact(); assert hasattr(a, 'resolved_at') and hasattr(a, 'resolved_by'); print('ok')"` → `ok`
- `python -c "from sps.api.routes.contradictions import router; print([r.path for r in router.routes])"` → `['/', '/{contradiction_id}/resolve', '/{contradiction_id}']`
- `python -c "from sps.api.main import app; paths = [r.path for r in app.routes]; assert any('/contradictions' in p for p in paths), paths; print('ok')"` → `ok`
- `python -c "from sps.api.main import app; print('ok')"` → `ok`
- `pytest tests/ -k "not (integration or temporal)" -x -q` → 9 passed, 7 skipped
- Alembic chain verified: `f3a1b9c2d7e4 → a06baa922883 → c1fc8c772c8d → 02b39bad0a95`

## Diagnostics

Before T03 lands, any call to contradiction endpoints emits a structured WARNING log line, e.g.:
```
contradiction_api.create.stub contradiction_id=<id> case_id=<id>
```
After migration runs against Postgres: `alembic current` shows `f3a1b9c2d7e4`; `\d contradiction_artifacts` shows `resolved_at timestamptz` and `resolved_by text` columns. After T03, `GET /api/v1/contradictions/{id}` returns the full `ContradictionResponse` row for denial inspection.

## Deviations

none

## Known Issues

none

## Files Created/Modified

- `alembic/versions/f3a1b9c2d7e4_contradiction_artifacts_resolved_fields.py` — new migration: adds resolved_at and resolved_by to contradiction_artifacts
- `src/sps/db/models.py` — ContradictionArtifact: added resolved_at and resolved_by Mapped fields
- `src/sps/api/routes/contradictions.py` — new router with Pydantic models and three stub endpoints (501)
- `src/sps/api/main.py` — registered contradictions_router under /api/v1/contradictions
- `.gsd/milestones/M003-ozqkoh/slices/S03/S03-PLAN.md` — pre-flight fix: added failure-path diagnostic check to Verification section
