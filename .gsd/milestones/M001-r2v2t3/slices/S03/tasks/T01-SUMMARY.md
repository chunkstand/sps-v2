---
id: T01
parent: S03
milestone: M001-r2v2t3
provides:
  - Legal-hold persistence tables (`legal_holds`, `legal_hold_bindings`) with FK + check constraint
  - Retention typed domain models for legal holds/bindings
  - Integration test proving holds can be inserted/read and bound to an EvidenceArtifact stable ID
key_files:
  - src/sps/db/models.py
  - alembic/versions/a06baa922883_legal_holds.py
  - src/sps/retention/models.py
  - tests/s03_legal_hold_test.py
key_decisions:
  - "Model hold bindings as an explicit table with a CHECK constraint enforcing exactly one target (artifact vs case)"
patterns_established:
  - "Legal hold lookups can key off `legal_hold_bindings.artifact_id` with an index"
observability_surfaces:
  - "./.venv/bin/pytest -q tests/s03_legal_hold_test.py"
duration: 50m
verification_result: passed
completed_at: 2026-03-15T22:20:00Z
blocker_discovered: false
---

# T01: Add legal-hold schema + domain model

**Added durable legal-hold tables + typed models, and proved holds can be bound to evidence artifacts in Postgres.**

## What Happened
- Read INV-004 and the legal-hold runbook and implemented the persistence substrate required to enforce “held evidence cannot be destructively deleted”.
- Added DB tables:
  - `legal_holds` — holds with who/why/when fields and ACTIVE/RELEASED status.
  - `legal_hold_bindings` — binds a hold to exactly one target (artifact OR case) enforced via a DB CHECK constraint.
- Added `src/sps/retention/models.py` with typed domain models (`LegalHold`, `LegalHoldBinding`).
- Added `tests/s03_legal_hold_test.py` proving a hold can be inserted and bound to an EvidenceArtifact stable ID.

## Verification
- `docker compose up -d postgres`
- `./.venv/bin/alembic upgrade head`
- `./.venv/bin/pytest -q tests/s03_legal_hold_test.py` → pass

## Diagnostics
- Primary: `pytest -q tests/s03_legal_hold_test.py`
- Schema state: `./.venv/bin/alembic current`

## Deviations
- None.

## Known Issues
- No API surface yet for applying/releasing holds; enforcement wiring happens in S03/T02.

## Files Created/Modified
- `src/sps/db/models.py` — added LegalHold + LegalHoldBinding models.
- `alembic/versions/a06baa922883_legal_holds.py` — migration.
- `src/sps/retention/models.py` — typed retention models.
- `tests/s03_legal_hold_test.py` — integration test.
