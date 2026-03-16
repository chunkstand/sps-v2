---
id: T01
parent: S04
milestone: M003-ozqkoh
provides:
  - dissent_artifacts Alembic migration (d8e2a4c9b1f5)
  - DissentArtifact SQLAlchemy model
  - CreateReviewDecisionRequest Pydantic validator for ACCEPT_WITH_DISSENT
key_files:
  - alembic/versions/d8e2a4c9b1f5_dissent_artifacts.py
  - src/sps/db/models.py
  - src/sps/api/routes/reviews.py
key_decisions:
  - Used op.create_foreign_key inline within op.create_table (sa.ForeignKeyConstraint) consistent with how alembic --sql renders DDL; named constraints explicitly to aid future rollback diagnosis
  - model_validator(mode='after') on CreateReviewDecisionRequest — fires after all field coercions, so outcome is already a ReviewDecisionOutcome enum when the check runs
  - server_default for resolution_state uses sa.text("'OPEN'") (SQL literal) consistent with LegalHold.status pattern in models.py
patterns_established:
  - Pydantic cross-field validator on CreateReviewDecisionRequest using model_validator(mode='after')
  - DissentArtifact FK style: ondelete="RESTRICT" for linked_review_id (protect audit trail), ondelete="CASCADE" for case_id (delete dissents when case deleted)
observability_surfaces:
  - "python -c 'from sps.db.models import DissentArtifact; print(\"ok\")'" → confirms model importable
  - alembic upgrade f3a1b9c2d7e4:d8e2a4c9b1f5 --sql | grep dissent → shows CREATE TABLE DDL
  - ValidationError on ACCEPT_WITH_DISSENT missing dissent_scope/dissent_rationale → HTTP 422 with Pydantic error detail paths
  - No new runtime log lines in this task (wired in T02)
duration: ~15m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Schema, model, and request extension

**Dissent persistence layer established: migration, model, and Pydantic validator all wired and verified.**

## What Happened

Wrote the Alembic migration `d8e2a4c9b1f5_dissent_artifacts.py` chaining from `f3a1b9c2d7e4`. The migration uses `op.create_table` with inline `sa.ForeignKeyConstraint` entries (named explicitly) for both FK relationships: `linked_review_id → review_decisions.decision_id` with `RESTRICT` and `case_id → permit_cases.case_id` with `CASCADE`. An explicit index on `case_id` is created separately via `op.create_index`.

Added `DissentArtifact` to `src/sps/db/models.py` immediately after `ContradictionArtifact`, following the same column style (`Mapped[str]`, `mapped_column(sa.Text, ...)`). The `resolution_state` server_default uses `sa.text("'OPEN'")` (SQL literal string) consistent with `LegalHold.status`.

Extended `CreateReviewDecisionRequest` with three optional fields (`dissent_scope`, `dissent_rationale`, `dissent_required_followup`) and a `model_validator(mode='after')` that raises `ValueError` when `outcome == ACCEPT_WITH_DISSENT` and either `dissent_scope` or `dissent_rationale` is None. The `model_validator` import was added to the existing `pydantic` import line.

## Verification

- `python -c "from sps.db.models import DissentArtifact; print('ok')"` → `ok`
- `alembic upgrade f3a1b9c2d7e4:d8e2a4c9b1f5 --sql | grep -i dissent` → `CREATE TABLE dissent_artifacts` present with all columns, constraints, and index
- Manual Python validation test: ACCEPT_WITH_DISSENT without dissent fields → `ValidationError` (path `()`); ACCEPT_WITH_DISSENT with dissent fields → passes; ACCEPT without dissent fields → passes
- `pytest tests/ -k "not (integration or temporal)" -x -q` → 9 passed, 8 skipped (no regressions)

## Diagnostics

- **Model import check:** `python -c "from sps.db.models import DissentArtifact; print('ok')"`
- **Migration DDL check:** `cd <project> && .venv/bin/alembic upgrade f3a1b9c2d7e4:d8e2a4c9b1f5 --sql | grep -i dissent`
- **Validator failure shape:** `ValidationError` with `loc=()` (model-level validator, not field-level) and message `dissent_scope and dissent_rationale are required when outcome is ACCEPT_WITH_DISSENT`. FastAPI surfaces this as HTTP 422.
- **Partial slices:** T02 will add `reviewer_api.dissent_artifact_created` log event; no DB writes happen from this task alone.

## Deviations

None. Plan followed exactly.

## Known Issues

None.

## Files Created/Modified

- `alembic/versions/d8e2a4c9b1f5_dissent_artifacts.py` — new migration creating `dissent_artifacts` table with all columns, constraints, and index
- `src/sps/db/models.py` — `DissentArtifact` class added after `ContradictionArtifact`
- `src/sps/api/routes/reviews.py` — three new optional fields + `model_validator` on `CreateReviewDecisionRequest`; `model_validator` added to pydantic imports
