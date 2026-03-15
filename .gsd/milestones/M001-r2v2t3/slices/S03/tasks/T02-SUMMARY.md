---
id: T02
parent: S03
milestone: M001-r2v2t3
provides:
  - INV-004 runtime guard (`assert_not_on_legal_hold`) with invariant-denial error payload
  - Guarded destructive delete entrypoint (denies held evidence with invariant metadata)
  - Denial-focused test proving fail-closed behavior
key_files:
  - src/sps/retention/guard.py
  - src/sps/api/routes/evidence.py
  - tests/s03_legal_hold_test.py
key_decisions:
  - "Fail closed on any ACTIVE hold binding (artifact-scoped or case-scoped)"
patterns_established:
  - "InvariantDenied carries invariant_id + operation + artifact_id (+ optional hold_id) and serializes via to_dict()"
observability_surfaces:
  - "./.venv/bin/pytest -q tests/s03_legal_hold_test.py -k deny"
duration: 45m
verification_result: passed
completed_at: 2026-03-15T22:40:00Z
blocker_discovered: false
---

# T02: Implement storage guard enforcing INV-004

**Implemented the INV-004 legal-hold guard and proved destructive delete attempts are denied with invariant metadata.**

## What Happened
- Added `src/sps/retention/guard.py`:
  - `assert_not_on_legal_hold(db, artifact_id, operation)` checks for ACTIVE holds bound to the artifact and (if linked) its case.
  - `InvariantDenied` exception includes `invariant_id=INV-004`, `operation`, `artifact_id`, and optional `hold_id`.
- Wired the guard into a destructive delete entrypoint (`DELETE /api/v1/evidence/artifacts/{artifact_id}`):
  - If held → 423 with invariant denial payload.
  - If not held → 501 (deletion intentionally not enabled in Phase 1).
- Extended `tests/s03_legal_hold_test.py` with a deny-focused API test.

## Verification
- `docker compose up -d postgres`
- `./.venv/bin/pytest -q tests/s03_legal_hold_test.py -k deny` → pass

## Diagnostics
- Primary proof: `pytest -q tests/s03_legal_hold_test.py -k deny`

## Deviations
- Guard is wired directly in the FastAPI route layer (no separate evidence service layer yet) to keep Phase 1 minimal while still proving INV-004 fail-closed behavior.

## Known Issues
- No true destructive delete/purge is enabled in Phase 1; only the denial behavior is proven.

## Files Created/Modified
- `src/sps/retention/guard.py` — legal-hold guard + invariant denial error.
- `src/sps/api/routes/evidence.py` — guarded DELETE endpoint.
- `tests/s03_legal_hold_test.py` — deny-focused test.
