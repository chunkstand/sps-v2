# M002-dq2dn9 / S03 — Replay/idempotency closure + final end-to-end integration proof — Research

**Date:** 2026-03-15

## Summary

This slice primarily supports **R004 (Active)** by turning the existing Temporal+Postgres proof path into an explicit **replay/determinism proof** using Temporal’s Python `Replayer`, and by strengthening the integration proof to cover **worker restarts / activity retries** without duplicating ledger side effects. It also supports **R005 (already validated)** by proving denial behavior remains stable/deterministic for the same DB snapshot and by ensuring denials don’t “multiply” under retries.

Key finding: the current repo already has almost everything needed for S03. The S02 integration test spins up a **real Temporal client + in-process Worker** against docker-compose Temporal, which means S03 can (a) fetch workflow history via `WorkflowHandle.fetch_history()` and (b) replay it locally via `temporalio.worker.Replayer` without introducing new infrastructure. The missing pieces are: (1) a replay test, (2) a restart/retry-focused integration test, and (3) a runbook-level “start stack → run canonical scenario” proof that’s reproducible.

Surprise: in the installed `temporalio==1.23.0`, `WorkflowHistory.from_json` requires a `workflow_id` parameter (`WorkflowHistory.from_json(workflow_id, json_str)`), and `WorkflowHandle.fetch_history()` / `WorkflowHistory.to_json()` exist and are the cleanest path to capturing a replayable history from tests.

## Recommendation

Extend the existing S02 Temporal+Postgres integration harness (the in-process Worker pattern) with two additional proofs:

1. **Replay determinism proof (offline):**
   - Run the canonical workflow to completion.
   - Fetch its history via `await handle.fetch_history()` and replay it with `Replayer(workflows=[PermitCaseWorkflow])`.
   - Fail the test if replay detects non-determinism.

2. **Retry/restart idempotency proof (online):**
   - Start the workflow and let it reach the “waiting for review” blocked state.
   - Stop worker A (simulating SIGTERM / worker crash) while the workflow is still running.
   - Start worker B and continue by sending the ReviewDecision signal.
   - Assert:
     - workflow completes successfully,
     - `case_transition_ledger` rows for the correlation_id are exactly the expected two (one denied + one applied), and
     - re-running key activities with the same `request_id` / `idempotency_key` remains stable.

If we also want a direct “activity retry executes the same activity twice” proof (not just restart replay), add a **test-only failpoint** to `apply_state_transition` / `persist_review_decision` (e.g., env-driven “fail once after commit for request_id=X”). Then configure a RetryPolicy for those activity calls in the workflow (or wrap a flaky activity in tests) and assert no duplicate ledger rows.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Workflow determinism verification | `temporalio.worker.Replayer` + `WorkflowHandle.fetch_history()` | Replayer is the intended SDK mechanism; it uses recorded event history and will raise on non-determinism. |
| Replay-safe idempotency at DB boundary | `case_transition_ledger.transition_id == StateTransitionRequest.request_id` (PK) | Activities can retry; DB uniqueness provides the hard “exactly once effect” guarantee. |
| Operator proof path | Existing `python -m sps.workflows.worker` + `python -m sps.workflows.cli` | Keeps the runbook simple and aligned with how we’ll run workers later. |

## Existing Code and Patterns

- `tests/m002_s02_temporal_guarded_transition_workflow_test.py` — Real Temporal+Postgres integration harness that runs a Worker in-process; best place to extend with history fetch/replay and worker restart tests.
- `src/sps/workflows/permit_case/workflow.py` — Deterministic workflow structure already present (no I/O in workflow code; deterministic request IDs from workflow_id/run_id/attempt).
- `src/sps/workflows/permit_case/activities.py` — Transaction-first authoritative activity pattern:
  1) read ledger by request_id, 2) enforce guard, 3) insert ledger row, 4) mutate case state only on success.
- `tests/m002_s02_transition_guard_db_idempotency_test.py` — DB-only idempotency proof; can be extended for “denial stability across different request_ids” (same DB snapshot).
- `src/sps/workflows/temporal.py` — Central client connection; keeps namespace/address/task-queue consistent across CLI/tests/worker.

## Constraints

- Temporal integration tests are opt-in: `SPS_RUN_TEMPORAL_INTEGRATION=1` is required.
- Current activities are synchronous SQLAlchemy (threadpool executor). This is good for S03: retries/replays should not require switching to async DB.
- Local dev Temporal state can outlive Postgres resets (Temporal uses the same Postgres volume). Tests should continue using unique workflow IDs (already true via ULID case IDs).
- Current workflow does not set explicit activity retry policy in `execute_activity`; to prove “real retry” we may need either:
  - a test-only failpoint + explicit RetryPolicy, or
  - a wrapper activity used only by the integration test worker.

## Common Pitfalls

- **Confusing “workflow replay” with “activity retry”** — Replayer proves determinism of workflow code; it does not exercise activity retry behavior. Use a failpoint + RetryPolicy (or worker restart) to prove idempotent side effects under real re-execution.
- **Non-deterministic workflow code sneaking in** — avoid `datetime.now()`, `uuid.uuid4()`, `random`, and other sandbox-restricted calls in workflow code; keep all I/O and non-determinism in activities.
- **History JSON handling drift** — in `temporalio==1.23.0`, `WorkflowHistory.from_json` requires `workflow_id` as the first arg; don’t copy older snippets verbatim.

## Open Risks

- If we implement an activity failpoint incorrectly (e.g., raising before commit), the test may not actually prove “idempotent after side effect”; it will only prove “no side effect happened.” Failpoints must trigger **after** the DB transaction commits.
- Worker restart tests can be flaky if the test doesn’t wait for the workflow to reach a stable “waiting” point before stopping the worker; we should wait on durable signals (ledger row existence + workflow status running).

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Temporal Python SDK (replay/testing) | `wshobson/agents@temporal-python-testing` | available (not installed) — `npx skills add wshobson/agents@temporal-python-testing` |
| SQLAlchemy + Alembic | `wispbit-ai/skills@sqlalchemy-alembic-expert-best-practices-code-review` | available (not installed) — `npx skills add wispbit-ai/skills@sqlalchemy-alembic-expert-best-practices-code-review` |
| Docker Compose orchestration | `manutej/luxor-claude-marketplace@docker-compose-orchestration` | available (not installed) — `npx skills add manutej/luxor-claude-marketplace@docker-compose-orchestration` |
| Pytest patterns/coverage | `github/awesome-copilot@pytest-coverage` | available (not installed) — `npx skills add github/awesome-copilot@pytest-coverage` |

## Sources

- Temporal Python SDK replay patterns (`Replayer`, `WorkflowHistory`) (source: https://context7.com/temporalio/sdk-python/llms.txt)
- Local repo integration harness and canonical proof path (source: `tests/m002_s02_temporal_guarded_transition_workflow_test.py`)
- Authoritative idempotency boundary (ledger PK = request_id) (source: `src/sps/workflows/permit_case/activities.py`)
