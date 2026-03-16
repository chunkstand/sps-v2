# S02: Independence thresholds + end-to-end runbook — UAT

**Milestone:** M008-z1k9mp
**Written:** 2026-03-16

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: This slice proves cross-component integration (Reviewer API, Postgres schema updates, and rolling threshold logic) which must be verified by asserting effects on a live database via a script.

## Preconditions

- Docker daemon must be running.
- Python virtual environment `.venv` must be present and dependencies installed.

## Smoke Test

Run `bash scripts/verify_m008_s02.sh`. The script should boot the stack, seed test data, post decisions hitting all four independence thresholds (PASS, WARNING, ESCALATION_REQUIRED, BLOCKED), print the resulting JSON and postgres summary, and exit 0.

## Test Cases

### 1. PASS Threshold

1. Boot docker compose and apply migrations.
2. Ensure the system has no prior historical decisions for the reviewer `reviewer-pass` and subject author `author-pass`.
3. Submit a review decision for a new case.
4. **Expected:** Returns 201 Created. The Postgres `review_decisions` row for the decision shows `reviewer_independence_status=PASS` and `subject_author_id=author-pass`.

### 2. WARNING Threshold

1. Seed 5 historical decisions in the last 90 days: 2 for the pair (`reviewer-warning`, `author-warning`), and 3 for other authors. The rate is 2/5 (40%).
2. Submit a review decision for a new case.
3. **Expected:** Returns 201 Created. A warning log `reviewer_api.independence_warning` is emitted. The Postgres row shows `reviewer_independence_status=WARNING`.

### 3. ESCALATION_REQUIRED Threshold

1. Seed 5 historical decisions in the last 90 days: 3 for the pair (`reviewer-escalation`, `author-escalation`), and 2 for other authors. The rate is 3/5 (60%).
2. Submit a review decision for a new case.
3. **Expected:** Returns 201 Created. An escalation log `reviewer_api.independence_escalation` is emitted. The Postgres row shows `reviewer_independence_status=ESCALATION_REQUIRED`.

### 4. BLOCKED Threshold

1. Seed 5 historical decisions in the last 90 days: 4 for the pair (`reviewer-blocked`, `author-blocked`), and 1 for other authors. The rate is 4/5 (80%).
2. Submit a review decision for a new case.
3. **Expected:** Returns 403 Forbidden. A block log `reviewer_api.independence_blocked` is emitted. The API response contains `guard_assertion_id: INV-SPS-REV-001` and `blocked_reason: INDEPENDENCE_THRESHOLD_BLOCKED`. No new row is persisted in `review_decisions`.

## Edge Cases

### First-Time Pair

1. A reviewer has 10 total reviews but 0 for the author. They submit a review, bringing total to 11 and pair count to 1.
2. **Expected:** The rate calculation uses `(pair_count - 1) / total` which evaluates to 0/11 = 0%. The status remains `PASS` instead of falsely flagging as a 100% paired rate.

## Failure Signals

- The runbook script exits with a non-zero status code.
- A 500 error is returned when submitting a decision.
- The 403 response missing `guard_assertion_id` or `blocked_reason`.
- Missing structured logs for warnings/escalations/blocks.

## Requirements Proved By This UAT

- R021 — Reviewer independence thresholds are computed and enforced with escalation and blocking per spec.
- R020 — The end-to-end API wiring is functional and proven live.

## Not Proven By This UAT

- UI/Console click paths (the runbook uses `curl` against the API).
- Authentication and RBAC around the reviewer identity (still relies on a shared `X-Reviewer-Api-Key`).

## Notes for Tester

- The runbook `scripts/verify_m008_s02.sh` resets the `review_decisions` table between scenarios so that the 90-day math evaluates perfectly for each threshold test. Do not run it concurrently with other tests.