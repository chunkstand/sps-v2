---
date: 2026-03-15
triggering_slice: M002-dq2dn9/S01
verdict: no-change
---

# Reassessment: M002-dq2dn9/S01

## Changes Made

No changes.

## Success-Criterion Coverage Check

- Local `docker compose` Temporal + Postgres + a Python worker can run a minimal `PermitCaseWorkflow` end-to-end and the run is visible in Temporal UI. → S02, S03
- A workflow attempt to transition a case into a protected/submission-bearing state (canonical proof: `REVIEW_PENDING → APPROVED_FOR_SUBMISSION`) **without** a valid `ReviewDecision` is denied **fail-closed**, and the denial includes guard assertion / invariant identifiers and is persisted as an audit/ledger event. → S02
- The same workflow progresses after receiving a valid `ReviewDecision` via Temporal signal (Phase 2 injection path) and the guarded transition succeeds, updating authoritative Postgres state. → S02
- Replay/idempotency is proven: activity retry / workflow replay does not duplicate state-transition side effects (ledger is idempotent) and guard denials remain deterministic for the same DB snapshot. → S03

## Requirement Coverage Impact

None.

- R004 remains in good shape: S01 proved the deterministic wait→signal→resume harness against real Temporal+Postgres; replay/idempotency closure remains appropriately owned by S03.
- R005 remains appropriately owned by S02 (primary) + S03 (supporting) and is still the right next risk to retire.

## Decision References

- #3 (Phase 2 proof strategy)
- #8 (guard placement: authoritative transitions enforced in a Postgres-backed activity)
- #9 (idempotency key for transition ledger)
- #10–12 (Temporal runtime config, workflow identity convention, sandbox import hygiene)
