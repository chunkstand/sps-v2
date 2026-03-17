---
id: T01
parent: S01
milestone: M012-v8s3qn
provides:
  - EmergencyRecord ORM model with time-bounded fields and FK to permit_cases
  - OverrideArtifact ORM model with time-bounded fields and FK to permit_cases
  - Alembic migration creating emergency_records and override_artifacts tables with FK constraints and composite indexes
key_files:
  - src/sps/db/models.py
  - alembic/versions/37a1384857bd_emergency_override_artifacts.py
key_decisions:
  - Used composite indexes on (case_id, expires_at) for both tables to optimize queries filtering by case and time validity
  - Set allowed_bypasses and forbidden_bypasses as nullable JSONB in EmergencyRecord to permit optional configuration
  - Set affected_surfaces as non-nullable JSONB in OverrideArtifact since override scope is always required
patterns_established:
  - Emergency/override artifact ORM models follow Phase 11 artifact pattern (ContradictionArtifact, DissentArtifact) with FK constraints and scope fields
observability_surfaces:
  - docker compose exec postgres psql -U sps -d sps -c '\d emergency_records' — inspect schema and FK constraints
  - docker compose exec postgres psql -U sps -d sps -c '\d override_artifacts' — inspect schema and JSONB columns
  - docker compose exec postgres psql -U sps -d sps -c "SELECT * FROM emergency_records WHERE expires_at > NOW()" — query active emergencies
  - docker compose exec postgres psql -U sps -d sps -c "SELECT * FROM override_artifacts WHERE expires_at > NOW()" — query active overrides
duration: 35min
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: EmergencyRecord and OverrideArtifact ORM models + migration

**Added EmergencyRecord and OverrideArtifact ORM models with time-bounded fields, FK constraints to permit_cases, and Alembic migration creating both tables with composite indexes for query performance.**

## What Happened

1. **Added EmergencyRecord ORM model** to `src/sps/db/models.py` following Phase 11 artifact pattern (ContradictionArtifact, DissentArtifact as templates). Model includes:
   - emergency_id (str PK)
   - incident_id, case_id (FK to permit_cases), scope, declared_by (all str)
   - started_at, expires_at (DateTime with timezone)
   - allowed_bypasses, forbidden_bypasses (nullable JSONB for optional configuration)
   - cleanup_due_at (nullable DateTime)
   - created_at (DateTime with server_default=now())
   - Composite index on (case_id, expires_at) for time-bounded queries

2. **Added OverrideArtifact ORM model** to `src/sps/db/models.py` with:
   - override_id (str PK)
   - case_id (FK to permit_cases), scope, justification, approver_id (all str)
   - start_at, expires_at (DateTime with timezone)
   - affected_surfaces (non-nullable JSONB array)
   - cleanup_required (Boolean)
   - created_at (DateTime with server_default=now())
   - Composite index on (case_id, expires_at) for time-bounded queries

3. **Generated Alembic migration** via `.venv/bin/alembic revision --autogenerate -m "emergency_override_artifacts"`. Migration ID: `37a1384857bd`. Alembic correctly detected:
   - Both tables with all columns
   - FK constraints on case_id → permit_cases.case_id with ondelete='RESTRICT'
   - Composite indexes ix_emergency_records_case_expires and ix_override_artifacts_case_expires
   - JSONB column types for allowed_bypasses, forbidden_bypasses, affected_surfaces

4. **Applied migration** via `alembic upgrade head` — migration ran cleanly (exit 0)

5. **Verified schema** via psql `\d` commands:
   - emergency_records table: FK constraint emergency_records_case_id_fkey REFERENCES permit_cases(case_id) ON DELETE RESTRICT
   - override_artifacts table: FK constraint override_artifacts_case_id_fkey REFERENCES permit_cases(case_id) ON DELETE RESTRICT
   - Both tables have composite indexes on (case_id, expires_at)
   - JSONB columns verified: allowed_bypasses, forbidden_bypasses (nullable), affected_surfaces (not null)

## Verification

All verification checks passed:
- ✅ `alembic upgrade head` exits 0
- ✅ `docker compose exec postgres psql -U sps -d sps -c '\d emergency_records'` shows FK constraint on case_id (emergency_records_case_id_fkey FOREIGN KEY (case_id) REFERENCES permit_cases(case_id) ON DELETE RESTRICT)
- ✅ `docker compose exec postgres psql -U sps -d sps -c '\d override_artifacts'` shows FK constraint on case_id (override_artifacts_case_id_fkey) and affected_surfaces column type jsonb
- ✅ Composite indexes ix_emergency_records_case_expires and ix_override_artifacts_case_expires verified in \d output

## Diagnostics

**Schema inspection:**
- `docker compose exec postgres psql -U sps -d sps -c '\d emergency_records'` — shows columns, indexes, FK constraints
- `docker compose exec postgres psql -U sps -d sps -c '\d override_artifacts'` — shows columns, indexes, FK constraints, JSONB types

**Query active/expired artifacts:**
- `docker compose exec postgres psql -U sps -d sps -c "SELECT emergency_id, case_id, expires_at, expires_at > NOW() as active FROM emergency_records ORDER BY created_at DESC LIMIT 5"` — inspect emergency expiry state
- `docker compose exec postgres psql -U sps -d sps -c "SELECT override_id, case_id, expires_at, expires_at > NOW() as active FROM override_artifacts ORDER BY created_at DESC LIMIT 5"` — inspect override expiry state

**Migration history:**
- `alembic history` — verify emergency_override_artifacts (37a1384857bd) in revision chain

**Failure states:**
- Migration failure: `alembic upgrade head` exits non-zero with stack trace
- Missing FK constraints: `\d emergency_records` lacks FOREIGN KEY line
- Wrong column types: `\d override_artifacts` shows affected_surfaces as text instead of jsonb

## Deviations

None. Task plan was followed exactly.

## Known Issues

None. All must-haves met, verification passed.

## Files Created/Modified

- `src/sps/db/models.py` — Added EmergencyRecord and OverrideArtifact ORM classes with FK constraints and composite indexes
- `alembic/versions/37a1384857bd_emergency_override_artifacts.py` — Migration creating emergency_records and override_artifacts tables with FK constraints on case_id and indexes on (case_id, expires_at)
