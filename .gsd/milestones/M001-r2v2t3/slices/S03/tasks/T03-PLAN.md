---
estimated_steps: 7
estimated_files: 2
---

# T03: Add purge workflow stub (dry-run) + tests

**Slice:** S03 — Retention + legal hold guardrails (INV-004) + purge denial tests
**Milestone:** M001-r2v2t3

## Description
Implement an operationally safe dry-run purge evaluator that lists purge-eligible evidence and proves held artifacts are never eligible.

## Steps
1. Define purge eligibility criteria for Phase 1 (retention_until + no legal hold).
2. Implement `dry_run_purge()` returning a report of eligible artifacts.
3. Ensure held artifacts never appear in the report.
4. Keep destructive purge disabled in Phase 1 (no object deletion).
5. Add tests for eligibility and hold exclusion.
6. Run legal-hold test suite.
7. Document intended future extension to real purge.

## Must-Haves
- [ ] `dry_run_purge()` exists and is deterministic.
- [ ] Tests prove held artifacts are never purge-eligible.

## Verification
- `./.venv/bin/pytest -q tests/s03_legal_hold_test.py`

## Inputs
- Legal hold guard + schema
- Evidence registry schema

## Expected Output
- `src/sps/retention/purge.py` — dry-run purge evaluator.
- `tests/s03_legal_hold_test.py` — coverage for purge eligibility + hold exclusion.
