# S02: Postgres-backed guarded transitions (deny + audit) + signal-driven review unblock

**Goal:** Make Postgres the authoritative, fail-closed enforcement point for PermitCase state transitions via a guarded Temporal activity that persists an idempotent transition/audit ledger.

**Demo:** Start a `PermitCaseWorkflow` for a case in `REVIEW_PENDING`. Workflow attempts `REVIEW_PENDING → APPROVED_FOR_SUBMISSION`:
- without a persisted valid `ReviewDecision`, the guard **denies** the transition **fail-closed**, the workflow enters a stable “blocked/waiting” path, and Postgres records an `APPROVAL_GATE_DENIED` ledger event including `guard_assertion_id=INV-SPS-STATE-002` and `normalized_business_invariants=[INV-001]`.
- after sending a `ReviewDecision` via Temporal signal (and persisting it), the workflow re-attempts the same transition and it **applies**, updating `permit_cases.case_state` and recording an “applied” ledger event.

## Must-Haves

- Guard boundary validates `StateTransitionRequest` (Pydantic v2) aligned to `model/sps/contracts/state-transition-request.schema.json`.
- Authoritative activity `apply_state_transition(request)`:
  - enforces `from_state` matches current `permit_cases.case_state`
  - implements minimal transition allowlist for the canonical proof path and **fail-closed** denial for unknown transitions
  - enforces protected transition reviewer gate for `REVIEW_PENDING → APPROVED_FOR_SUBMISSION`
  - persists **both** denials and applied transitions into `case_transition_ledger` keyed by `request_id` (idempotent)
  - updates `permit_cases.case_state` only when transition is applied
- Denial semantics for missing/invalid review gate:
  - `event_type=APPROVAL_GATE_DENIED`
  - includes `guard_assertion_id=INV-SPS-STATE-002` and `normalized_business_invariants` containing `INV-001`
  - is persisted in `case_transition_ledger.payload` in a stable, test-assertable shape
- Signal-driven unblock:
  - workflow waits after denial and resumes after signal
  - signal payload + persisted `review_decisions.decision_outcome` use canonical enum values (`ACCEPT|ACCEPT_WITH_DISSENT|BLOCK`)
- Idempotency proof:
  - re-applying the same `request_id` returns the previously persisted outcome without duplicating ledger rows or double-updating `permit_cases`.

## Proof Level

- This slice proves: `integration`
- Real runtime required: yes
- Human/UAT required: no (optional manual check via Temporal UI)

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s02_transition_guard_db_idempotency_test.py`
- (diagnostic / failure-path) `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s02_transition_guard_db_idempotency_test.py -k denied --log-cli-level=INFO` (prints structured denial logs with `request_id` + `event_type` and proves denial is durable via ledger assertions)
- `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s02_temporal_guarded_transition_workflow_test.py`
- (optional manual proof) With `docker compose up -d` and worker running:
  - Temporal UI shows the denial→wait→signal→apply history at http://localhost:8080

## Observability / Diagnostics

- Runtime signals: structured logs for `activity.start|activity.ok|activity.denied|activity.error` including `workflow_id`, `run_id`, `case_id`, `request_id`, `event_type` (never log secrets).
- Inspection surfaces:
  - Temporal UI workflow history (signal event + activity results)
  - Postgres tables: `permit_cases`, `review_decisions`, `case_transition_ledger`
- Failure visibility:
  - guard denials are durable via `case_transition_ledger` rows
  - activity exceptions still surface in Temporal history + worker logs with correlation tuple
- Redaction constraints: do not log evidence contents or notes fields; only stable IDs and enums.

## Integration Closure

- Upstream surfaces consumed:
  - `src/sps/workflows/permit_case/workflow.py` determinism pattern (activities only)
  - `src/sps/workflows/permit_case/activities.py` DB session pattern
  - Contracts: `model/sps/contracts/state-transition-request.schema.json`, `model/sps/contracts/review-decision.schema.json`, `model/sps/contracts/permit-case.schema.json`
  - Guard assertion registry: `invariants/sps/guard-assertions.yaml`
- New wiring introduced in this slice:
  - new activities registered by `src/sps/workflows/worker.py` for guarded transitions + persisted review decisions
  - workflow path: attempt transition → denied → wait → signal → persist review → re-attempt → applied
- What remains before the milestone is truly usable end-to-end: replay/history-based determinism + retry proofs (S03).

## Tasks

- [x] **T01: Implement Postgres guarded transition + idempotent ledger writes (deny + applied)** `est:2h`
  - Why: This is the authoritative enforcement point for R005; it must be fail-closed, auditable, and idempotent under activity retry.
  - Files: `src/sps/workflows/permit_case/activities.py`, `src/sps/workflows/worker.py`, `src/sps/db/models.py`, `invariants/sps/guard-assertions.yaml`, `tests/m002_s02_transition_guard_db_idempotency_test.py`
  - Do: Add a typed `StateTransitionRequest` boundary model + `StateTransitionResult` (applied/denied). Implement `apply_state_transition(request)` activity that (1) validates request, (2) in a single DB transaction enforces `from_state` and the canonical protected transition gate, (3) writes an idempotent `case_transition_ledger` row keyed by `request_id`, (4) updates `permit_cases.case_state` only on applied, and (5) on duplicate `request_id` returns the persisted prior result without re-applying.
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s02_transition_guard_db_idempotency_test.py`
  - Done when: DB-level tests prove (a) `APPROVAL_GATE_DENIED` payload contains `INV-SPS-STATE-002` + `INV-001`, and (b) duplicate `request_id` does not create extra ledger rows or double-apply state.

- [x] **T02: Wire PermitCaseWorkflow denial→signal unblock→apply path + Temporal/Postgres integration proof** `est:2h`
  - Why: Proves the real end-to-end behavior across Temporal + Postgres for the canonical path, advancing R005 and supporting R004.
  - Files: `src/sps/workflows/permit_case/workflow.py`, `src/sps/workflows/permit_case/contracts.py`, `src/sps/workflows/permit_case/activities.py`, `src/sps/workflows/cli.py`, `tests/m002_s02_temporal_guarded_transition_workflow_test.py`
  - Do: Update bootstrap to seed contract-valid enum values (case starts in `REVIEW_PENDING`). Update signal contract + CLI to use canonical `ReviewDecision.decision_outcome` values. In workflow: attempt guarded transition (stable deterministic `request_id`), handle denied result by waiting; on signal persist the review decision via an idempotent activity, then re-attempt transition with `required_review_id` and complete when applied.
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s02_temporal_guarded_transition_workflow_test.py`
  - Done when: Integration test shows (1) initial denial is persisted in ledger and workflow blocks, (2) signal causes review decision persistence, (3) second attempt applies and updates `permit_cases.case_state=APPROVED_FOR_SUBMISSION`, and (4) ledger has exactly one denial event + one applied event for the run.

## Files Likely Touched

- `src/sps/workflows/permit_case/activities.py`
- `src/sps/workflows/permit_case/contracts.py`
- `src/sps/workflows/permit_case/workflow.py`
- `src/sps/workflows/worker.py`
- `src/sps/workflows/cli.py`
- `tests/m002_s02_transition_guard_db_idempotency_test.py`
- `tests/m002_s02_temporal_guarded_transition_workflow_test.py`
