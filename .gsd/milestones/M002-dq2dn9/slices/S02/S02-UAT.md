# S02: Postgres-backed guarded transitions (deny + audit) + signal-driven review unblock — UAT

**Milestone:** M002-dq2dn9
**Written:** 2026-03-15

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: This slice’s definition-of-done is a real Temporal+Postgres behavior proof (guard denial is durable in Postgres; signal resumes the workflow; second guarded attempt applies). A live runtime run validates the observability surfaces (Temporal history + worker logs + Postgres tables) beyond pure unit assertions.

## Preconditions

1. Local infra is running:
   - `docker compose up -d`
   - Services should include: `postgres`, `temporal`, `temporal-ui`.
2. Python environment is ready:
   - `uv sync` (or repo-standard venv setup)
3. Database schema is at head (if needed):
   - `./.venv/bin/alembic upgrade head`
4. Temporal UI is reachable (optional but recommended):
   - http://localhost:8080

## Smoke Test

1. In terminal A (worker):
   - `./.venv/bin/python -m sps.workflows.worker`
2. In terminal B:
   - `./.venv/bin/python -m sps.workflows.cli start --case-id CASE-UAT-S02-SMOKE-1`
   - `./.venv/bin/python -m sps.workflows.cli signal-review --case-id CASE-UAT-S02-SMOKE-1 --decision-outcome ACCEPT --reviewer-id reviewer-uat --wait`
3. **Expected:** The signal command prints a final JSON result where:
   - `initial_result.result == "denied"` with `event_type == "APPROVAL_GATE_DENIED"` and `guard_assertion_id == "INV-SPS-STATE-002"`
   - `final_result.result == "applied"` with `event_type == "CASE_STATE_CHANGED"`

## Test Cases

### 1. Protected transition is denied (fail-closed) without a ReviewDecision

1. Start the worker:
   - `./.venv/bin/python -m sps.workflows.worker`
2. Start a workflow for a fresh case:
   - `./.venv/bin/python -m sps.workflows.cli start --case-id CASE-UAT-S02-DENY-1`
3. **Expected (worker logs):**
   - A `workflow.transition_denied ... event_type=APPROVAL_GATE_DENIED ... guard_assertion_id=INV-SPS-STATE-002`
   - A `workflow.waiting_for_review ... signal=ReviewDecision`
4. Inspect Postgres for the denial ledger row (use your preferred psql shell):
   - Find the workflow’s `(workflow_id, run_id)` in logs, then:
   - `SELECT transition_id, event_type, payload FROM case_transition_ledger WHERE correlation_id = '<workflow_id>:<run_id>' ORDER BY occurred_at;`
5. **Expected (Postgres):**
   - One row with `event_type='APPROVAL_GATE_DENIED'`
   - `payload.guard_assertion_id == 'INV-SPS-STATE-002'`
   - `payload.normalized_business_invariants` contains `'INV-001'`
6. **Expected (Postgres case state):**
   - `SELECT case_state FROM permit_cases WHERE case_id='CASE-UAT-S02-DENY-1';` returns `REVIEW_PENDING`

### 2. ReviewDecision signal unblocks and the guarded transition applies

1. Send a valid ReviewDecision and wait for completion:
   - `./.venv/bin/python -m sps.workflows.cli signal-review --case-id CASE-UAT-S02-DENY-1 --decision-outcome ACCEPT --reviewer-id reviewer-uat --wait`
2. **Expected (CLI output JSON):**
   - `initial_result.result == "denied"`
   - `final_result.result == "applied"`
   - `review_decision_id` is present
3. Inspect Postgres case state:
   - `SELECT case_state FROM permit_cases WHERE case_id='CASE-UAT-S02-DENY-1';`
4. **Expected:** `APPROVED_FOR_SUBMISSION`
5. Inspect Postgres ledger rows for the correlation:
   - `SELECT transition_id, event_type FROM case_transition_ledger WHERE correlation_id = '<workflow_id>:<run_id>' ORDER BY occurred_at;`
6. **Expected:** Exactly two rows:
   - one `APPROVAL_GATE_DENIED` (attempt-1)
   - one `CASE_STATE_CHANGED` (attempt-2)

### 3. Idempotency: repeating the same signal does not create duplicate ReviewDecision rows

1. Re-run the same signal command (same case, same workflow run):
   - `./.venv/bin/python -m sps.workflows.cli signal-review --case-id CASE-UAT-S02-DENY-1 --decision-outcome ACCEPT --reviewer-id reviewer-uat --wait`
2. **Expected:**
   - The workflow is already complete; the CLI returns quickly.
   - The `review_decisions` table still has exactly one row for the workflow’s idempotency key:
     - `SELECT count(*) FROM review_decisions WHERE idempotency_key = 'review/<workflow_id>/<run_id>';` → `1`

## Edge Cases

### BLOCK outcome causes the protected transition to remain denied (workflow fails after re-attempt)

1. Start a new workflow:
   - `./.venv/bin/python -m sps.workflows.cli start --case-id CASE-UAT-S02-BLOCK-1`
2. Signal BLOCK and wait:
   - `./.venv/bin/python -m sps.workflows.cli signal-review --case-id CASE-UAT-S02-BLOCK-1 --decision-outcome BLOCK --reviewer-id reviewer-uat --wait`
3. **Expected:**
   - The workflow does not reach an applied transition.
   - Temporal UI shows the workflow run failed with a message like: `guarded transition did not apply after review`.
   - Postgres ledger contains a denial for the second attempt (inspect via `correlation_id`).

## Failure Signals

- Temporal UI shows activity failures/retries, or the workflow fails before reaching the expected wait/apply states.
- Worker logs contain `activity.error` for `apply_state_transition` or `persist_review_decision` correlated to the case/run.
- Postgres:
  - Missing `case_transition_ledger` rows for the run
  - Denial payload missing `guard_assertion_id=INV-SPS-STATE-002` or `INV-001`
  - `permit_cases.case_state` not updated on the applied path

## Requirements Proved By This UAT

- R005 — Protected transition denial is fail-closed + durable (guard assertion + invariant IDs), and signal-driven review persistence unblocks a subsequent successful guarded transition.

## Not Proven By This UAT

- Replay-history determinism / no-duplicate-side-effects under workflow replay across worker restarts (S03 closes this).
- Full transition-table coverage beyond the canonical proof transition.

## Notes for Tester

- Prefer using a fresh `CASE-UAT-*` case ID each run to avoid workflow ID collisions (`workflow_id = permit-case/<case_id>`).
- If Postgres was reset but Temporal history was not, old workflows may retry activities against missing DB rows (noisy but not a logic failure for this slice). Reset both if you want a clean UAT environment.
