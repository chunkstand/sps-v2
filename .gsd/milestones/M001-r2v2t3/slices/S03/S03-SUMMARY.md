---
id: S03
parent: M001-r2v2t3
milestone: M001-r2v2t3
provides:
  - Legal-hold persistence and bindings
  - INV-004 enforcement guard (fail-closed) for destructive evidence operations
  - Dry-run purge evaluator that never marks held artifacts eligible
requires:
  - slice: S02
    provides: Evidence registry + storage binding + stable IDs
affects: []
key_files:
  - src/sps/db/models.py
  - alembic/versions/a06baa922883_legal_holds.py
  - src/sps/retention/guard.py
  - src/sps/retention/purge.py
  - tests/s03_legal_hold_test.py
key_decisions:
  - "Deny destructive ops under hold with invariant metadata (invariant_id + operation + artifact_id + hold_id)"
patterns_established:
  - "Legal-hold bindings enforce exactly one target via DB CHECK constraint"
  - "InvariantDenied -> HTTP 423 with structured denial payload"
observability_surfaces:
  - "./.venv/bin/pytest -q tests/s03_legal_hold_test.py"
drill_down_paths:
  - .gsd/milestones/M001-r2v2t3/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001-r2v2t3/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M001-r2v2t3/slices/S03/tasks/T03-SUMMARY.md
duration: 2h
verification_result: passed
completed_at: 2026-03-15T23:10:00Z
---

# S03: Retention + legal hold guardrails (INV-004) + purge denial tests

**Shipped legal-hold guardrails for evidence (INV-004) and proved held evidence cannot be treated as purge/delete-eligible.**

## What Happened
- Added durable legal-hold persistence:
  - `legal_holds` table for hold records (who/why/when, ACTIVE/RELEASED)
  - `legal_hold_bindings` table binding holds to either an artifact or a case (exactly-one-target enforced by DB CHECK constraint)
- Implemented the INV-004 runtime guard (`assert_not_on_legal_hold`) that fails closed when any ACTIVE hold binds an artifact (or its linked case).
- Wired the guard into a destructive delete entrypoint for evidence artifacts; under hold it returns a structured invariant denial payload with `invariant_id=INV-004`.
- Implemented a conservative dry-run purge evaluator that lists purge-eligible artifacts (expired + not held) without deleting anything.

## Verification
- `docker compose up -d postgres`
- `./.venv/bin/alembic upgrade head`
- `./.venv/bin/pytest -q tests/s03_legal_hold_test.py` → pass

## Requirements Advanced
- R003 — Legal hold enforcement substrate exists and destructive operations are denied with invariant metadata.

## Requirements Validated
- R003 — Validated by `tests/s03_legal_hold_test.py` proving denial and purge exclusion under hold.

## New Requirements Surfaced
- (none)

## Requirements Invalidated or Re-scoped
- None.

## Deviations
- Destructive delete is intentionally not enabled in Phase 1 (returns 501 when not held). The slice proves the fail-closed denial semantics under hold.

## Known Limitations
- No API surface yet for applying/releasing holds; this slice establishes the persistence + enforcement primitives.

## Follow-ups
- None.

## Files Created/Modified
- `src/sps/db/models.py` — legal hold models.
- `src/sps/retention/guard.py` — INV-004 guard.
- `src/sps/retention/purge.py` — dry-run purge.
- `tests/s03_legal_hold_test.py` — integration tests.

## Forward Intelligence
### What the next slice should know
- Hold enforcement is defined by `legal_hold_bindings` + ACTIVE holds, not by the legacy boolean flags (`permit_cases.legal_hold`, `evidence_artifacts.legal_hold_flag`). If those booleans remain, treat them as derived caches.

### What's fragile
- Any future introduction of real destructive purge must ensure it checks INV-004 in exactly one central place (prefer guard) and emits consistent denial payloads.

### Authoritative diagnostics
- `pytest -q tests/s03_legal_hold_test.py` is the fastest proof of INV-004 behavior.

### What assumptions changed
- "We can do hold enforcement purely via a boolean flag" — we established explicit hold records + bindings so holds are durable, queryable, and auditable.
