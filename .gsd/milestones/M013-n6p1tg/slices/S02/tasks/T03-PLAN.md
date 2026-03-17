---
estimated_steps: 6
estimated_files: 2
---

# T03: Add docker-compose runbook for admin governance across all change types

**Slice:** M013-n6p1tg S02 — Governed admin changes for source rules + incentive programs with live runbook
**Milestone:** M013-n6p1tg

## Description
Add an operational runbook script that spins up docker-compose services, exercises the intent → review → apply workflow for portal support, source rules, and incentive programs, and asserts audit events in Postgres.

## Steps
1. Create `scripts/verify_m013_s02.sh` patterned after `scripts/verify_m012_s01.sh` with shared helper functions and env setup.
2. Script intent creation, reviewer approval, and governed apply calls for portal support, source rules, and incentive programs using the admin/reviewer API keys.
3. Add Postgres assertions via `docker compose exec` to verify audit events and updated authoritative tables for each change type.
4. Ensure the runbook cleans up or reuses deterministic IDs to stay repeatable across runs.

## Must-Haves
- [ ] Runbook proves intent → review → apply for portal support, source rules, and incentive programs with audit events.
- [ ] Postgres assertions are executed inside the container to avoid host psql dependency.

## Verification
- `bash scripts/verify_m013_s02.sh`
- Runbook exits 0 and prints audit event assertions for all change types.

## Observability Impact
- Signals added/changed: runbook emits audit event checks and table queries in output.
- How a future agent inspects this: run the script and inspect `audit_events` and admin governance tables.
- Failure state exposed: non-zero exit or missing audit rows in runbook output.

## Inputs
- `scripts/verify_m012_s01.sh` — runbook structure and docker-compose/psql patterns.
- `docker-compose.yml` — service names and Postgres access.

## Expected Output
- `scripts/verify_m013_s02.sh` — operational runbook proving governed admin flows across all change types.
