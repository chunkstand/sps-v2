---
estimated_steps: 8
estimated_files: 2
---

# T04: Override guard in apply_state_transition activity

**Slice:** S01 — Emergency/override artifacts + guard enforcement + lifecycle proof
**Milestone:** M012-v8s3qn

## Description

Implement fail-closed override validation in apply_state_transition activity. Guards deny protected transitions when override is missing, expired, or out-of-scope, emitting OVERRIDE_DENIED ledger events with guard assertion ID and normalized invariants.

## Steps

1. Add _validate_override() helper function in src/sps/workflows/permit_case/activities.py after _check_contradiction_blocking()
2. Implement logic: if StateTransitionRequest.override_id is None, return early (no override provided, not required for all transitions yet); if override_id is not None, query OverrideArtifact by override_id; if not found, deny with OVERRIDE_DENIED; if expires_at <= now(), deny with OVERRIDE_DENIED; parse affected_surfaces JSONB, check if f"{from_state}->{to_state}" in affected_surfaces, if not, deny with OVERRIDE_DENIED
3. On denial: emit log workflow.override_denied (WARNING, fields: workflow_id, case_id, transition, override_id, denial_reason, guard_assertion_id=INV-SPS-EMERG-001, normalized_business_invariants=[INV-006])
4. Insert OVERRIDE_DENIED event in case_transition_ledger with guard_assertion_id=INV-SPS-EMERG-001, normalized_business_invariants as JSONB
5. Wire _validate_override() call into apply_state_transition before the ReviewDecision check on protected transitions (e.g., REVIEW_PENDING → APPROVED_FOR_SUBMISSION)
6. Add override_id to StateTransitionRequest if not already present (it exists per research, just verify it's used)
7. Update apply_state_transition to pass override_id from request to _validate_override()
8. Write unit test proving: override_id=None → no denial; override_id='nonexistent' → OVERRIDE_DENIED + INV-SPS-EMERG-001; expired override → OVERRIDE_DENIED; valid override → allowed

## Must-Haves

- [ ] _validate_override() helper queries OverrideArtifact and enforces time bounds + scope
- [ ] OVERRIDE_DENIED ledger events include guard_assertion_id=INV-SPS-EMERG-001 + normalized_business_invariants=[INV-006]
- [ ] workflow.override_denied structured log emitted on denial
- [ ] Override guard wired into apply_state_transition before protected transitions
- [ ] Unit test coverage for all denial paths (missing, expired, out-of-scope) and success path

## Verification

- Write tests/m012_s01_override_guard_unit_test.py with test cases: test_no_override_id_allows, test_nonexistent_override_denies, test_expired_override_denies, test_out_of_scope_override_denies, test_valid_override_allows
- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m012_s01_override_guard_unit_test.py -v` passes all 5 test cases
- Transition ledger OVERRIDE_DENIED events include guard_assertion_id and normalized_business_invariants fields

## Observability Impact

- Signals added/changed: workflow.override_denied (WARNING, fields: workflow_id, case_id, transition, override_id, denial_reason, guard_assertion_id, normalized_business_invariants)
- How a future agent inspects this: docker compose exec postgres psql -c "SELECT * FROM case_transition_ledger WHERE event_type='OVERRIDE_DENIED'" or query by guard_assertion_id
- Failure state exposed: OVERRIDE_DENIED ledger event with denial_reason (missing|expired|out_of_scope) and guard metadata

## Inputs

- StateTransitionRequest.override_id field from src/sps/workflows/permit_case/contracts.py
- OverrideArtifact ORM model from T01
- Contradiction blocking guard template (src/sps/workflows/permit_case/activities.py lines 983-1001)
- Guard assertion INV-SPS-EMERG-001 from invariants/sps/guard-assertions.yaml

## Expected Output

- `src/sps/workflows/permit_case/activities.py` — _validate_override() helper + wiring into apply_state_transition
- `tests/m012_s01_override_guard_unit_test.py` — unit tests for override guard enforcement
