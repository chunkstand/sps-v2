---
id: T03
parent: S04
milestone: M003-ozqkoh
provides:
  - tests/m003_s04_dissent_artifacts_test.py — 2-scenario integration test proving R009 end-to-end
  - scripts/verify_m003_s04.sh — operator runbook, exits 0 on success
  - db.flush() fix in POST /api/v1/reviews/decisions for FK-safe DissentArtifact INSERT ordering
key_files:
  - tests/m003_s04_dissent_artifacts_test.py
  - scripts/verify_m003_s04.sh
  - src/sps/api/routes/reviews.py
key_decisions:
  - db.flush() inserted after db.add(review_decision_row) inside the ACCEPT_WITH_DISSENT branch — without ORM relationship(), SQLAlchemy cannot infer FK-safe INSERT ordering; flush forces ReviewDecision to DB first while keeping both rows in the same transaction (DECISIONS #36)
  - _reset_db() truncates dissent_artifacts explicitly as the first table, before review_decisions and permit_cases, to avoid FK constraint violations during cleanup (ondelete=RESTRICT on linked_review_id)
  - Request payload uses decision_id, idempotency_key, case_id, reviewer_id, subject_author_id, outcome — matching CreateReviewDecisionRequest; object_type/object_id/reviewer_independence_status are derived by the endpoint, not supplied by caller
patterns_established:
  - Integration test payload matches actual CreateReviewDecisionRequest schema (verified against m003_s03 + s01 tests)
  - _reset_db() explicit table ordering: dissent_artifacts first, then case_transition_ledger, review_decisions, contradiction_artifacts, permit_cases CASCADE
observability_surfaces:
  - reviewer_api.dissent_artifact_created — fired in endpoint before db.commit(); fields dissent_id, linked_review_id, case_id, scope_len
  - GET /api/v1/dissents/{dissent_id} — 200 full artifact or 404 {"error":"not_found","dissent_id":"..."}
  - SELECT dissent_id, linked_review_id, resolution_state FROM dissent_artifacts; — DB inspection
  - Runbook prints postgres_summary table dump to stderr on success
duration: ~25min
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T03: Integration test and operator runbook

**Integration test (2 scenarios) and operator runbook for dissent artifact creation prove R009 end-to-end; DB flush ordering bug in POST /api/v1/reviews/decisions found and fixed.**

## What Happened

Wrote `tests/m003_s04_dissent_artifacts_test.py` and `scripts/verify_m003_s04.sh` following the S03 patterns. On first test run both scenarios failed with a `ForeignKeyViolation` on `fk_dissent_artifacts_linked_review_id` — the ReviewDecision row wasn't present in `review_decisions` when the DissentArtifact INSERT ran.

Root cause: SQLAlchemy's unit-of-work topological sort only respects FK ordering when an ORM `relationship()` is declared. The DissentArtifact and ReviewDecision models have no `relationship()` — only a raw `ForeignKey` column. Without a declared relationship, the flush ordering is unspecified and the two INSERTs can arrive at Postgres in either order.

Fix: added `db.flush()` after `db.add(review_decision_row)` inside the `if row.dissent_flag:` branch in `src/sps/api/routes/reviews.py`. This forces ReviewDecision to the DB before the DissentArtifact INSERT, while both rows remain in the same transaction (rollback is still atomic).

After the fix, both integration scenarios passed. The runbook exited 0 with all psql assertions passing. Unit tests were unaffected.

The test payloads initially included fields (`object_type`, `object_id`, `reviewer_independence_status`) that `CreateReviewDecisionRequest` rejects as `extra_forbidden` — corrected to match the actual model schema.

## Verification

```
SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s04_dissent_artifacts_test.py -v -s
# → 2 passed, 0 failed

bash scripts/verify_m003_s04.sh
# → runbook: ok (exit 0)
# All psql assertions passed: resolution_state=OPEN for ACCEPT_WITH_DISSENT; COUNT=0 for ACCEPT

pytest tests/ -k "not (integration or temporal)" -x -q
# → 9 passed, 9 skipped
```

## Diagnostics

- `reviewer_api.dissent_artifact_created` in API logs — one line per ACCEPT_WITH_DISSENT decision; fields: `dissent_id`, `linked_review_id`, `case_id`, `scope_len`
- `GET /api/v1/dissents/{dissent_id}` with `X-Reviewer-Api-Key` header → 200 + full artifact JSON
- `SELECT dissent_id, linked_review_id, resolution_state FROM dissent_artifacts;` — confirm row presence/absence
- FK violation during flush → `sqlalchemy.exc.IntegrityError` wrapping `psycopg.errors.ForeignKeyViolation fk_dissent_artifacts_linked_review_id` → HTTP 500; check postgres logs for constraint detail
- If `reviewer_api.dissent_artifact_created` absent for an ACCEPT_WITH_DISSENT response → check `dissent_flag` on the ReviewDecision row in DB

## Deviations

- Added `db.flush()` in `src/sps/api/routes/reviews.py` — not mentioned in the task plan. Required to fix a latent FK ordering bug discovered during test execution. The plan said "run integration test"; the test revealed this production bug. Decision recorded as #36 in DECISIONS.md.
- Request payload fields corrected: plan described a generic JSON shape; actual `CreateReviewDecisionRequest` excludes `object_type`, `object_id`, `reviewer_independence_status` (derived by endpoint) and requires `subject_author_id`.

## Known Issues

none

## Files Created/Modified

- `tests/m003_s04_dissent_artifacts_test.py` — new: 2-scenario integration test, R009 proof
- `scripts/verify_m003_s04.sh` — new: operator runbook, exits 0 on success
- `src/sps/api/routes/reviews.py` — added `db.flush()` before DissentArtifact INSERT in ACCEPT_WITH_DISSENT branch
- `.gsd/milestones/M003-ozqkoh/slices/S04/tasks/T03-PLAN.md` — added `## Observability Impact` section (pre-flight fix)
- `.gsd/DECISIONS.md` — appended decision #36 (db.flush() FK ordering)
