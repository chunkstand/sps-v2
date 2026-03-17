---
estimated_steps: 6
estimated_files: 1
---

# T06: Integration tests for override guard enforcement

**Slice:** S01 — Emergency/override artifacts + guard enforcement + lifecycle proof
**Milestone:** M012-v8s3qn

## Description

Prove override guard denies transitions without valid override, allows with active override, and denies with expired or out-of-scope override via Temporal+Postgres integration tests. Validates guard assertion ID and normalized invariants in transition ledger denials.

## Steps

1. Create tests/m012_s01_override_guard_test.py with Temporal+Postgres test harness (seed DB, start worker, create workflow)
2. Test case 1: Seed PermitCase in REVIEW_PENDING state; attempt REVIEW_PENDING → APPROVED_FOR_SUBMISSION without override_id (no blocking contradiction) → transition succeeds (override not yet required on this path)
3. Test case 2: Seed blocking contradiction on case; attempt REVIEW_PENDING → APPROVED_FOR_SUBMISSION with override_id='OVR-NONEXISTENT' → transition denied with OVERRIDE_DENIED event, guard_assertion_id=INV-SPS-EMERG-001, normalized_business_invariants=[INV-006]
4. Test case 3: Seed valid OverrideArtifact with expires_at in past; attempt transition with that override_id → OVERRIDE_DENIED with denial_reason='expired'
5. Test case 4: Seed valid OverrideArtifact with expires_at in future and affected_surfaces=['REVIEW_PENDING->APPROVED_FOR_SUBMISSION']; attempt transition with that override_id → transition succeeds, ledger shows CASE_STATE_CHANGED (not OVERRIDE_DENIED)
6. Assert transition ledger events for all test cases include expected guard_assertion_id and normalized_business_invariants fields where applicable

## Must-Haves

- [ ] Test case proving transition succeeds without override when no blocking guard applies
- [ ] Test case proving OVERRIDE_DENIED on nonexistent override_id with guard_assertion_id=INV-SPS-EMERG-001
- [ ] Test case proving OVERRIDE_DENIED on expired override
- [ ] Test case proving transition success with valid, active, in-scope override
- [ ] Assertions on transition ledger guard metadata (guard_assertion_id, normalized_business_invariants)

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m012_s01_override_guard_test.py -v` passes all 4 test cases
- docker compose exec postgres psql shows OVERRIDE_DENIED events with guard_assertion_id in case_transition_ledger

## Inputs

- Override guard implementation from T04 (apply_state_transition activity)
- OverrideArtifact ORM model from T01
- Blocking contradiction seeding pattern from Phase 3 M003/S03
- Temporal+Postgres integration test harness pattern from Phase 5 M005/S01

## Expected Output

- `tests/m012_s01_override_guard_test.py` — 4 integration test cases proving override guard enforcement with guard assertion IDs and normalized invariants
