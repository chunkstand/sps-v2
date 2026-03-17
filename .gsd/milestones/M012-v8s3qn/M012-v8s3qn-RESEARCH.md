# M012-v8s3qn: Phase 12 — Emergency and Override Governance — Research

**Date:** 2026-03-16

## Summary

This milestone implements GOV-005 emergency declaration and override workflows with time-bounded artifacts, enforced in workflow/guard paths. The spec defines two mechanisms: **emergency records** (emergency_id, incident_id, scope, declared_by, started_at, expires_at, allowed_bypasses, forbidden_bypasses, cleanup_due_at) and **override artifacts** (override_id, scope, justification, start_at, expires_at, affected_surfaces, approver_id, cleanup_required). Both must be explicit, time-bounded, and fail-closed when invalid or expired.

The codebase already has infrastructure for this: `StateTransitionRequest.override_id` exists but is always `None`; `CaseState.EMERGENCY_HOLD` exists but no transitions populate it; `ArtifactClass.OVERRIDE_RECORD` exists in the evidence registry; and guard assertion `INV-SPS-EMERG-001` is defined but not enforced. The spec defines a runbook (`emergency-declaration.md`) with clear forbidden actions and cleanup obligations.

**Primary recommendation:** Implement emergency/override artifacts as ORM models with expiration enforcement, wire guard checks into `apply_state_transition` to validate active overrides before allowing protected transitions, add EMERGENCY_HOLD state transitions via a new API endpoint (gated by escalation-owner role), and prove the lifecycle with integration tests + docker-compose runbook showing declaration → bypass → expiration → cleanup.

## Recommendation

**Approach:** Follow the established artifact persistence pattern (ORM models + idempotent activities + API endpoints + guard enforcement) used successfully in Phases 3–11. Create two new tables: `emergency_records` and `override_artifacts`. Emergency records are created via a new POST /api/v1/emergencies endpoint (escalation-owner RBAC only) and linked to incidents. Override artifacts are created via POST /api/v1/overrides and referenced in `StateTransitionRequest.override_id` when bypassing guards. Guards must validate override existence, scope, and time bounds before allowing bypass. EMERGENCY_HOLD state is entered via emergency declaration and exited via cleanup workflow with reviewer confirmation.

**Why:** This approach reuses proven patterns (Phase 3 contradictions/dissents, Phase 11 post-submission artifacts) and aligns with spec requirements for explicit, auditable, time-bounded exceptions. The existing `override_id` field in `StateTransitionRequest` shows the spec anticipated this design. Fail-closed enforcement prevents silent normalization of exceptions.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Time-bounded artifact expiration | SQLAlchemy query filters + `expires_at` timestamp | Already used in `EvidenceArtifact` and compliance freshness guards; proven pattern for time-based policy enforcement |
| Guard assertion wiring | `src/sps/guards/guard_assertions.py` + `get_normalized_business_invariants()` | Centralized guard-to-invariant mapping; already wired into `apply_state_transition` for contradictions/review independence |
| Idempotent artifact persistence | Activities with PK check + IntegrityError race handling | Used in all Phase 3–11 artifact persistence; ensures exactly-once semantics under Temporal retry |
| API auth/RBAC gating | `require_role()` dependency + JWT role claims | Phase 10 security boundary pattern; already proven for reviewer/operator/release-manager separation |

## Existing Code and Patterns

- `src/sps/workflows/permit_case/contracts.py` — `StateTransitionRequest.override_id: str | None` already exists; currently always `None` but ready for override artifact linkage
- `src/sps/workflows/permit_case/contracts.py` — `CaseState.EMERGENCY_HOLD` enum value exists but no transitions populate it yet
- `src/sps/evidence/models.py` — `ArtifactClass.OVERRIDE_RECORD` already defined; can store override artifacts via `EvidenceRegistry`
- `invariants/sps/guard-assertions.yaml` — `INV-SPS-EMERG-001` guard assertion exists with statement: "Emergency bypass outside declared scope, duration, or policy allowances is forbidden"; links to `INV-006`
- `invariants/sps/INV-006/invariant.yaml` — "Emergency exceptions cannot remain active past allowed duration without renewed override"; severity=high, runtime_guard=orchestrator timer guard
- `runbooks/sps/emergency-declaration.md` — Authoritative runbook defining trigger, diagnostics, exact operator actions, allowed/forbidden bypasses, escalation owners, success criteria, closure evidence
- `src/sps/workflows/permit_case/activities.py:apply_state_transition()` — Guard enforcement function; contradiction blocking guard (lines 983–1001) is the template for override validation
- `src/sps/db/models.py:ContradictionArtifact` and `DissentArtifact` — Artifact persistence patterns with FK to `permit_cases`, resolution state tracking, and timestamps
- `src/sps/api/routes/reviews.py` — Reviewer API with `require_reviewer_api_key` dependency pattern; template for escalation-owner-gated emergency API
- `specs/sps/build-approved/spec.md` — Emergency record contract: `emergency_id, incident_id, scope, declared_by, started_at, expires_at, allowed_bypasses, forbidden_bypasses, cleanup_due_at`; override artifact contract: `override_id, scope, justification, start_at, expires_at, affected_surfaces, approver_id, cleanup_required`
- `specs/sps/build-approved/spec.md` — Forbidden transitions: `EMERGENCY_HOLD -> SUBMITTED directly`; `EMERGENCY_HOLD > 24 hours -> mandatory escalation and redesign review trigger`

## Constraints

- Emergency/override enforcement must fail closed: missing or expired artifacts must deny protected transitions with structured denial events in the transition ledger
- EMERGENCY_HOLD state cannot transition directly to SUBMITTED; must exit via cleanup workflow with reviewer confirmation (per spec section 9.3)
- Emergency duration cannot exceed 24 hours without renewed override (per spec GOV-005 and runbook)
- Override artifacts must be scoped: guards check `affected_surfaces` includes the transition being attempted
- Workflow code must remain deterministic: emergency/override validation happens in activities, not workflow code
- Emergency declarations require incident linkage: cannot declare emergency without an active incident record
- Audit logging is mandatory: emergency/override use must emit audit events even when bypassing other controls (per runbook "What may never be skipped")

## Common Pitfalls

- **Silent override normalization** — Guards must never implicitly allow bypass; override_id must be explicitly provided and validated. Avoid: treating `None` override_id as "allowed in dev mode."
- **Expired override acceptance** — Query must filter `expires_at > NOW()` before allowing bypass. Avoid: trusting that cleanup jobs will purge expired overrides before they're used.
- **Scope creep in emergency state** — Emergency bypasses must be scoped to specific surfaces (e.g., reviewer independence on case X). Avoid: global emergency flags that disable all guards.
- **EMERGENCY_HOLD escape hatches** — Spec forbids direct EMERGENCY_HOLD → SUBMITTED transition. Avoid: adding "quick fix" transitions that skip cleanup workflow.
- **Missing incident linkage** — Emergency records must have valid `incident_id` FK. Avoid: allowing emergency declaration without incident context.
- **Forgetting cleanup obligations** — Emergency exit requires cleanup artifact with retroactive review plan. Avoid: treating emergency as "just revert the state."
- **Override reuse across cases** — Override artifacts should be case-specific or surface-specific, not global. Avoid: single override_id used for hundreds of cases.
- **Temporal workflow nondeterminism** — Override validation must happen in activities, not inline workflow code. Avoid: calling DB from workflow to check override validity.

## Open Risks

- **Emergency duration policy enforcement:** Spec says 24h max, but unclear if this is a hard reject or warning + escalation threshold — decide during planning whether to deny at 24h or allow with mandatory escalation audit event.
- **Override renewal semantics:** Spec says "renewed override" for extensions beyond max duration, but unclear if renewal creates a new artifact or updates `expires_at` — decide if renewal is a new POST or PATCH operation.
- **Incident model gap:** Emergency records require `incident_id` FK but no `incidents` table exists yet — decide if Phase 12 introduces incident model or uses string incident_id with external incident tracker assumption.
- **Cleanup workflow trigger:** Emergency exit requires cleanup artifact, but spec doesn't define if this is automated timer, manual operator action, or reviewer-initiated — decide if cleanup is a separate API endpoint or part of emergency release workflow.
- **Emergency override interaction:** If an emergency record has `allowed_bypasses = ["reviewer_independence"]`, does that implicitly populate `override_id` in state transitions or does operator still need to create explicit override artifact? — decide if emergency record serves as override artifact or if both are required.
- **EMERGENCY_HOLD exit path:** Spec says "prior safe state" but unclear if this is automatic reversion or manual operator-selected target state — decide if we persist pre-emergency state snapshot or require explicit target state in cleanup request.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Temporal workflows | (no specialized skill found) | none found |
| SQLAlchemy | (no specialized skill found) | none found |
| FastAPI | (no specialized skill found) | none found |

## Sources

- Emergency/override requirements and artifact contracts (source: [specs/sps/build-approved/spec.md](specs/sps/build-approved/spec.md) sections 6.2 GOV-005, 9.2 state transitions, 10A artifact catalog, 20 runbooks)
- Guard assertion INV-SPS-EMERG-001 and invariant INV-006 (source: [invariants/sps/guard-assertions.yaml](invariants/sps/guard-assertions.yaml) and [invariants/sps/INV-006/invariant.yaml](invariants/sps/INV-006/invariant.yaml))
- Emergency declaration runbook (source: [runbooks/sps/emergency-declaration.md](runbooks/sps/emergency-declaration.md))
- Existing override_id field and EMERGENCY_HOLD state (source: [src/sps/workflows/permit_case/contracts.py](src/sps/workflows/permit_case/contracts.py) StateTransitionRequest and CaseState enum)
- Contradiction blocking guard template (source: [src/sps/workflows/permit_case/activities.py](src/sps/workflows/permit_case/activities.py) lines 983–1001)
- Artifact persistence patterns from Phase 3 (source: [src/sps/db/models.py](src/sps/db/models.py) ContradictionArtifact and DissentArtifact)
- RBAC auth dependency pattern (source: [src/sps/api/routes/reviews.py](src/sps/api/routes/reviews.py) require_reviewer_api_key)
