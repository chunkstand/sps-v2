---
estimated_steps: 5
estimated_files: 4
---

# T01: Migration, model update, and contradiction router stub

**Slice:** S03 — Contradiction artifacts + advancement blocking  
**Milestone:** M003-ozqkoh

## Description

Lays the schema and API skeleton for S03. The `ContradictionArtifact` table is missing `resolved_at` and `resolved_by` columns — a new Alembic migration adds them (nullable, backward-compatible). The ORM model gains the two new `Mapped` fields. A new router module `contradictions.py` is created with stub endpoints (501) for POST create, POST resolve, and GET read, gated by `require_reviewer_api_key`. The router is registered in `main.py` under `/api/v1/contradictions`. Nothing here changes runtime behavior — it's pure scaffolding that subsequent tasks depend on.

## Steps

1. Generate or hand-author a new Alembic migration under `alembic/versions/` that runs `op.add_column('contradiction_artifacts', sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True))` and `op.add_column('contradiction_artifacts', sa.Column('resolved_by', sa.Text(), nullable=True))`. Provide a matching `downgrade()` that drops both columns. Name the migration descriptively (e.g. `contradiction_artifacts_resolved_fields`).
2. Update `ContradictionArtifact` in `src/sps/db/models.py` to add `resolved_at: Mapped[dt.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)` and `resolved_by: Mapped[str | None] = mapped_column(sa.Text, nullable=True)` after `resolution_status`.
3. Create `src/sps/api/routes/contradictions.py`. Define Pydantic models: `CreateContradictionRequest` (fields: `contradiction_id`, `case_id`, `scope`, `source_a`, `source_b`, `ranking_relation`, `blocking_effect: bool`; `ConfigDict(extra="forbid")`), `ResolveContradictionRequest` (fields: `resolved_by: str`; `ConfigDict(extra="forbid")`), `ContradictionResponse` (fields matching the full `ContradictionArtifact` row for read/create response). Create a `router = APIRouter(tags=["contradictions"])`. Add three stub endpoints all returning 501: `POST /` (`create_contradiction`), `POST /{contradiction_id}/resolve` (`resolve_contradiction`), `GET /{contradiction_id}` (`get_contradiction`). All three take `dependencies=[Depends(require_reviewer_api_key)]` imported from `sps.api.routes.reviews`. Import `require_reviewer_api_key` from `sps.api.routes.reviews` — it already exists and is not reviewer-specific by name.
4. In `src/sps/api/main.py`, import `contradictions_router` from `sps.api.routes.contradictions` and register with `app.include_router(contradictions_router, prefix="/api/v1/contradictions")`.
5. Verify import checks and that migration applies cleanly (dry-run with `alembic upgrade head --sql` or against real Postgres if available).

## Must-Haves

- [ ] New Alembic migration file exists with both `upgrade()` and `downgrade()` operations.
- [ ] `ContradictionArtifact` ORM model has `resolved_at` and `resolved_by` fields.
- [ ] `contradictions.py` router has all three endpoints (stub, 501), gated with `require_reviewer_api_key`.
- [ ] Router registered in `main.py` under `/api/v1/contradictions`.
- [ ] `python -c "from sps.api.main import app; print('ok')"` passes.

## Verification

- `python -c "from sps.db.models import ContradictionArtifact; a = ContradictionArtifact(); assert hasattr(a, 'resolved_at') and hasattr(a, 'resolved_by'); print('ok')"`
- `python -c "from sps.api.routes.contradictions import router; print([r.path for r in router.routes])"`
- `python -c "from sps.api.main import app; paths = [r.path for r in app.routes]; assert any('/contradictions' in p for p in paths), paths; print('ok')"`
- `pytest tests/ -k "not (integration or temporal)" -x -q` → still passes

## Observability Impact

- Signals added/changed: none yet (stubs return 501)
- How a future agent inspects this: `alembic current` and `alembic history` confirm migration applied; `\d contradiction_artifacts` in psql confirms columns
- Failure state exposed: 501 responses on all contradiction endpoints until T03

## Inputs

- `src/sps/db/models.py` — `ContradictionArtifact` model to extend (missing `resolved_at`, `resolved_by`)
- `src/sps/api/routes/reviews.py` — `require_reviewer_api_key` dependency to import
- `src/sps/api/main.py` — router registration point

## Expected Output

- `alembic/versions/<hash>_contradiction_artifacts_resolved_fields.py` — new migration
- `src/sps/db/models.py` — `ContradictionArtifact` updated with two new nullable fields
- `src/sps/api/routes/contradictions.py` — new router module with three stub endpoints
- `src/sps/api/main.py` — contradiction router registered
