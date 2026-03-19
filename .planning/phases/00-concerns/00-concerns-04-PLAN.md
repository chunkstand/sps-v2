---
phase: 00-concerns
plan: 04
type: execute
wave: 2
depends_on:
  - "00-concerns-03"
files_modified:
  - src/sps/db/models.py
  - alembic/versions/*.py
  - src/sps/api/routes/reviews.py
  - src/sps/workflows/permit_case/workflow.py
  - tests/workflows/test_review_signal_delivery.py
autonomous: true
must_haves:
  truths:
    - "Review decision signals are retried when Temporal delivery fails"
    - "Persisted review decisions eventually reach the workflow even after initial signal failure"
  artifacts:
    - path: "src/sps/db/models.py"
      provides: "signal outbox persistence"
    - path: "src/sps/api/routes/reviews.py"
      provides: "enqueue + retry for review decision signals"
    - path: "tests/workflows/test_review_signal_delivery.py"
      provides: "coverage for signal retry/reconciliation"
  key_links:
    - from: "src/sps/api/routes/reviews.py"
      to: "src/sps/workflows/permit_case/workflow.py"
      via: "ReviewDecision signal retry"
      pattern: "ReviewDecision"
---

<objective>
Add a durable retry path for ReviewDecision signal delivery to the PermitCase workflow.

Purpose: Avoid stale workflow state when Temporal signal delivery fails.
Output: Outbox + retry job and tests.
</objective>

<execution_context>
@./.opencode/get-shit-done/workflows/execute-plan.md
@./.opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@src/sps/api/routes/reviews.py
@src/sps/workflows/permit_case/workflow.py
@src/sps/db/models.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add a review signal outbox table</name>
  <files>src/sps/db/models.py, alembic/versions/*.py</files>
  <action>
Introduce a ReviewDecisionSignalOutbox model with fields for decision_id, case_id, status, last_error, attempt_count, next_retry_at, created_at, updated_at. Add indexes on status/next_retry_at and case_id. Create an Alembic migration to add the table and indexes with downgrade support.
  </action>
  <verify>alembic upgrade head</verify>
  <done>Database has a durable outbox table for pending review decision signals.</done>
</task>

<task type="auto">
  <name>Task 2: Enqueue and retry review decision signals</name>
  <files>src/sps/api/routes/reviews.py, src/sps/workflows/permit_case/workflow.py, tests/workflows/test_review_signal_delivery.py</files>
  <action>
On review decision creation, enqueue an outbox record in the same DB transaction. Update _send_review_signal to mark the outbox record delivered on success and record failures with backoff (next_retry_at). Add a lightweight retry runner (e.g., async function invoked on a schedule or a management command) that loads pending outbox rows and re-sends signals. Add tests that simulate a failed send and confirm a retry succeeds and updates status.
  </action>
  <verify>python -m pytest tests/workflows -k review_signal_delivery</verify>
  <done>Failed signal deliveries are retried and eventually delivered with updated outbox status.</done>
</task>

</tasks>

<verification>
`python -m pytest tests/workflows -k review_signal_delivery` passes.
</verification>

<success_criteria>
- Review decision signals persist in an outbox and retry until delivered.
- Outbox status reflects success/failure with backoff metadata.
</success_criteria>

<output>
After completion, create `.planning/phases/00-concerns/00-concerns-04-SUMMARY.md`
</output>
