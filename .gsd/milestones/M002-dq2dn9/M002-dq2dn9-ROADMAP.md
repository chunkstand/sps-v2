# M002-dq2dn9: Phase 2 — Temporal harness + guarded state transitions

**Vision:** A PermitCase progresses only via a Temporal workflow whose *only* authoritative mutation path is a Postgres-backed state-transition guard (fail-closed), producing deterministic denials with invariant/guard IDs and replay-safe, idempotent transition/audit ledger writes.

## Success Criteria

- Local `docker compose` Temporal + Postgres + a Python worker can run a minimal `PermitCaseWorkflow` end-to-end and the run is visible in Temporal UI.
- A workflow attempt to transition a case into a protected/submission-bearing state (canonical proof: `REVIEW_PENDING → APPROVED_FOR_SUBMISSION`) **without** a valid `ReviewDecision` is denied **fail-closed**, and the denial includes guard assertion / invariant identifiers and is persisted as an audit/ledger event.
- The same workflow progresses after receiving a valid `ReviewDecision` via Temporal signal (Phase 2 injection path) and the guarded transition succeeds, updating authoritative Postgres state.
- Replay/idempotency is proven: activity retry / workflow replay does not duplicate state-transition side effects (ledger is idempotent) and guard denials remain deterministic for the same DB snapshot.

## Key Risks / Unknowns

- Temporal determinism hazards (Python SDK sandbox, time/uuid usage, imports) can cause replay failures if workflow code does non-deterministic work.
- Activity retry + worker failure can duplicate DB writes unless a hard idempotency key is enforced at the DB boundary.
- Guard placement correctness: enforcing spec §9 + §20A guard assertions in the wrong layer (workflow) would either break determinism or allow fail-open behavior.

## Proof Strategy

- Temporal determinism hazards → retire in **S01** by running a real workflow that blocks on a signal (Temporal history shows the wait/signal/resume path) and by keeping all I/O in activities.
- Duplicate side effects under activity retry → retire in **S02** by enforcing `request_id`-keyed transition ledger inserts (duplicate PK returns the prior result) and proving it via an integration test.
- Guard correctness (protected transition denial/unblock) → retire in **S02** by proving `REVIEW_PENDING → APPROVED_FOR_SUBMISSION` is denied without `ReviewDecision`, then succeeds after signal-injected decision.
- Replay determinism + idempotency closure → retire in **S03** by replaying captured history and by proving ledger counts are stable under replays/retries.

## Verification Classes

- Contract verification:
  - Pydantic v2 models validate `model/sps/contracts/state-transition-request.schema.json` (and any new signal payload schemas) at the guard boundary.
  - Unit tests for guard decision outputs (denial payload shape, stable identifiers).
- Integration verification:
  - `docker compose` Temporal + Postgres; worker connects to Temporal and activities transact against Postgres.
  - Pytest integration tests start workflows via Temporal client and assert Postgres state/ledger outcomes.
- Operational verification:
  - Worker start/stop (SIGTERM) leaves workflows in a recoverable state (retries continue on restart).
  - Denials are observable via Temporal history *and* persisted ledger events.
- UAT / human verification:
  - Temporal UI shows workflow runs, signal events, and activity failures/denials for the canonical proof path.

## Milestone Definition of Done

This milestone is complete only when all are true:

- All slices below are complete.
- A real worker entrypoint exists and is exercised against the local Temporal cluster.
- Authoritative PermitCase state transitions occur only via the guarded activity (no direct specialist mutation path).
- Success criteria are re-checked against live behavior (real Temporal + real Postgres), not only mocked/unit artifacts.
- Final integrated acceptance scenarios pass:
  - Denied protected transition without ReviewDecision
  - Signal-driven ReviewDecision unblocks and transition succeeds
  - Replay/idempotency does not duplicate ledger side effects

## Requirement Coverage

- Covers: R004, R005
- Partially covers: none
- Leaves for later: none
- Orphan risks: none

## Slices

- [ ] **S01: Temporal worker + minimal PermitCaseWorkflow (signal wait) + operator CLI** `risk:high` `depends:[]`
  > After this: you can start a local worker, start a PermitCaseWorkflow via a CLI, and see it waiting for a ReviewDecision signal in Temporal UI (with minimal Postgres-backed case bootstrap performed via an activity).

- [ ] **S02: Postgres-backed guarded transitions (deny + audit) + signal-driven review unblock** `risk:high` `depends:[S01]`
  > After this: starting the workflow attempts `REVIEW_PENDING → APPROVED_FOR_SUBMISSION`; it is denied (fail-closed) without a ReviewDecision and persists a denial ledger event, then succeeds after sending a ReviewDecision signal (decision persisted) and updates authoritative case state.

- [ ] **S03: Replay/idempotency closure + final end-to-end integration proof** `risk:medium` `depends:[S02]`
  > After this: integration tests prove replays/retries do not duplicate transition ledger effects and guard denials are deterministic; a runbook-level “start stack → run canonical scenario” is exercised end-to-end against docker-compose Temporal+Postgres.

## Boundary Map

### S01 → S02

Produces:
- `sps.workflows.worker` entrypoint that runs the worker against local Temporal.
- `sps.workflows.permit_case.workflow.PermitCaseWorkflow` with a stable workflow input contract (case_id) and a signal contract for `ReviewDecision` injection.
- `sps.workflows.cli` (or equivalent) that can:
  - start the workflow (returning workflow_id/run_id)
  - send a ReviewDecision signal
- Minimal activities boundary with a Postgres session pattern suitable for authoritative writes.

Consumes:
- Postgres schema/models from Phase 1 (PermitCase, ReviewDecision, CaseTransitionLedger).

### S02 → S03

Produces:
- Guard boundary contract: `StateTransitionRequest` validation + `StateTransitionResult` (success or structured denial with identifiers).
- Authoritative activity: `apply_state_transition(request)` that:
  - enforces `from_state` matches DB state
  - enforces transition allow/deny
  - enforces guard assertions (from `invariants/sps/guard-assertions.yaml`) for protected transitions
  - writes idempotent ledger/audit rows keyed by `request_id`
  - updates `permit_cases.case_state` only on success
- Workflow behavior that routes denial to a stable, observable “blocked/waiting” path and can resume on signal.

Consumes:
- Worker/workflow/CLI harness from S01.
