---
id: T03
parent: S03
milestone: M001-r2v2t3
provides:
  - Dry-run purge evaluator listing purge-eligible evidence artifacts
  - Tests proving held artifacts never appear purge-eligible
key_files:
  - src/sps/retention/purge.py
  - tests/s03_legal_hold_test.py
key_decisions:
  - "Phase 1 purge eligibility is conservative: expires_at <= as_of and no ACTIVE legal-hold binding"
patterns_established:
  - "Dry-run purge is a safe diagnostic surface; destructive purge remains disabled"
observability_surfaces:
  - "./.venv/bin/pytest -q tests/s03_legal_hold_test.py"
duration: 35m
verification_result: passed
completed_at: 2026-03-15T22:55:00Z
blocker_discovered: false
---

# T03: Add purge workflow stub (dry-run) + tests

**Implemented a safe dry-run purge evaluator and proved legal-hold artifacts are never purge-eligible.**

## What Happened
- Added `src/sps/retention/purge.py` with `dry_run_purge()`:
  - lists evidence artifacts with `expires_at <= as_of`
  - excludes any artifact bound by an ACTIVE legal hold (INV-004)
  - does not delete anything
- Extended `tests/s03_legal_hold_test.py` to prove:
  - an expired, unheld artifact is purge-eligible
  - an expired, held artifact is not purge-eligible

## Verification
- `./.venv/bin/pytest -q tests/s03_legal_hold_test.py` → pass

## Diagnostics
- Run: `pytest -q tests/s03_legal_hold_test.py`

## Deviations
- None.

## Known Issues
- Purge policy is minimal in Phase 1 (only `expires_at` + hold exclusion). Rich retention-class rules are deferred.

## Files Created/Modified
- `src/sps/retention/purge.py` — dry-run purge evaluator.
- `tests/s03_legal_hold_test.py` — purge eligibility + hold exclusion test.
