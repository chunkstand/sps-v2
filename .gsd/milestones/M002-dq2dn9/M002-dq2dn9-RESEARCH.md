# M002-dq2dn9 — Research

**Date:** 2026-03-15

## Summary

Phase 2 should prove a single, canonical governed progression path end-to-end with **real Temporal + real Postgres**: start a `PermitCaseWorkflow`, attempt a protected transition (`REVIEW_PENDING → APPROVED_FOR_SUBMISSION`) **without** a `ReviewDecision` and observe a fail-closed denial with guard/assertion IDs, then inject a `ReviewDecision` via a Temporal signal and observe the same transition succeed. The most important implementation choice is placing **all authoritative mutation + guard evaluation inside an activity** (DB transaction), not in workflow code, so the workflow stays deterministic and all external side effects are naturally idempotency-protected.

The codebase already has the right primitives for Phase 2 governance: an authoritative schema (including `review_decisions` and `case_transition_ledger`), a fail-closed invariant guard pattern (`InvariantDenied` + `to_dict`), and a local docker-compose stack that includes Temporal and Postgres. What’s missing is the Temporal worker/workflow harness, a typed transition-request contract boundary, and a state transition guard that (a) enforces the transition table and (b) emits denial audit events consistently.

Primary recommendation: **implement the guard as a Postgres-backed “transition apply” function invoked only from Temporal orchestration code**, using `StateTransitionRequest` as the single mutation contract and using `request_id` as the idempotency key (`case_transition_ledger.transition_id`). This gives replay-safe semantics and makes denial behavior deterministic for a given DB snapshot.

## Recommendation

Build Phase 2 as two vertical proofs, in this order:

1. **Temporal harness proof (R004 table-stakes):**
   - Minimal `PermitCaseWorkflow` that can start, call a stub activity, block waiting for a signal, then continue.
   - Prefer Temporal’s Python testing utilities (`WorkflowEnvironment.start_time_skipping`) for fast unit-level workflow tests, but keep at least one integration test that points at the docker-compose Temporal/Postgres endpoints.

2. **Guarded transition proof (R005 table-stakes):**
   - Implement a single authoritative activity like `apply_state_transition(request: StateTransitionRequest) -> StateTransitionResult` that:
     - loads the case row,
     - validates `from_state` matches current DB state,
     - checks the transition is allowed by the spec’s transition table,
     - enforces guard assertions relevant to the attempted transition (at minimum `INV-SPS-STATE-002` for protected/submission-bearing transitions),
     - writes a ledger entry with a stable idempotency key (`transition_id = request.request_id`), and
     - updates `permit_cases.case_state` only on success.
   - On denial, write a **denial audit event** (ledger row) with event_type from spec section 20A (e.g. `APPROVAL_GATE_DENIED`) and include `guard_assertion_id` + `normalized_business_invariants[]` in the payload.

This keeps the workflow logic boring (start → wait for decision → request transition) and makes Postgres the single place where authority is enforced.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Workflow determinism & replay hazards | Temporal workflows vs activities split | Workflows must be deterministic; activities are allowed to do I/O and can be retried. Put DB writes + network calls in activities, not workflow code. |
| Idempotency under activity retries | Postgres primary key / unique constraints | Use `case_transition_ledger.transition_id` as an idempotency key (set to `StateTransitionRequest.request_id`). On retry, detect duplicate PK and return the prior result instead of double-writing. |
| Typed boundary validation | Canonical JSON Schemas under `model/sps/contracts/*.schema.json` + Pydantic v2 | Avoid ad-hoc dict payloads. Treat schemas as authoritative contracts; implement Pydantic models mirroring them and validate at the guard boundary. |
| Guard assertion registry | `invariants/sps/guard-assertions.yaml` | Don’t hardcode assertion IDs/reasons in many places; load once and reference by ID so denials are stable + auditable. |

## Existing Code and Patterns

- `docker-compose.yml` — already provisions **Temporal (7233)** + **Temporal UI (8080)** + **Postgres (5432)**; Phase 2 worker should target this for integration.
- `docker/postgres/init/00-init.sql` — creates `sps`, `temporal`, and `temporal_visibility` DBs and roles; ensures Temporal auto-setup works locally.
- `src/sps/config.py` — centralized typed settings + DSN redaction. Temporal settings exist in `.env.example` but are not yet represented in `Settings`.
- `src/sps/db/models.py` — Phase 1 schema already includes:
  - `PermitCase` (`case_state`, `current_package_id`, …)
  - `ReviewDecision`
  - `CaseTransitionLedger` (good home for both success and denial audit events)
- `model/sps/contracts/state-transition-request.schema.json` — authoritative contract for guarded mutation requests; should become the guard boundary input.
- `src/sps/retention/guard.py` — good precedent for fail-closed governance:
  - `InvariantDenied` carries `invariant_id` + context
  - `to_dict()` yields structured denial diagnostics

## Constraints

- Temporal is already part of local infra; **Python Temporal SDK is not yet in `pyproject.toml`** (Phase 2 will need to add it and standardize the worker entry point).
- The codebase is currently **sync SQLAlchemy**. For Phase 2, the lowest-risk path is to keep DB work in **sync activities** (run in a thread pool) rather than introducing SQLAlchemy async everywhere.
- `case_transition_ledger` currently has only `transition_id` PK (no separate idempotency key column). That’s fine if we treat `transition_id == request_id` as the idempotency key.
- Guard assertion IDs and denial audit event names are normalized in spec section **20A** and `invariants/sps/guard-assertions.yaml`; Phase 2 should emit these exact identifiers.

## Common Pitfalls

- **Doing I/O inside workflow code** — keep workflows deterministic; call DB/network only via activities.
- **Non-idempotent DB writes under activity retry** — activities can retry after worker failure/timeouts; use `request_id`-keyed inserts and treat duplicate PK as “already applied”.
- **Generating new ids on retry** — if the workflow recreates `request_id` each time it re-enters a code path, the DB cannot dedupe. Generate once and persist in workflow state, or derive from stable fields (`workflow_id + event`).
- **Fail-open guard behavior** — guard must deny by default for unknown transitions / missing required records; represent the full transition table but allow “unsupported/unimplemented” to safe-stop rather than guessing.
- **Missing denial visibility** — denials that only show up as exceptions in Temporal history are hard to audit; persist denial audit events to `case_transition_ledger` with guard/invariant IDs.

## Open Risks

- Temporal sandbox/determinism surprises in Python (import patterns, asyncio helpers, time/uuid usage). Plan for a replay test using Temporal’s `Replayer` once a workflow history exists.
- Scope creep from “full transition table”: implement the **full representation** (data structure) but only **prove** a minimal path in Phase 2; deny/route-to-safe-stop for the rest.
- Schema gaps for audit/denial events: the repo has a generic `InternalEventEnvelope` schema, but no explicit schema for guard denial payloads. This may become a Phase 2/3 candidate requirement depending on how strictly we want contract coverage.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Temporal (Python SDK) | `wshobson/agents@temporal-python-testing` | available (not installed) — `npx skills add wshobson/agents@temporal-python-testing` |
| SQLAlchemy / Alembic | `wispbit-ai/skills@sqlalchemy-alembic-expert-best-practices-code-review` | available (not installed) — `npx skills add wispbit-ai/skills@sqlalchemy-alembic-expert-best-practices-code-review` |
| Docker Compose | `manutej/luxor-claude-marketplace@docker-compose-orchestration` | available (not installed) — `npx skills add manutej/luxor-claude-marketplace@docker-compose-orchestration` |

(Installed skills in this environment are `debug-like-expert`, `frontend-design`, `gh`, `swiftui`; none are directly specialized for Temporal/Postgres orchestration.)

## Sources

- Guard placement matrix + denial audit event names (source: [spec.md §20A](specs/sps/build-approved/spec.md))
- Full PermitCase transition table + disallowed transitions (source: [spec.md §9](specs/sps/build-approved/spec.md))
- Guard assertion registry and IDs (source: [invariants/sps/guard-assertions.yaml](invariants/sps/guard-assertions.yaml))
- Temporal Python SDK testing patterns (time-skipping env, signals) (source: [Temporal Python SDK README](https://github.com/temporalio/sdk-python/blob/main/README.md))
- Temporal Python SDK: workflow signals/queries and update validators (source: [Temporal Python SDK docs (Context7)](https://context7.com/temporalio/sdk-python/llms.txt))
