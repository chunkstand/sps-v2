---
estimated_steps: 4
estimated_files: 3
---

# T01: Add portal support governance schema + contracts

**Slice:** S01 — Admin intent/review/apply for portal support metadata
**Milestone:** M013-n6p1tg

## Description
Introduce authoritative storage for portal support metadata plus admin-specific intent/review artifacts, and define the request/response contracts used by the admin API.

## Steps
1. Extend `src/sps/db/models.py` with ORM models for `portal_support_metadata`, `admin_portal_support_intents`, and `admin_portal_support_reviews` (include status enums, JSONB payloads, and FK links as needed).
2. Add an Alembic migration that creates the new tables with indexes on intent_id, review_id/idempotency_key, and portal_family.
3. Create `src/sps/api/contracts/admin_portal_support.py` with Pydantic models for intent creation, review decision, and apply response payloads.
4. Ensure models and contracts import cleanly from existing modules (no circular imports).

## Must-Haves
- [ ] Portal support metadata and admin intent/review tables exist in ORM + migration with required indexes.
- [ ] Admin portal support API contracts exist with strict (extra="forbid") validation.

## Observability Impact
- Signals added: authoritative rows in `portal_support_metadata`, `admin_portal_support_intents`, and `admin_portal_support_reviews` with status enums and JSON payloads.
- Inspection approach: verify rows + index presence via Postgres catalog, and use ORM imports to surface schema wiring.
- Failure visibility: migration failure or missing index shows up in `alembic upgrade head` output; import errors flag circular dependency regressions.

## Verification
- `alembic upgrade head`
- `python -c "from sps.db import models; from sps.api.contracts import admin_portal_support"`

## Inputs
- `src/sps/db/models.py` — existing ORM patterns and JSONB usage for authoritative tables.
- `.gsd/DECISIONS.md` — admin governance model decision (admin-specific artifacts).

## Expected Output
- `src/sps/db/models.py` — new ORM models for admin portal support governance.
- `alembic/versions/*_admin_portal_support_governance.py` — migration creating new tables.
- `src/sps/api/contracts/admin_portal_support.py` — request/response schema for admin endpoints.
