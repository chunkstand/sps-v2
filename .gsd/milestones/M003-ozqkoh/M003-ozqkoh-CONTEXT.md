# M003-ozqkoh: Phase 3 — reviewer service + independence/dissent/contradiction governance — Context

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution.

## Project Description

Implement the Phase 3 reviewer/governance surfaces from the SPS v2.0.1 BUILD_APPROVED package:

- A **reviewer service API** (FastAPI) that is the *sole authoritative writer* of `ReviewDecision` records.
- A review injection path that unblocks waiting Temporal workflows by **signaling** them after a review is recorded.
- **Fail-closed reviewer-policy guards** on high-risk surfaces (minimum enforceable subset of reviewer-independence / self-approval prohibition).
- **Contradiction artifacts** (manual create/resolve) and guarded state advancement that blocks while same-rank blocking contradictions are unresolved (INV-003).
- **Dissent artifacts** and lifecycle persistence (recorded + queryable), without implementing release gating yet.

This milestone turns the Phase 2 “signal injection for tests” into a governed reviewer-owned authority boundary aligned with spec authority rules.

## Why This Milestone

Phase 2 proved guarded state transitions and replay-safe Temporal semantics, but review decisions were injected via Temporal signals and persisted by the workflow activity.

The BUILD_APPROVED spec requires:

- `ReviewDecision` writable **only** by the reviewer service.
- reviewer independence / self-approval constraints on high-risk surfaces (INV-008 / CTL-11A).
- same-rank blocking contradictions to block advancement until reviewer resolution (INV-003 / CTL-14A).

Without this milestone, the system can advance via a “test-only injection path” that doesn’t reflect the real authority boundary and can’t enforce reviewer governance where it matters.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Start the local stack (docker-compose Postgres + Temporal) and run a `PermitCaseWorkflow` that becomes review-blocked.
- Record a `ReviewDecision` via an HTTP reviewer API endpoint and see the workflow resume (via Temporal signal) and progress through guarded transitions.
- Create a blocking contradiction artifact for a case, observe that advancement is denied while unresolved, then resolve it and observe advancement succeeds.
- Record an accept-with-dissent decision and see a persisted dissent artifact linked to the review decision.

### Entry point / environment

- Entry point: `./.venv/bin/uvicorn sps.api.main:app` (reviewer endpoints under `/api/v1/...`) + Temporal worker (`./.venv/bin/python -m sps.workflows.worker`)
- Environment: local dev (`docker compose`)
- Live dependencies involved: Postgres, Temporal, Temporal UI (optional), MinIO (optional)

## Completion Class

- Contract complete means:
  - Review API request/response contracts validate (Pydantic v2), including idempotency conflict behavior.
  - Structured denial payloads include stable `guard_assertion_id` + normalized invariant IDs where policy denies.
- Integration complete means:
  - A real workflow run (Temporal + Postgres) is unblocked by a review recorded via HTTP API (not CLI/test-only signal).
  - Unresolved blocking contradiction artifacts prevent `REVIEW_PENDING → APPROVED_FOR_SUBMISSION` until resolved.
- Operational complete means:
  - Reviewer API and worker can be restarted without duplicating review/ledger side effects (idempotency keys enforced at DB boundary).

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- A PermitCaseWorkflow reaches `REVIEW_PENDING`, attempts the protected transition, is denied (fail-closed), then resumes and succeeds **after** a ReviewDecision is recorded via HTTP reviewer API and a Temporal signal is delivered.
- A same-rank blocking contradiction artifact (case-scoped) causes deterministic denial of advancement, and resolving it allows advancement.
- Accept-with-dissent produces a durable dissent artifact linked to the originating ReviewDecision.

And we must prove the above against **real** docker-compose Temporal + Postgres (not only unit tests).

## Risks and Unknowns

- Reviewer identity / independence semantics — without a full auth/RBAC system, we must pick a minimal enforceable independence rule set that is still fail-closed on high-risk surfaces.
- Signal delivery and workflow targeting — reviewer service must reliably signal the correct workflow execution; signal failures must not produce “review recorded but workflow forever waiting” without an operational recovery path.
- Idempotency at the API boundary — duplicate idempotency keys must not create duplicate decisions or inconsistent audit ledger.
- Scope creep — full reviewer UI and full independence metrics (rolling-quarter thresholds) are explicitly *not* the first target; keep to minimal enforceable governance + proof paths.

## Existing Codebase / Prior Art

- `src/sps/api/main.py` — existing FastAPI entrypoint (currently evidence routes only)
- `src/sps/api/routes/evidence.py` — existing `/api/v1/evidence/...` surface used by reviewers
- `src/sps/db/models.py` — existing `ReviewDecision` and `ContradictionArtifact` tables (may need extension) and `CaseTransitionLedger`
- `src/sps/workflows/permit_case/workflow.py` — current review wait + signal pattern (will be adjusted so workflow no longer persists ReviewDecision)
- `src/sps/workflows/permit_case/activities.py` — guarded transition activity (will be extended to block unresolved contradictions)
- `src/sps/guards/guard_assertions.py` + `invariants/sps/guard-assertions.yaml` — stable guard assertion IDs for denials (`INV-SPS-REV-001`, `INV-SPS-CONTRA-001`, etc.)
- `specs/sps/build-approved/spec.md` — review decision API contract + authority rules (ReviewDecision writable only by reviewer service)
- `specs/sps/build-approved/surface-policy.yaml` and `surface-map.yaml` — high-risk surfaces and reviewer-independence requirements

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R006 — reviewer service records ReviewDecision and unblocks workflows
- R007 — reviewer independence/self-approval guard enforced for high-risk surfaces
- R008 — contradiction artifacts + advancement blocking until resolution (INV-003)
- R009 — dissent artifacts recorded and queryable

## Scope

### In Scope

- Add reviewer endpoints to the existing FastAPI app under `/api/v1/...`.
- Require a dev API key for reviewer endpoints (explicit boundary; not production auth).
- Implement `POST /api/v1/reviews/decisions` aligned to spec behavior:
  - client-provided `decision_id` + `idempotency_key`
  - 409 on idempotency-key conflict
  - policy denials include guard/invariant identifiers
  - write to `review_decisions` + an audit/ledger event in `case_transition_ledger`
  - signal the appropriate Temporal workflow after persistence
- Implement contradiction endpoints (manual create/resolve) and extend the state transition guard to deny advancement while blocking contradictions are unresolved.
- Implement dissent artifact persistence linked to ReviewDecision for ACCEPT_WITH_DISSENT decisions (record/export only; no release gating yet).
- Update PermitCaseWorkflow so it no longer persists ReviewDecision itself; it should treat reviewer service as authoritative.

### Out of Scope / Non-Goals

- Full reviewer UI (queue/evidence view/decision capture) beyond HTTP endpoints.
- Rolling-quarter independence metrics export and threshold enforcement.
- Override/emergency artifact creation workflows (exceptions are not supported yet; independence denials remain fail-closed).
- Full auth/RBAC/OIDC (beyond a dev API key gate).

## Technical Constraints

- ReviewDecision is written only by the reviewer service (spec authority rule).
- Workflow code must remain deterministic; any DB reads for review decisions must occur via activities or via signal payloads.
- Denials must fail closed and include stable `guard_assertion_id`/invariant identifiers.
- Idempotency must be enforced at the Postgres boundary for review decisions and any new artifacts.

## Integration Points

- Temporal — reviewer service signals waiting workflows (targeting `permit-case/<case_id>` workflow IDs)
- Postgres — reviewer service persists ReviewDecision + audit/ledger; guard queries contradictions
- Invariants/policy artifacts — surface policy + guard assertions drive stable denial identifiers

## Open Questions

- What is the minimal enforceable reviewer-independence input we can require now (e.g., require `subject_author_id` for high-risk surfaces and deny self-approval when `reviewer_id == subject_author_id`)?
- Should reviewer-service signal failure be a hard error (reject decision) or a soft error (decision recorded with a recovery mechanism to notify/resume workflows)?
