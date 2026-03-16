---
estimated_steps: 5
estimated_files: 3
---

# T01: Schema, model, and request extension

**Slice:** S04 — Dissent artifacts
**Milestone:** M003-ozqkoh

## Description

Establish the persistence layer for dissent artifacts: a new Alembic migration creates the `dissent_artifacts` table; a new `DissentArtifact` SQLAlchemy model maps to it; `CreateReviewDecisionRequest` gains optional `dissent_scope`, `dissent_rationale`, `dissent_required_followup` fields and a Pydantic `model_validator` that rejects `ACCEPT_WITH_DISSENT` requests missing `dissent_scope` or `dissent_rationale`. No endpoint logic yet — that lands in T02.

## Steps

1. Write `alembic/versions/d8e2a4c9b1f5_dissent_artifacts.py` with `down_revision='f3a1b9c2d7e4'`. Use `op.create_table('dissent_artifacts', ...)` with columns: `dissent_id` (Text, PK), `linked_review_id` (Text, not null), `case_id` (Text, not null), `scope` (Text, not null), `rationale` (Text, not null), `required_followup` (Text, nullable), `resolution_state` (Text, not null, server_default `'OPEN'`), `created_at` (DateTime(timezone=True), not null, server_default `sa.func.now()`). Add UNIQUE constraint on `linked_review_id`. Add index on `case_id`. Add FK `linked_review_id → review_decisions.decision_id` with `ondelete="RESTRICT"`. Add FK `case_id → permit_cases.case_id` with `ondelete="CASCADE"`.

2. Add `DissentArtifact` to `src/sps/db/models.py` following the `ContradictionArtifact` pattern: `Mapped[str]` columns with `mapped_column(sa.Text, ...)`. Fields: `dissent_id` (PK), `linked_review_id` (FK `review_decisions.decision_id`, `ondelete="RESTRICT"`, unique=True), `case_id` (FK `permit_cases.case_id`, `ondelete="CASCADE"`, index=True), `scope`, `rationale`, `required_followup` (nullable), `resolution_state`, `created_at`.

3. In `src/sps/api/routes/reviews.py`, add three optional fields to `CreateReviewDecisionRequest`: `dissent_scope: str | None = None`, `dissent_rationale: str | None = None`, `dissent_required_followup: str | None = None`.

4. Add a `model_validator(mode='after')` to `CreateReviewDecisionRequest` that raises `ValueError("dissent_scope and dissent_rationale are required when outcome is ACCEPT_WITH_DISSENT")` if `self.outcome == ReviewDecisionOutcome.ACCEPT_WITH_DISSENT` and (`self.dissent_scope is None or self.dissent_rationale is None`). Import `model_validator` from `pydantic`.

5. Verify imports and Pydantic validation work as expected.

## Must-Haves

- [ ] Migration file `d8e2a4c9b1f5_dissent_artifacts.py` exists and `alembic upgrade --sql` output includes `CREATE TABLE dissent_artifacts`
- [ ] `DissentArtifact` model importable from `sps.db.models`
- [ ] `CreateReviewDecisionRequest(outcome='ACCEPT_WITH_DISSENT', ...)` without dissent fields raises `ValidationError`
- [ ] `CreateReviewDecisionRequest(outcome='ACCEPT', ...)` without dissent fields passes validation (dissent fields are optional for non-dissent outcomes)
- [ ] `down_revision='f3a1b9c2d7e4'` set correctly to chain migrations

## Verification

- `python -c "from sps.db.models import DissentArtifact; print('ok')"` → `ok`
- `python -c "from sps.api.routes.reviews import CreateReviewDecisionRequest, ReviewDecisionOutcome; import pydantic; r = pydantic.validate_call(lambda x: x)(CreateReviewDecisionRequest)" ` — use direct instantiation to test validator
- `python -c "from sps.api.routes.reviews import CreateReviewDecisionRequest; from pydantic import ValidationError; [...]"` — construct ACCEPT_WITH_DISSENT without dissent fields → ValidationError; with fields → passes
- `./.venv/bin/alembic upgrade --sql | grep -i dissent_artifacts"` → shows CREATE TABLE DDL
- `pytest tests/ -k "not (integration or temporal)" -x -q` → still passes (no regressions)

## Inputs

- `src/sps/db/models.py` — `ContradictionArtifact` (lines ~108–128) is the structural reference for column types, FK style, and `__table_args__`
- `alembic/versions/f3a1b9c2d7e4_contradiction_artifacts_resolved_fields.py` — `down_revision` chaining pattern; migration file style
- `src/sps/api/routes/reviews.py` — `CreateReviewDecisionRequest` current shape; `ReviewDecisionOutcome` enum location

## Observability Impact

**What changes for a future agent inspecting this task:**

- `DissentArtifact` is now importable from `sps.db.models` — `python -c "from sps.db.models import DissentArtifact; print('ok')"` confirms the model is live.
- `alembic upgrade --sql` produces `CREATE TABLE dissent_artifacts` DDL — inspectable without a live DB.
- `CreateReviewDecisionRequest` with `outcome=ACCEPT_WITH_DISSENT` missing `dissent_scope` or `dissent_rationale` raises `pydantic.ValidationError` with paths `['dissent_scope']` / `['dissent_rationale']` — visible in HTTP 422 response detail array.
- Failure state: if import fails, it's a missing `__table_args__` or SA column type issue. If validator doesn't fire, check that `model_validator` import comes from `pydantic` (not `pydantic.v1`).
- No new log lines in this task — observability signals (`reviewer_api.dissent_artifact_created`) are wired in T02 when the INSERT logic is added.

## Expected Output

- `alembic/versions/d8e2a4c9b1f5_dissent_artifacts.py` — new migration creating `dissent_artifacts` table
- `src/sps/db/models.py` — `DissentArtifact` class added
- `src/sps/api/routes/reviews.py` — three new optional fields + `model_validator` on `CreateReviewDecisionRequest`
