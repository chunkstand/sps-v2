---
id: S03
parent: M004-lp1flz
milestone: M004-lp1flz
provides:
  - End-to-end docker-compose runbook proving intake → RESEARCH_COMPLETE with fixture override artifacts
requires:
  - slice: S02
    provides: Jurisdiction + requirements fixtures and workflow activities
  - slice: S01
    provides: Intake contract, Project persistence, and INTAKE_COMPLETE workflow step
affects:
  - M005/S01
key_files:
  - scripts/verify_m004_s03.sh
key_decisions:
  - Delete fixture artifact rows by fixture IDs before reusing override to avoid idempotent conflicts.
patterns_established:
  - Runbook restarts the workflow after intake and cleans fixture IDs for repeatable runs.
observability_surfaces:
  - runbook stdout (postgres_summary + structured_log_hint + ledger snapshot on failure)
  - worker log file emitted by the runbook
  - case_transition_ledger/jurisdiction_resolutions/requirement_sets via assert_postgres
  - docker compose logs api
  - docker compose logs worker (only when worker is containerized)
drill_down_paths:
  - .gsd/milestones/M004-lp1flz/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M004-lp1flz/slices/S03/tasks/T02-SUMMARY.md
duration: 1h35m
verification_result: passed
completed_at: 2026-03-15
---

# S03: End-to-end docker-compose proof (API + worker + Postgres + Temporal)

**Docker-compose runbook now proves an intake-driven workflow reaches RESEARCH_COMPLETE with fixture-backed artifacts and API/DB evidence.**

## What Happened
- Hardened the S03 runbook to delete fixture artifact rows by stable fixture IDs before applying the fixture override.
- Kept the runbook’s intake → worker → workflow restart flow so the intake-created case advances through jurisdiction and requirements.
- Confirmed API read surfaces and Postgres evidence for jurisdiction/requirements artifacts under the runtime case_id.

## Verification
- `./.venv/bin/pytest tests/m004_s03_fixture_override_test.py`
- `bash scripts/verify_m004_s03.sh`

## Requirements Advanced
- None.

## Requirements Validated
- R010 — Operational runbook proves intake request persists Project/PermitCase and reaches INTAKE_COMPLETE under live services.
- R011 — Operational runbook proves jurisdiction resolution persists and advances to JURISDICTION_COMPLETE.
- R012 — Operational runbook proves requirements persistence and RESEARCH_COMPLETE advancement with provenance.

## New Requirements Surfaced
- None.

## Requirements Invalidated or Re-scoped
- None.

## Deviations
- None.

## Known Limitations
- Worker logs are emitted to the runbook log file rather than `docker compose logs worker` when running locally.

## Follow-ups
- None.

## Files Created/Modified
- `scripts/verify_m004_s03.sh` — delete fixture artifact rows by fixture IDs before applying overrides in the runbook.

## Forward Intelligence
### What the next slice should know
- The Phase 4 fixture IDs are stable across runs; runbooks must clear rows by fixture IDs to avoid idempotent inserts that skip runtime case_id persistence.

### What's fragile
- Fixture ID reuse — failing to clear by ID causes `JURISDICTION_REQUIRED_DENIED` despite successful fixture lookup.

### Authoritative diagnostics
- `.gsd/runbook/m004_s03_worker_*.log` — contains fixture_case_id logs and transition denials when the runbook fails.
- `case_transition_ledger` rows for the runtime case_id — definitive progression evidence.

### What assumptions changed
- Clearing by fixture case_id alone was insufficient; fixture ID collisions required explicit deletion by fixture IDs.
