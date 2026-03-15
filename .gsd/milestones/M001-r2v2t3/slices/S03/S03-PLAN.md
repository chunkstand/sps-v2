# S03: Retention + legal hold guardrails (INV-004) + purge denial tests

**Goal:** Enforce legal-hold retention controls so bound evidence cannot be destructively deleted or purged while held.
**Demo:** Place a legal hold on an EvidenceArtifact, attempt purge/delete, and observe the operation is denied with an explicit reason; releasing the hold allows purge eligibility.

## Must-Haves

- Legal hold data model and API surface for applying/removing holds.
- Storage guard that blocks destructive delete/purge operations when legal hold is active (INV-004).
- Negative tests proving purge/delete fails closed under hold.

## Proof Level

- This slice proves: integration
- Real runtime required: yes (Postgres; MinIO optional depending on whether purge is metadata-only or includes object deletion)
- Human/UAT required: no

## Verification

- `docker compose up -d`
- `./.venv/bin/pytest -q tests/s03_legal_hold_test.py`

## Observability / Diagnostics

- Runtime signals: invariant denial responses include `invariant_id=INV-004` and operation name
- Inspection surfaces: Postgres `legal_holds` table (or equivalent); API endpoints
- Failure visibility: denial reason includes artifact_id, hold_id, and whether the hold is case-scoped or artifact-scoped
- Redaction constraints: never expose sensitive evidence content

## Integration Closure

- Upstream surfaces consumed: evidence registry from S02; `invariants/sps/INV-004/invariant.yaml`; `runbooks/sps/legal-hold.md`
- New wiring introduced in this slice: retention/hold guard around destructive operations
- What remains before the milestone is truly usable end-to-end: nothing for Phase 1 (Phase 2 begins next)

## Tasks

- [x] **T01: Add legal-hold schema + domain model** `est:1h`
  - Why: Legal hold must be durable, queryable, and enforceable against purge operations.
  - Files: `src/sps/db/models.py`, `alembic/versions/*`, `src/sps/retention/models.py`
  - Do: Add tables for legal holds and hold bindings (artifact or case scope); include who/when/why fields; ensure hold lookup by artifact stable ID is efficient.
  - Verify: `./.venv/bin/alembic upgrade head`
  - Done when: migration applies and a test can insert/read a hold.

- [x] **T02: Implement storage guard enforcing INV-004** `est:1h`
  - Why: INV-004 is critical; destructive delete must fail closed under legal hold.
  - Files: `src/sps/retention/guard.py`, `src/sps/evidence/service.py`
  - Do: Implement `assert_not_on_legal_hold(artifact_id)` used by delete/purge paths; ensure denial includes invariant_id and a human-readable reason.
  - Verify: `./.venv/bin/pytest -q tests/s03_legal_hold_test.py -k deny`
  - Done when: destructive delete attempt is denied with invariant_id=INV-004.

- [x] **T03: Add purge workflow stub (dry-run) + tests** `est:1h`
  - Why: We need an operationally safe way to evaluate purge eligibility without risking data loss.
  - Files: `src/sps/retention/purge.py`, `tests/s03_legal_hold_test.py`
  - Do: Implement a `dry_run_purge()` that lists purge-eligible evidence (based on retention_until and no legal hold); ensure held artifacts never appear; (actual destructive purge can remain disabled until later).
  - Verify: `./.venv/bin/pytest -q tests/s03_legal_hold_test.py`
  - Done when: tests prove held artifacts are never purge-eligible.

## Files Likely Touched

- `src/sps/retention/*`
- `src/sps/db/models.py`
- `alembic/versions/*`
- `tests/s03_legal_hold_test.py`
