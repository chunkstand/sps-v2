# M002-dq2dn9 / S02 — Research

**Date:** 2026-03-15

## Summary

Slice **S02** primarily owns **R005** (guarded transitions + structured denials + audit persistence) and supports **R004** (by extending the minimal workflow from “wait for signal” to “attempt guarded transition → deny → wait → signal → succeed”). The canonical proof path in the roadmap/spec is **`REVIEW_PENDING → APPROVED_FOR_SUBMISSION`**: the workflow must attempt the transition without a `ReviewDecision` and be **denied fail-closed**, with a denial that includes the spec’s **guard assertion ID** (`INV-SPS-STATE-002`) and linked invariant(s) (`INV-001`), and that denial must be **persisted** as a ledger/audit event.

Key findings from the repo:
- Phase 1 already provides the durable tables we need (`permit_cases`, `review_decisions`, `case_transition_ledger`). However, **nothing currently writes to `case_transition_ledger`**, so S02 will define the first real “audit” semantics.
- The existing S01 bootstrap/workflow contracts are **not aligned** with canonical enums in the generated model contracts:
  - `ensure_permit_case_exists()` seeds `case_state="NEW"` (not in the contract enum; the spec state machine starts at `DRAFT`/`INTAKE_PENDING`, and the proof path requires `REVIEW_PENDING`).
  - Workflow signal uses `decision_outcome=APPROVE|DENY`, but the authoritative contract `ReviewDecision` uses `ACCEPT|ACCEPT_WITH_DISSENT|BLOCK`.
  - `submission_mode` / `portal_support_level` values seeded in DB don’t match the contract enums either.
  These mismatches will either force the guard to accept “invalid” states/outcomes (bad), or they must be corrected in S02 as part of making guarded transitions spec-consistent.

## Recommendation

Implement S02’s governance boundary as a **single authoritative activity** (sync SQLAlchemy in a Temporal activity threadpool) that takes a typed **`StateTransitionRequest`** (Pydantic v2 model aligned to `model/sps/contracts/state-transition-request.schema.json`) and returns a typed **`StateTransitionResult`** (new internal model) that is either:
- `applied` (and includes the resulting `case_state`), or
- `denied` (and includes `denial_event_type`, `guard_assertion_id`, `normalized_business_invariants[]`, plus a small stable `reason_code`).

The activity must be **idempotent at the DB boundary** using the decision already recorded in `.gsd/DECISIONS.md`:
- Use `StateTransitionRequest.request_id` as the `case_transition_ledger.transition_id` primary key.
- If a duplicate PK is detected, **return the previously persisted outcome** (replay/activity retry safe) and do not double-update `permit_cases`.

Workflow shape (deterministic):
1) Bootstrap case row (fix S01 seed values so the case is in a known, contract-valid state for the proof path).
2) Attempt `REVIEW_PENDING → APPROVED_FOR_SUBMISSION` via `apply_state_transition(...)`.
3) If denied with `APPROVAL_GATE_DENIED`, log and wait for signal.
4) On signal: persist a `ReviewDecision` (separate idempotent activity keyed by stable `idempotency_key`), then re-attempt the transition with `required_review_id` set.

For the canonical denial audit event, use the spec’s **Denial Audit Event** name from §20A:
- `APPROVAL_GATE_DENIED` (linked to guard assertion `INV-SPS-STATE-002`, invariant `INV-001`).

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Workflow determinism | Workflow/Activity split already used in S01 | Keep all DB I/O + guard logic in activities; workflows remain replay-safe and boring. |
| Idempotency under activity retry | `case_transition_ledger.transition_id` PK + Decision #9 | DB uniqueness is the simplest provable dedupe boundary; returning the prior stored result closes retry/replay duplication. |
| Guard assertion identifiers + linked invariants | `invariants/sps/guard-assertions.yaml` + `invariants/sps/index.yaml` + spec §20A matrix | Prevents “stringly-typed” one-off denial reasons; denials stay stable/auditable. |
| Typed trust-boundary payload | `model/sps/contracts/state-transition-request.schema.json` | Avoid ad-hoc dicts at the mutation boundary; makes denial tests stable. |

## Existing Code and Patterns

- `src/sps/workflows/permit_case/workflow.py` — deterministic workflow pattern (activities only; `wait_condition` for signals).
- `src/sps/workflows/permit_case/activities.py` — sync SQLAlchemy DB usage inside Temporal activity with correlation logging.
- `src/sps/workflows/worker.py` — worker registration pattern (ThreadPoolExecutor for sync activities).
- `src/sps/workflows/cli.py` — operator CLI wiring for start + signal.
- `src/sps/retention/guard.py` — precedent for **fail-closed** invariant denials with structured `to_dict()` diagnostics.
- `src/sps/db/models.py` — Phase 1 tables needed for S02:
  - `ReviewDecision` has `idempotency_key` unique constraint (good for signal-driven persistence idempotency).
  - `CaseTransitionLedger` has generic `payload` JSONB to store structured denial/applied results.
- `tests/m002_s01_temporal_permit_case_workflow_test.py` — in-process worker integration test harness against docker-compose Temporal/Postgres.

## Constraints

- The codebase is currently **sync SQLAlchemy**; introducing SQLAlchemy async for S02 would be high-risk. Keep DB work in sync activities executed in Temporal’s threadpool executor.
- `invariants/` and `model/` are **not included in the wheel build** (`pyproject.toml` packages only `src/sps`). If S02 loads YAML from `invariants/` at runtime, it will work in-repo but won’t work from a packaged wheel unless we:
  - include these artifacts as package data, or
  - copy the required subset under `src/sps/...`.
- Current workflow/DB seed values are not contract-valid (`case_state="NEW"`, `decision_outcome="APPROVE"`, etc.). The guard should not “accept garbage” to make tests pass; S02 likely needs to correct these to spec enums.
- Temporal workflows must not use `datetime.now()`/`uuid.uuid4()` directly; use deterministic sources (`workflow.now()`, stable derived IDs, or Temporal’s deterministic helpers) when constructing activity inputs.

## Common Pitfalls

- **Treating a governance denial as an exception** — raising in the activity risks retries and noisy Temporal histories; return a structured `denied` result and persist the audit event.
- **Generating a new `request_id` per attempt** — breaks idempotency; request IDs must be stable per transition attempt (derive from `workflow_id/run_id + transition_name`, store in workflow state).
- **Partial idempotency** — if the ledger write is deduped but the case_state update is not (or vice-versa), retries can still double-apply. Keep “ledger insert + state update” in one DB transaction keyed off the same `request_id`.

## Open Risks

- Full transition table scope creep: spec §9.2 is large. S02 should implement a minimal representation sufficient for the canonical path and fail-closed for unknown transitions.
- Outcome vocabulary drift: workflow signal and DB `ReviewDecision.decision_outcome` currently don’t match the generated schema. If not normalized in S02, later reviewers/adapters will inherit inconsistent semantics.
- Packaging/runtime artifact access: if we want the guard assertion registry to be “real” in deployed runtimes, we need a clear strategy for shipping `invariants/` (and possibly `model/`) alongside the code.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Temporal (Python) | `wshobson/agents@temporal-python-testing` | available (not installed) — `npx skills add wshobson/agents@temporal-python-testing` |
| SQLAlchemy + Alembic | `wispbit-ai/skills@sqlalchemy-alembic-expert-best-practices-code-review` | available (not installed) — `npx skills add wispbit-ai/skills@sqlalchemy-alembic-expert-best-practices-code-review` |
| Docker Compose | `manutej/luxor-claude-marketplace@docker-compose-orchestration` | available (not installed) — `npx skills add manutej/luxor-claude-marketplace@docker-compose-orchestration` |

## Sources

- Transition table row for `REVIEW_PENDING → APPROVED_FOR_SUBMISSION` and disallowed transitions (source: `specs/sps/build-approved/spec.md` §9.2–§9.3)
- Denial Audit Event name for reviewer gate (`APPROVAL_GATE_DENIED`) and linked guard assertion ID (`INV-SPS-STATE-002`) (source: `specs/sps/build-approved/spec.md` §20A)
- Guard assertion registry (`INV-SPS-STATE-002` → `INV-001`) (source: `invariants/sps/guard-assertions.yaml`, `invariants/sps/index.yaml`)
- Authoritative contract enums for `PermitCase.case_state` and `ReviewDecision.decision_outcome` (source: `model/sps/contracts/permit-case.schema.json`, `model/sps/contracts/review-decision.schema.json`)
- Guard boundary input contract shape (source: `model/sps/contracts/state-transition-request.schema.json`)
- Workflow/activity determinism guidance + workflow metadata (source: Temporal Python SDK docs via Context7: `/temporalio/sdk-python`)
