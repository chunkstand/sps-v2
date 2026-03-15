---
estimated_steps: 9
estimated_files: 4
---

# T02: Implement SQLAlchemy models + Alembic migrations for Phase 1 entities

**Slice:** S01 — Postgres schema + migrations + typed model package
**Milestone:** M001-r2v2t3

## Description
Define the Phase 1 authoritative schema in SQLAlchemy and ship Alembic migrations that apply cleanly to a fresh Postgres database.

## Steps
1. Read the Phase 1 spec references (listed in M001 context) to confirm the entity set and required fields.
2. Create/extend SQLAlchemy `Base` and a canonical place for models (`src/sps/db/models.py`).
3. Model the Phase 1 tables (PermitCase, Project, review/decision records, contradictions, transition ledger, evidence metadata, release applicability / artifact metadata) with stable ID columns + indexes.
4. Add foreign keys + non-null constraints and any obvious uniqueness constraints required for stable IDs.
5. Add/confirm Alembic configuration (`alembic.ini`, `alembic/env.py`) aligned to the repo layout.
6. Generate a migration revision and hand-audit the DDL.
7. Apply migrations against local docker-compose Postgres on a fresh volume.
8. Ensure `alembic current` shows `head`.
9. Add minimal docs/comments to prevent later drift.

## Must-Haves
- [ ] `src/sps/db/models.py` defines substantive SQLAlchemy models (not stubs) for Phase 1 entities.
- [ ] `alembic/versions/*` migrations exist and are deterministic + reviewable.
- [ ] Migrations apply cleanly on a fresh Postgres instance (`alembic upgrade head`).

## Verification
- `docker compose up -d postgres`
- `./.venv/bin/alembic upgrade head`
- `./.venv/bin/alembic current`

## Inputs
- `specs/sps/build-approved/spec.md` — authoritative domain definitions.
- `specs/sps/build-approved/plan.md` — Phase 1 scope.
- `model/sps/model.yaml` — enums/naming expectations.

## Expected Output
- `src/sps/db/models.py` — SQLAlchemy models for Phase 1 tables.
- `alembic/` — environment + migration revision(s).
- `alembic.ini` — configured for this service.
- (If needed) `src/sps/db/session.py` — engine/session utilities used by Alembic.
