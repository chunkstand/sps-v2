---
estimated_steps: 6
estimated_files: 2
---

# T01: EmergencyRecord and OverrideArtifact ORM models + migration

**Slice:** S01 — Emergency/override artifacts + guard enforcement + lifecycle proof
**Milestone:** M012-v8s3qn

## Description

Add ORM models for EmergencyRecord and OverrideArtifact with time-bounded fields and FK constraints to permit_cases, and generate Alembic migration creating both tables. These models establish authoritative persistence for emergency declarations and override artifacts required for GOV-005 enforcement.

## Steps

1. Add EmergencyRecord ORM model to src/sps/db/models.py with fields: emergency_id (str PK), incident_id (str), case_id (str FK to permit_cases), scope (str), declared_by (str), started_at (DateTime), expires_at (DateTime), allowed_bypasses (JSONB), forbidden_bypasses (JSONB), cleanup_due_at (DateTime nullable)
2. Add OverrideArtifact ORM model to src/sps/db/models.py with fields: override_id (str PK), case_id (str FK to permit_cases), scope (str), justification (str), start_at (DateTime), expires_at (DateTime), affected_surfaces (JSONB), approver_id (str), cleanup_required (Boolean)
3. Generate Alembic migration: `alembic revision --autogenerate -m "emergency_override_artifacts"`
4. Review migration to ensure FK constraints on case_id and indexes on (case_id, expires_at) for query performance
5. Apply migration: `alembic upgrade head`
6. Verify table creation and FK constraints via docker compose exec postgres psql -U sps -d sps -c '\d emergency_records' and '\d override_artifacts'

## Must-Haves

- [ ] EmergencyRecord model with all required fields and FK to permit_cases
- [ ] OverrideArtifact model with all required fields and FK to permit_cases
- [ ] Alembic migration creating both tables with FK constraints and indexes
- [ ] Migration applied cleanly (alembic upgrade head exits 0)
- [ ] FK constraints verified via psql \d output

## Verification

- `alembic upgrade head` exits 0
- `docker compose exec postgres psql -U sps -d sps -c '\d emergency_records'` shows FK constraint on case_id
- `docker compose exec postgres psql -U sps -d sps -c '\d override_artifacts'` shows FK constraint on case_id and affected_surfaces column type jsonb

## Observability Impact

**What signals change:**
- Database schema now includes emergency_records and override_artifacts tables visible via `\dt` and `\d <table_name>`
- Migration history in alembic_version table updated with emergency_override_artifacts revision
- FK constraints on emergency_records.case_id and override_artifacts.case_id enforce referential integrity (visible in `\d` output as FOREIGN KEY constraints)

**How a future agent inspects this task:**
- `docker compose exec postgres psql -U sps -d sps -c '\dt emergency_records'` — verify table exists
- `docker compose exec postgres psql -U sps -d sps -c '\d emergency_records'` — inspect schema, FK constraints, indexes
- `docker compose exec postgres psql -U sps -d sps -c '\d override_artifacts'` — inspect schema, FK constraints, JSONB columns
- `alembic history` — verify migration in revision chain
- `grep -A20 'class EmergencyRecord' src/sps/db/models.py` — verify ORM model definition

**What failure state becomes visible:**
- Migration failure: `alembic upgrade head` exits non-zero with stack trace in stdout
- Missing FK constraints: `\d emergency_records` output lacks "FOREIGN KEY (case_id) REFERENCES permit_cases"
- Wrong column types: `\d override_artifacts` shows affected_surfaces as text instead of jsonb
- Missing indexes: `\d emergency_records` lacks index on (case_id, expires_at) for query performance

## Inputs

- Existing permit_cases table (FK target)
- Phase 11 artifact persistence pattern (ContradictionArtifact, DissentArtifact) as ORM model template
- Spec emergency/override contracts (specs/sps/build-approved/spec.md GOV-005)

## Expected Output

- `src/sps/db/models.py` — EmergencyRecord and OverrideArtifact ORM classes
- `alembic/versions/*_emergency_override_artifacts.py` — migration creating emergency_records and override_artifacts tables with FK constraints
