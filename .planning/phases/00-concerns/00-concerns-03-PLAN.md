---
phase: 00-concerns
plan: 03
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sps/db/models.py
  - alembic/versions/*.py
autonomous: true
must_haves:
  truths:
    - "Reviewer independence queries use indexes that cover reviewer_id, subject_author_id, and decision_at"
    - "90-day review decision filters no longer require full table scans"
  artifacts:
    - path: "src/sps/db/models.py"
      provides: "ReviewDecision composite indexes"
      contains: "Index(\"ix_review_decisions_reviewer_subject_decision_at\""
    - path: "alembic/versions"
      provides: "migration adding review_decisions indexes"
  key_links:
    - from: "src/sps/db/models.py"
      to: "review_decisions"
      via: "__table_args__ indexes"
      pattern: "review_decisions"
---

<objective>
Add indexes to support reviewer independence metrics queries.

Purpose: Eliminate expensive table scans for 90-day reviewer metrics.
Output: Composite indexes and migration.
</objective>

<execution_context>
@./.opencode/get-shit-done/workflows/execute-plan.md
@./.opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@src/sps/db/models.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add composite indexes to ReviewDecision model</name>
  <files>src/sps/db/models.py</files>
  <action>
Extend ReviewDecision.__table_args__ with indexes that match reviewer independence query filters: (decision_at) and (reviewer_id, subject_author_id, decision_at). Keep existing ix_review_decisions_object index intact. Use clear index names and ensure they are compatible with Postgres.
  </action>
  <verify>python -m pytest tests -k review_decisions</verify>
  <done>ReviewDecision includes new composite indexes for decision_at and reviewer/subject/decision_at.</done>
</task>

<task type="auto">
  <name>Task 2: Create Alembic migration for new indexes</name>
  <files>alembic/versions/*.py</files>
  <action>
Generate a new Alembic revision that adds the two indexes to review_decisions and includes downgrade steps to drop them. Ensure the migration only includes these indexes and does not alter unrelated tables.
  </action>
  <verify>alembic upgrade head</verify>
  <done>Database schema includes the new review_decisions indexes after migration.</done>
</task>

</tasks>

<verification>
`alembic upgrade head` completes and indexes are present.
</verification>

<success_criteria>
- Review decision queries can use targeted indexes instead of table scans.
- Migration exists with upgrade/downgrade for new indexes.
</success_criteria>

<output>
After completion, create `.planning/phases/00-concerns/00-concerns-03-SUMMARY.md`
</output>
