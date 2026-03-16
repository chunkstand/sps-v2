---
estimated_steps: 6
estimated_files: 2
---

# T02: Add docker-compose runbook proving reviewer flow + thresholds

**Slice:** S02 — Independence thresholds + end-to-end runbook
**Milestone:** M008-z1k9mp

## Description
Provide an operator runbook that boots the stack, seeds reviewer data, exercises queue/evidence/decision endpoints, and asserts independence threshold enforcement against live Postgres.

## Steps
1. Create `scripts/verify_m008_s02.sh` based on the M007 runbook pattern for docker-compose startup and migrations.
2. Seed REVIEW_PENDING data and historical review_decisions to trigger warning/escalation/blocked thresholds via SQL inserts.
3. Call reviewer queue and evidence summary endpoints with `X-Reviewer-Api-Key` and capture expected outputs.
4. Submit decisions that hit PASS/WARNING/ESCALATION_REQUIRED/BLOCKED paths and assert HTTP responses.
5. Query Postgres inside the container to verify persisted independence status and subject_author_id.

## Must-Haves
- [ ] Runbook starts docker-compose, applies migrations, and uses reviewer API key for all reviewer endpoints.
- [ ] Runbook proves queue → evidence → decision flow and demonstrates threshold enforcement with DB assertions.

## Verification
- `bash scripts/verify_m008_s02.sh`

## Inputs
- `scripts/verify_m007_s03.sh` — runbook structure and docker-compose orchestration pattern.
- `src/sps/api/templates/reviewer_console.html` — reviewer console entrypoint for UI smoke reference.

## Expected Output
- `scripts/verify_m008_s02.sh` — executable end-to-end runbook for reviewer flow and independence thresholds.

## Observability Impact
- Signals: runbook prints reviewer API responses and SQL inspection output to stdout, making independence status, subject_author_id, and HTTP failures visible without tailing service logs.
- Inspection path: operators run the script, then review the echoed curl responses and psql query output to validate queue/evidence/decision flow and threshold enforcement.
- Failure surface: non-2xx curl responses or empty SQL result sets are surfaced via `set -euo pipefail` and explicit response dumps for diagnosis.
