---
estimated_steps: 7
estimated_files: 3
---

# T02: Prove DB idempotency under real activity retry (post-commit failpoint)

**Slice:** S03 — Replay/idempotency closure + final end-to-end integration proof
**Milestone:** M002-dq2dn9

## Description

Replayer proves workflow-code determinism, but it does not prove that *re-executed activities* won’t duplicate DB writes. This task adds a test-only failpoint that raises *after commit* for a targeted request so Temporal retries the activity, and then asserts the authoritative Postgres effects are still exactly-once (ledger PK + review idempotency key do their job).

## Steps

1. Add `src/sps/failpoints.py` with a minimal “fail once” helper gated behind env (e.g., `SPS_ENABLE_TEST_FAILPOINTS=1`) and keyed by a string like `apply_state_transition.after_commit/<request_id>`.
2. Wire the failpoint into `apply_state_transition(...)` (and, if needed, `persist_review_decision(...)`) strictly **after** the DB transaction has committed.
3. Add `tests/m002_s03_temporal_activity_retry_idempotency_test.py` that:
   - configures env failpoint keys before spinning up the in-process worker,
   - runs the canonical workflow,
   - asserts the activity was attempted more than once (via Temporal history or test-visible signal), and
   - asserts Postgres row counts are unchanged (no duplicated ledger rows; no duplicated review decision rows).

## Must-Haves

- [ ] Failpoint is impossible to trigger in normal runtime (guarded behind explicit env) and fails **at most once** per process.
- [ ] Failpoint triggers only after commit (the test must prove “side effect happened, then activity failed, then retried”).
- [ ] The integration test proves no duplicate `case_transition_ledger` rows (per `correlation_id`) and no duplicate `review_decisions` rows (per `idempotency_key`).

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s03_temporal_activity_retry_idempotency_test.py`

## Observability Impact

- Signals added/changed: structured activity log line when failpoint triggers (include request_id + correlation tuple, but no secrets).
- How a future agent inspects this: Temporal UI activity attempt history + Postgres ledger query by `correlation_id`.
- Failure state exposed: explicit exception message identifying the failpoint key that fired.

## Inputs

- `src/sps/workflows/permit_case/activities.py` — authoritative side-effect boundary.
- `tests/m002_s02_temporal_guarded_transition_workflow_test.py` — worker/client wiring pattern.

## Expected Output

- `src/sps/failpoints.py` — reusable, test-only failpoint facility.
- `tests/m002_s03_temporal_activity_retry_idempotency_test.py` — proves idempotent DB effects under real activity retry.
