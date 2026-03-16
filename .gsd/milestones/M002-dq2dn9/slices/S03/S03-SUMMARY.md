---
id: S03
parent: M002-dq2dn9
milestone: M002-dq2dn9
provides:
  - Replay determinism + exactly-once DB side effects proofs for PermitCaseWorkflow (offline Replayer + real activity retries) and an operator runbook for end-to-end verification
requires:
  - slice: S02
    provides: Postgres-authoritative guarded transitions + signal-driven ReviewDecision persistence (deny → wait → signal → persist → apply)
affects:
  - M003 (Phase 3 reviewer service can rely on replay-safe, idempotent guarded transition substrate)
key_files:
  - tests/helpers/temporal_replay.py
  - tests/m002_s03_temporal_replay_determinism_test.py
  - src/sps/failpoints.py
  - src/sps/workflows/permit_case/activities.py
  - tests/m002_s03_temporal_activity_retry_idempotency_test.py
  - scripts/lib/assert_postgres.sh
  - scripts/verify_m002_s03_runbook.sh
key_decisions:
  - Construct `temporalio.worker.Replayer` with the same Pydantic-aware `data_converter` as the live Temporal client to avoid converter-mismatch replay failures.
  - Force real Temporal activity retries with env-gated, key-addressable post-commit failpoints (fail once per key) to prove exactly-once DB effects without production risk.
  - Run runbook Postgres assertions via `docker compose exec ... psql` inside the container to avoid host tooling requirements and avoid DSN/credential handling.
patterns_established:
  - Integration determinism harness: run workflow against docker-compose → fetch history → offline replay → assert durable Postgres outcomes.
  - Post-commit retry harness: commit authoritative write → raise test-only failpoint → observe Temporal retry → assert DB row counts remain stable.
  - Runbook verification script: idempotent stack bring-up + background worker + CLI orchestration + DB invariant assertions keyed by workflow correlation.
observability_surfaces:
  - Replayer exceptions pinpoint first diverging history event (test re-raises with workflow_id/run_id context).
  - Temporal history shows explicit failure messages `FAILPOINT_FIRED key=<...>` on retry attempts.
  - Worker structured logs include failpoint key + workflow_id/run_id + request_id/idempotency_key.
  - Runbook prints workflow_id/run_id/case_id and a minimal Postgres summary (ledger event counts + review decision row).
drill_down_paths:
  - .gsd/milestones/M002-dq2dn9/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M002-dq2dn9/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M002-dq2dn9/slices/S03/tasks/T03-SUMMARY.md
duration: 2h30m
verification_result: passed
completed_at: 2026-03-15
---

# S03: Replay/idempotency closure + final end-to-end integration proof

**Proved the Phase 2 PermitCaseWorkflow is replay-deterministic and that activity retries do not duplicate authoritative Postgres side effects, and added a one-command runbook to exercise the canonical scenario end-to-end.**

## What Happened

This slice closed the remaining Phase 2 risks around Temporal replay determinism and “exactly-once effect” semantics at the Postgres boundary:

- Added an **offline replay determinism integration test** that runs a real workflow to completion on docker-compose Temporal+Postgres, fetches the recorded history, and replays it with Temporal’s `Replayer` (failing on any non-determinism).
- Added **env-gated post-commit failpoints** in the authoritative activities and an integration test that forces real Temporal activity retries **after a committed DB write**, proving the ledger and review-decision writes remain exactly-once.
- Added an **operator-style runbook** script that brings up the local stack, starts the real worker, drives the canonical workflow via the CLI, and asserts the expected Postgres invariants by correlation id.

## Verification

Passed:

- `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s03_temporal_replay_determinism_test.py`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s03_temporal_activity_retry_idempotency_test.py`
- `bash scripts/verify_m002_s03_runbook.sh`

## Requirements Advanced

- R005 — Strengthened the existing guard proof by showing denial/apply outcomes remain stable under offline replay and real activity retries (no duplicated ledger/review side effects).

## Requirements Validated

- R004 — Now proved (not just mapped): offline history replay succeeds deterministically and post-commit activity retries do not duplicate Postgres side effects; runbook demonstrates the canonical scenario end-to-end on the real stack.

## New Requirements Surfaced

- None.

## Requirements Invalidated or Re-scoped

- None.

## Deviations

- Runbook uses the current CLI interface (`start` / `signal-review`) rather than older planned subcommand names.
- Made `tests/` importable (`tests/__init__.py`) to support shared replay helpers.

## Known Limitations

- None discovered in the S03 proof surface.

## Follow-ups

- None.

## Files Created/Modified

- `tests/helpers/temporal_replay.py` — offline replay helper around `temporalio.worker.Replayer`.
- `tests/m002_s03_temporal_replay_determinism_test.py` — run workflow → fetch history → offline replay → assert Postgres outcomes.
- `src/sps/failpoints.py` — env-gated, key-addressable “fail once” failpoints with test-visible counters.
- `src/sps/workflows/permit_case/activities.py` — post-commit failpoint hooks + structured logs.
- `tests/m002_s03_temporal_activity_retry_idempotency_test.py` — forces real retries and asserts exactly-once DB effects.
- `scripts/lib/assert_postgres.sh` — docker-compose Postgres assertion helpers.
- `scripts/verify_m002_s03_runbook.sh` — stack → worker → CLI → DB asserts runbook.

## Forward Intelligence

### What the next slice should know

- Offline replay is sensitive to **data converter wiring**; use the same Pydantic-aware converter in tests/replayer as in the live Temporal client.
- The idempotency proof that matters is **post-commit failure + retry**; the failpoint keys (`apply_state_transition.after_commit/<request_id>`, `persist_review_decision.after_commit/<idempotency_key>`) are the stable hooks.

### What's fragile

- If deterministic ID conventions change (`correlation_id`, `request_id`, `idempotency_key`), update the replay and idempotency tests + runbook in lockstep; they intentionally key their DB assertions off those IDs.

### Authoritative diagnostics

- `bash scripts/verify_m002_s03_runbook.sh` — fastest end-to-end signal (worker+CLI+DB invariants).
- Temporal UI + history failures containing `FAILPOINT_FIRED key=...` — confirms retries were forced on the intended boundary.

### What assumptions changed

- “S01 proves replay safety” → actual replay safety needed an explicit offline history replay proof + a post-commit retry proof; both are now in place.
