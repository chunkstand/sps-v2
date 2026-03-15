---
estimated_steps: 7
estimated_files: 2
---

# T02: Implement storage guard enforcing INV-004

**Slice:** S03 — Retention + legal hold guardrails (INV-004) + purge denial tests
**Milestone:** M001-r2v2t3

## Description
Implement a guard that prevents destructive delete/purge operations when evidence is under legal hold, failing closed with explicit invariant denial details.

## Steps
1. Implement `assert_not_on_legal_hold(artifact_id)` querying hold state.
2. Define invariant denial error shape that includes `invariant_id=INV-004`, operation name, artifact_id.
3. Wire the guard into any destructive delete/purge entrypoints (evidence service layer).
4. Ensure denials are consistent across API and internal callers.
5. Add focused tests proving denial behavior.
6. Ensure redaction: never include evidence content.
7. Run deny-focused test subset.

## Must-Haves
- [ ] Destructive delete attempt is denied when hold is active.
- [ ] Denial includes `invariant_id=INV-004` and a human-readable reason.

## Verification
- `./.venv/bin/pytest -q tests/s03_legal_hold_test.py -k deny`

## Observability Impact
- Signals added/changed: invariant-denial error surface with invariant_id + operation.
- How a future agent inspects this: run legal-hold tests; check API 4xx body for invariant metadata.
- Failure state exposed: purge/delete attempts become diagnosable denials instead of silent no-ops.

## Inputs
- Legal hold schema + lookup utilities
- Evidence service delete/purge entrypoints

## Expected Output
- `src/sps/retention/guard.py` — enforcement guard.
- `src/sps/evidence/service.py` — guard used by destructive operations.
