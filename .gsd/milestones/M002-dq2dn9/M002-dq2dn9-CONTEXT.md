# M002-dq2dn9: Phase 2 — Temporal harness + guarded state transitions — Context

**Gathered:** 2026-03-15
**Status:** Queued — pending auto-mode execution.

## Project Description

Implement SPS v2.0.1 Phase 2 runtime harness per `specs/sps/build-approved/runtime-implementation-profile.md`:

- Temporal is the authoritative workflow engine for progression.
- Python workers implement workflows/activities.
- Authoritative business state is persisted in Postgres.
- All authoritative PermitCase state changes are mediated by an explicit **state transition guard**.

This milestone focuses on making the system *governable*: no direct specialist mutation, fail-closed guarded transitions, replay-safe side effects, and safe-stop routing.

## Why This Milestone

Phase 1 provides durable storage + evidence. Phase 2 is where SPS becomes a governed workflow system rather than a set of CRUD services.

Without the Temporal harness + guard, later work (reviewer gates, submission adapters, contradiction handling, release controls) can’t be proven to be authority-safe.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Start a local Temporal cluster + worker and run a minimal PermitCaseWorkflow end-to-end (with stubbed activities).
- Observe that any attempt to advance a case into a protected/submission-bearing state without required review/evidence is denied by the state transition guard.
- Inject a ReviewDecision into a waiting workflow via Temporal signals (until the reviewer service exists in Phase 3).
- Prove replay/idempotency: replays do not duplicate side effects and guard denials are deterministic.

### Entry point / environment

- Entry point: a Python Temporal worker (`sps.workflows.worker` or equivalent) + integration tests that start workflows via Temporal client.
- Environment: local dev via `docker compose` (Temporal + Postgres; MinIO optional for Phase 2 tests).
- Live dependencies involved: Temporal, Postgres.

## Completion Class

- Contract complete means: typed workflow inputs/outputs and transition requests validate; guard checks are deterministic and emit structured denials.
- Integration complete means: real Temporal + Postgres run, workflows persist state transitions, and signal-driven review unblocks guarded progression.
- Operational complete means: basic diagnostics exist (denial reasons include guard assertion / invariant identifiers; correlation IDs present).

## Final Integrated Acceptance

To call this milestone complete, we must prove:

1. **Guarded transition enforcement**
   - A workflow attempt to advance into `APPROVED_FOR_SUBMISSION` (or any protected state) without an appropriate ReviewDecision is denied.
2. **Signal-driven review unblock**
   - The same workflow progresses after receiving a valid ReviewDecision via Temporal signal.
3. **Replay/idempotency**
   - Workflow replay does not duplicate side effects (e.g., transition ledger entries are idempotent) and guard behavior is deterministic.

## Risks and Unknowns

- Temporal replay hazards: side effects and DB writes must be structured to avoid non-determinism.
- Guard placement correctness: must align with `invariants/sps/guard-assertions.yaml` and spec section 20A.
- State model completeness: transition table (spec section 9.2) is large; we will implement full table representation but prove a minimal end-to-end path first.

## Existing Codebase / Prior Art

- `specs/sps/build-approved/runtime-implementation-profile.md` — normative runtime binding.
- `specs/sps/build-approved/spec.md` — state model (section 9), retry rules (section 13), guard placement matrix (section 20A).
- `invariants/sps/index.yaml` and `invariants/sps/guard-assertions.yaml` — required invariant assertions and guard statements.
- M001 outputs (Phase 1): Postgres schema/migrations + evidence registry scaffolding (dependency).

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R001–R003 (Phase 1 foundations) must be complete before M002 is meaningful.
- R004 — Temporal harness exists and runs PermitCaseWorkflow.
- R005 — Guarded transitions + denial diagnostics/audit events exist.

## Scope

### In Scope

- Temporal workflow + worker wiring for PermitCaseWorkflow (minimal end-to-end flow with stubbed activities).
- State transition request contract validation at the guard boundary.
- State transition guard enforcing:
  - transition table preconditions (spec section 9)
  - guard assertions (invariants guard-assertions)
  - invariant checks INV-001..INV-008 where applicable (initially proven on a subset)
- Replay-safe side-effect pattern + idempotency keys for transition writes.
- Safe-stop routing paths for unsupported / blocked / contradictory cases (at least one proven path).

### Out of Scope / Non-Goals

- Full domain specialist implementations (research, compliance, document generation) — stubs only.
- Reviewer UI/service and independence checks (Phase 3).
- Submission adapters and external status normalization (Phase 5).

## Technical Constraints

- Temporal must remain the authoritative execution harness.
- No specialist worker may advance PermitCase state directly.
- Guard failures must fail closed and produce actionable denial diagnostics.
- Signal-driven ReviewDecision injection is allowed for Phase 2 tests only; the authoritative reviewer service remains Phase 3.

## Integration Points

- Temporal cluster (docker-compose)
- Postgres (authoritative store)
- Evidence registry surfaces from M001 (read-only usage in guard checks)

## Open Questions

- Which protected transition(s) should be used as the canonical Phase 2 “proof path” (recommend: `REVIEW_PENDING -> APPROVED_FOR_SUBMISSION` denial + approval).
- Exact mechanism for denial audit events (DB table vs structured log sink) while keeping Phase 6 observability requirements in view.
