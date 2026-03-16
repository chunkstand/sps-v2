# M003-ozqkoh — Research

**Date:** 2026-03-16

## Summary

M003 is mostly an authority-boundary refactor plus two new governance surfaces: a reviewer-owned HTTP write path for `ReviewDecision` (with idempotency + policy denials), and contradiction/dissent artifacts that can block state advancement. The codebase is small and already has the critical “Temporal orchestration + Postgres-authoritative guard” pattern: all nondeterministic work happens in activities, and denials are persisted to `case_transition_ledger` with stable `guard_assertion_id` + normalized invariant IDs.

The main constraint is that Phase 2 currently persists `ReviewDecision` from inside the workflow via the `persist_review_decision` activity. M003 must flip that: **only the reviewer API writes `review_decisions`**, and the workflow should treat the review as an external fact and only use a signal to resume and re-attempt the guarded transition. The highest risk operationally is “review recorded but workflow never unblocks” due to signal delivery failure; the research recommendation is to design for a recovery path (at minimum a durable delivery status / retry mechanism) rather than assuming Temporal signaling is always available.

## Recommendation

Prove M003 in this order:

1) **Replace the Phase 2 “workflow writes ReviewDecision” path** with a reviewer API endpoint that (a) persists a `ReviewDecision` idempotently (DB unique key boundary), (b) records a durable audit/ledger event for the decision, and (c) signals `permit-case/<case_id>` to resume.

2) Update `PermitCaseWorkflow` to **stop calling** `persist_review_decision` and instead **only** wait for the `ReviewDecision` signal, then re-attempt the guarded transition with the expected `required_review_id`. This keeps workflow determinism intact and makes the reviewer service the sole writer.

3) Add contradiction blocking in the DB guard (`apply_state_transition`) using the existing `contradiction_artifacts` table, plus manual create/resolve endpoints. Use the spec’s CTL-14A denial audit event type (`CONTRADICTION_ADVANCE_DENIED`) and the guard assertion ID `INV-SPS-CONTRA-001`.

4) Add dissent persistence as a DB artifact linked to `ReviewDecision` for `ACCEPT_WITH_DISSENT` outcomes. Keep it “record + query only” per milestone scope; do not implement release gating.

This ordering front-loads the end-to-end integration proof (HTTP → Postgres → Temporal signal → workflow resumes) before adding additional policy surfaces.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Exactly-once-ish review recording | Postgres unique constraint on `review_decisions.idempotency_key` + “return existing when identical, 409 when conflicting” | This is the correct trust boundary; Temporal retries and client retries both collapse to DB invariants. |
| “Signal-or-start” delivery semantics | Temporal “signal-with-start” pattern via `Client.start_workflow(... start_signal=..., start_signal_args=...)` | Avoids brittle “signal then fail if not running” behavior; provides an operational escape hatch if a workflow wasn’t started yet. |
| Deterministic orchestration | Existing Phase 2 pattern: workflow orchestrates; activities do DB I/O | Keeps Temporal replay-safe and prevents accidental nondeterminism when adding reviewer integration. |
| Stable denial identifiers | `sps.guards.guard_assertions.get_normalized_business_invariants()` + invariant registry under `invariants/sps/` | Lets API and guards emit stable `guard_assertion_id` + normalized invariants without duplicating mappings in code. |

## Existing Code and Patterns

- `src/sps/workflows/permit_case/workflow.py` — current proof workflow: denial → wait for signal → **persists** review → re-attempt transition. M003 must remove the persistence step.
- `src/sps/workflows/permit_case/activities.py` — authoritative Postgres guard in `apply_state_transition`; already emits `APPROVAL_GATE_DENIED` with `guard_assertion_id=INV-SPS-STATE-002` + `normalized_business_invariants`.
- `src/sps/workflows/temporal.py` — shared `connect_client()` and Pydantic data converter wiring; reuse for API-driven signaling.
- `src/sps/api/main.py` + `src/sps/api/routes/evidence.py` — FastAPI routing + “Pydantic v2 extra=forbid” contract enforcement patterns; DB session dependency via `get_db`.
- `src/sps/db/models.py` — existing `ReviewDecision`, `ContradictionArtifact`, `CaseTransitionLedger` tables. Note: there is **no dissent table** yet.
- `invariants/sps/guard-assertions.yaml` — includes `INV-SPS-REV-001` (independence) and `INV-SPS-CONTRA-001` (contradictions) mappings.

## Constraints

- Workflow determinism: DB reads/writes must occur in activities or via signals; no direct DB access in workflow code (`PermitCaseWorkflow`).
- Authority boundary: spec authority rule requires `ReviewDecision` writable only by reviewer service; workflows must stop persisting decisions.
- Denial audit semantics: spec binds CTL-14A and CTL-11A to denial event types (`CONTRADICTION_ADVANCE_DENIED`, `REVIEW_INDEPENDENCE_DENIED`) and guard assertion IDs (`INV-SPS-CONTRA-001`, `INV-SPS-REV-001`).
- Current schema mismatch vs spec: `review-decision.schema.json` does **not** include `idempotency_key` or `schema_version`, but DB model does. The API contract will need to define these explicitly (Pydantic request model) without relying on the binding contract schema.
- FastAPI sync/async split: current evidence endpoints are sync; Temporal signaling requires async calls. Reviewer endpoints should likely be `async def` to avoid blocking.

## Common Pitfalls

- **“Review recorded but workflow never unblocks”** — If the reviewer API commits the `ReviewDecision` and then signaling fails (workflow not running, Temporal outage), the case can be stuck in `REVIEW_PENDING` indefinitely. Avoid by adding a recovery mechanism (candidate requirement) or using Temporal signal-with-start where acceptable.
- **Idempotency conflict semantics are easy to get wrong** — Current `persist_review_decision` activity treats idempotency as “return existing”; it does *not* compare payloads. The reviewer API must implement “409 on same idempotency key with non-identical payload” per spec.
- **Fail-open independence checks** — The repo currently has no author/producer identity model suitable for real independence metrics. A minimal Phase 3 implementation must still fail closed on obvious violations and emit stable denial IDs; do not accept “PASS” blindly without at least a definable rule set.
- **Event type drift** — Phase 2 guard event types are hardcoded strings; adding contradiction denials should follow the spec’s names to keep audit/event queries stable.

## Open Risks

- Reviewer independence inputs are underspecified in the current implementation scaffold: there is no `subject_author_id` / “primary author” field for the reviewed object. Minimal enforceable semantics need a concrete proxy (candidate: require/derive an author id for high-risk review objects, or treat reviewer_independence_status as computed server-side and deny if not PASS/WARNING).
- Signal delivery semantics need an operational story. Without an outbox / retry, M003 can meet contract completeness but fail operational completeness under transient Temporal outages.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | `wshobson/agents@fastapi-templates` | available |
| Temporal (Python) | `wshobson/agents@temporal-python-testing` | available |
| SQLAlchemy/Alembic | `wispbit-ai/skills@sqlalchemy-alembic-expert-best-practices-code-review` | available |
| Pydantic v2 | `bobmatnyc/claude-mpm-skills@pydantic` | available |

## Sources

- Review decision API request shape + error cases (source: `specs/sps/build-approved/spec.md` section “10.3 Review Decision Contract”).
- Contradiction artifact schema + same-rank blocking rule (source: `specs/sps/build-approved/spec.md` section “18.3 Contradiction Artifact Schema”).
- Guard placement matrix mapping CTL-11A/CTL-14A to denial event types and guard assertion IDs (source: `specs/sps/build-approved/spec.md` section “20A. Guard Placement Matrix”).
- Guard assertion → normalized invariant mapping used in runtime denials (source: `invariants/sps/guard-assertions.yaml` + `src/sps/guards/guard_assertions.py`).
- Temporal client wiring used by CLI/tests and reusable for reviewer API signaling (source: `src/sps/workflows/temporal.py`).
- Temporal Python “signal-with-start” pattern (source: [Execute Signal-With-Start](https://github.com/temporalio/documentation/blob/main/docs/develop/python/message-passing.mdx)).
