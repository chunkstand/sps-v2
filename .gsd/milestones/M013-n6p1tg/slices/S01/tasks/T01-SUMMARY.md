---
id: T01
parent: S01
milestone: M013-n6p1tg
provides:
  - Portal support governance ORM schema, migration, and admin API contracts
key_files:
  - src/sps/db/models.py
  - alembic/versions/e3a9c4b7d2f1_admin_portal_support_governance.py
  - src/sps/api/contracts/admin_portal_support.py
  - tests/m013_s01_admin_portal_support_governance_test.py
key_decisions:
  - None
patterns_established:
  - Admin portal support governance tables with JSONB payloads and status fields
observability_surfaces:
  - Postgres tables: portal_support_metadata, admin_portal_support_intents, admin_portal_support_reviews
  - Alembic migration e3a9c4b7d2f1
  - Import check for contracts/models

duration: 1.3h
verification_result: failed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Add portal support governance schema + contracts

**Added admin portal support governance schema, migration, and contracts, plus a placeholder integration test file.**

## What Happened
- Extended `src/sps/db/models.py` with PortalSupportMetadata, AdminPortalSupportIntent, and AdminPortalSupportReview ORM models (JSONB payloads, status fields, FK link, indexes).
- Added Alembic migration `e3a9c4b7d2f1_admin_portal_support_governance.py` to create the new tables, constraints, and indexes.
- Created `src/sps/api/contracts/admin_portal_support.py` defining strict Pydantic request/response models for intent, review, and apply payloads.
- Added a placeholder integration test file per slice-level instruction (currently failing until T03 implements the tests).

## Verification
- `.venv/bin/alembic upgrade head` → **failed** (Postgres not reachable at localhost:5432).
- `.venv/bin/python -c "from sps.db import models; from sps.api.contracts import admin_portal_support"` → **passed**.

## Diagnostics
- Inspect tables: `portal_support_metadata`, `admin_portal_support_intents`, `admin_portal_support_reviews` after migrations.
- Migration: `alembic upgrade head` (requires running Postgres).
- Import check: `.venv/bin/python -c "from sps.db import models; from sps.api.contracts import admin_portal_support"`.

## Deviations
- Created `tests/m013_s01_admin_portal_support_governance_test.py` placeholder earlier than T03 per auto-mode instruction.

## Known Issues
- Alembic upgrade cannot run until Postgres is available on localhost:5432.
- Placeholder test intentionally fails until T03 implementation.

## Files Created/Modified
- `src/sps/db/models.py` — added portal support governance ORM models.
- `alembic/versions/e3a9c4b7d2f1_admin_portal_support_governance.py` — migration for new tables/indexes.
- `src/sps/api/contracts/admin_portal_support.py` — admin portal support request/response contracts.
- `tests/m013_s01_admin_portal_support_governance_test.py` — placeholder integration test stub.
- `.gsd/milestones/M013-n6p1tg/slices/S01/S01-PLAN.md` — marked T01 complete and added failure-path verification.
- `.gsd/milestones/M013-n6p1tg/slices/S01/tasks/T01-PLAN.md` — added Observability Impact section.
- `.gsd/STATE.md` — advanced next action to T02.
