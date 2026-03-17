---
estimated_steps: 10
estimated_files: 1
---

# T08: Docker-compose runbook for full emergency/override lifecycle

**Slice:** S01 — Emergency/override artifacts + guard enforcement + lifecycle proof
**Milestone:** M012-v8s3qn

## Description

Operational proof of end-to-end emergency/override governance with real API + worker + Postgres. Runbook exercises declare emergency → create override → protected transition with override → expire override → transition denial → cleanup exit, proving the full lifecycle with real entrypoints.

## Steps

1. Create scripts/verify_m012_s01.sh with provisioning, lifecycle steps, and cleanup
2. Provision docker-compose stack (scripts/start_temporal_dev.sh), start worker (in background), start API (in background)
3. STEP 1: POST /cases with intake contract → 201 + case_id; start PermitCaseWorkflow for case_id; advance to REVIEW_PENDING state
4. STEP 2: POST /emergencies with escalation-owner JWT + case_id → 201 + emergency_id; verify emergency_records row exists via psql
5. STEP 3: POST /overrides with escalation-owner JWT + case_id + affected_surfaces=["REVIEW_PENDING->APPROVED_FOR_SUBMISSION"] → 201 + override_id; verify override_artifacts row exists via psql
6. STEP 4: Seed blocking contradiction on case; POST /reviews/decisions with override_id → 201 (transition allowed because valid override bypasses contradiction guard); verify case_transition_ledger shows CASE_STATE_CHANGED (not OVERRIDE_DENIED)
7. STEP 5: UPDATE override_artifacts SET expires_at=NOW()-'1 hour'::interval WHERE override_id=... (simulate expiration); verify updated expires_at via psql
8. STEP 6: POST /reviews/decisions with expired override_id → 403 + OVERRIDE_DENIED response; verify case_transition_ledger shows OVERRIDE_DENIED event with guard_assertion_id=INV-SPS-EMERG-001
9. STEP 7: Send EmergencyHoldExit signal with reviewer_confirmation_id → case exits EMERGENCY_HOLD (if entered during lifecycle); verify ledger shows exit transition
10. Cleanup: docker compose down -v; exit 0 if all assertions pass, exit 1 on any failure

## Must-Haves

- [ ] Runbook provisions docker-compose stack with Postgres + Temporal + worker + API
- [ ] STEP 1-3: Emergency + override creation proven via API + DB
- [ ] STEP 4: Protected transition succeeds with valid override
- [ ] STEP 5-6: Override expiration denies transition with guard assertion ID
- [ ] STEP 7: EMERGENCY_HOLD cleanup proven with reviewer confirmation
- [ ] All assertions use docker exec postgres psql for DB verification
- [ ] Runbook exits 0 on success, 1 on failure

## Verification

- `bash scripts/verify_m012_s01.sh` exits 0
- All 7 lifecycle steps pass with expected HTTP status codes and DB state
- runbook.pass logs emitted for each successful assertion
- runbook.fail logs emitted with diagnostic context on any failure

## Observability Impact

- Signals added/changed: runbook.step (INFO, fields: step_num, step_description), runbook.pass (INFO, fields: assertion_description), runbook.fail (ERROR, fields: assertion_description, expected, actual)
- How a future agent inspects this: bash scripts/verify_m012_s01.sh output shows step-by-step progress and assertion results
- Failure state exposed: runbook exits 1 and prints step_num + assertion that failed; docker compose logs show API/worker logs for debugging

## Inputs

- All T01-T07 implementations (ORM models, API endpoints, guard enforcement, workflow transitions, integration tests)
- Docker-compose provisioning pattern from M011/S02 (scripts/start_temporal_dev.sh)
- Postgres assertion pattern from M003/S03 (docker exec postgres psql queries)
- JWT generation for escalation-owner role (Phase 10 auth utils)

## Expected Output

- `scripts/verify_m012_s01.sh` — end-to-end runbook proving declare → bypass → expire → cleanup lifecycle with real API + worker + Postgres
