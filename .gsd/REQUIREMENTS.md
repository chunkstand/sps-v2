# Requirements

## Active

### R011 — Jurisdiction stack resolution (F-002)
- Class: integration
- Status: active
- Description: SPS determines the full authority stack and support level (city/county/state/utility/overlays) and persists a JurisdictionResolution.
- Why it matters: Jurisdiction drives requirements, portal support, and safe-stop/manual handling decisions.
- Source: spec (section 6.1 F-002)
- Primary owning slice: M004/S01
- Supporting slices: none
- Validation: pending (integration tests + runbook)
- Notes: Uses spec-sourced fixtures in Phase 4.

### R012 — Requirements retrieval with provenance (F-003)
- Class: integration
- Status: active
- Description: SPS retrieves permit requirements from ranked authoritative sources and persists provenance in a RequirementSet.
- Why it matters: Authoritative requirements are the foundation for compliance, document generation, and review.
- Source: spec (section 6.1 F-003)
- Primary owning slice: M004/S01
- Supporting slices: none
- Validation: pending (integration tests + runbook)
- Notes: Fixture-based sources only; external integrations deferred.

### R013 — Compliance evaluation (F-004)
- Class: integration
- Status: active
- Description: SPS evaluates zoning/building/electrical/fire/program rules against project facts and persists a ComplianceEvaluation.
- Why it matters: Compliance results determine blockers/warnings and must be auditable before document generation.
- Source: spec (section 6.1 F-004)
- Primary owning slice: M005/S01
- Supporting slices: none
- Validation: pending (integration tests + runbook)
- Notes: Fixture-based rule set and deterministic evaluator in Phase 5.

### R014 — Incentive assessment (F-005)
- Class: integration
- Status: active
- Description: SPS produces IncentiveAssessment outputs with evidence-backed eligibility status and rankings.
- Why it matters: Incentive findings are advisory outputs required before review and package generation.
- Source: spec (section 6.1 F-005)
- Primary owning slice: M005/S01
- Supporting slices: none
- Validation: pending (integration tests + runbook)
- Notes: Fixture-based program sources only; external integrations deferred.

### R015 — Submission package generation (F-006)
- Class: integration
- Status: active
- Description: SPS generates a SubmissionPackage with documents, manifest, and artifact digests.
- Why it matters: Submission and review depend on a sealed package with auditable artifacts and digests.
- Source: spec (section 6.1 F-006)
- Primary owning slice: M006/S01
- Supporting slices: none
- Validation: pending (integration tests + runbook)
- Notes: Fixture templates only; external document services deferred.

### R016 — Idempotent submission adapters + receipt persistence (F-006/F-007)
- Class: integration
- Status: active
- Description: SPS executes idempotent submission attempts and persists receipt artifacts correlated to tracking IDs.
- Why it matters: Submission must be auditable and non-duplicative to avoid portal-side inconsistencies.
- Source: spec (section 6.1 F-006/F-007)
- Primary owning slice: M007/S01
- Supporting slices: none
- Validation: pending (integration tests + runbook)
- Notes: Single mock adapter in Phase 7.

### R017 — Status normalization + tracking events (F-007)
- Class: integration
- Status: active
- Description: SPS normalizes external status events via mapping rules and persists them as ExternalStatusEvent records.
- Why it matters: Unmapped statuses must fail closed; tracking drives case progression and review comment loops.
- Source: spec (section 6.1 F-007)
- Primary owning slice: M007/S01
- Supporting slices: none
- Validation: pending (integration tests + runbook)
- Notes: Fixture-based status maps in Phase 7.

### R018 — Manual fallback package generation (F-008)
- Class: integration
- Status: active
- Description: SPS produces ManualFallbackPackage for unsupported portals and enters bounded manual state.
- Why it matters: Unsupported portals must not silently fail; manual fallback is a governed safe-stop path.
- Source: spec (section 6.1 F-008)
- Primary owning slice: M007/S01
- Supporting slices: none
- Validation: pending (integration tests + runbook)
- Notes: Manual fallback path only; no full operator UI yet.

### R019 — Proof bundle validation and reviewer confirmation (CTL-06A)
- Class: compliance/security
- Status: active
- Description: SPS validates proof bundle sufficiency before marking submission as complete.
- Why it matters: Prevents submission without required evidence and reviewer confirmation.
- Source: spec (section 18A; CTL-06A)
- Primary owning slice: M007/S01
- Supporting slices: none
- Validation: pending (integration tests + runbook)
- Notes: API-level confirmation only in Phase 7.

## Validated

### R010 — Intake normalization into Project (F-001)
- Class: core-capability
- Status: validated
- Description: SPS creates a PermitCase from intake and persists a normalized Project object using the spec-derived intake contract.
- Why it matters: All downstream research/compliance/document work depends on normalized project facts that are durable and auditable.
- Source: spec (section 6.1 F-001)
- Primary owning slice: M004/S01
- Supporting slices: none
- Validation: proved (pytest tests/m004_s01_intake_api_workflow_test.py + scripts/verify_m004_s01.sh runbook)
- Notes: Spec-derived intake contract; no external intake integrations yet.

### R009 — Dissent artifacts recorded and queryable
- Class: governance
- Status: validated
- Description: Accept-with-dissent decisions create a durable dissent artifact linked to the originating review decision, with resolution state.
- Why it matters: High-risk dissent tightens release conditions and must be auditable even before release gating is implemented.
- Source: spec (section 17.6; task E-003; dissent artifact contract matrix)
- Primary owning slice: M003/S04
- Supporting slices: none
- Validation: proved (Postgres integration tests — ACCEPT_WITH_DISSENT → dissent_artifacts row with linked_review_id, case_id, scope, rationale, resolution_state=OPEN; ACCEPT → no dissent row; GET /api/v1/dissents/{dissent_id} returns full artifact; operator runbook verify_m003_s04.sh exits 0)
- Notes: Release-blocking enforcement is deferred until release gate milestone(s).

### R008 — Contradiction artifacts + advancement blocking until resolution (INV-003)
- Class: compliance/security
- Status: validated
- Description: Same-rank blocking contradictions are persisted and cause guarded advancement denials until reviewer resolution.
- Why it matters: Contradictions must not allow auto-advance; this is the core governance control for contradictory sources.
- Source: spec (section 18; CTL-14A; INV-003; guard assertion INV-SPS-CONTRA-001)
- Primary owning slice: M003/S03
- Supporting slices: none
- Validation: proved (Postgres integration tests — blocking contradiction → CONTRADICTION_ADVANCE_DENIED + guard_assertion_id=INV-SPS-CONTRA-001 + INV-003; resolve via HTTP API → CASE_STATE_CHANGED; non-blocking contradiction transparent to guard; operator runbook verify_m003_s03.sh exits 0)
- Notes: Manual create/resolve via API; contradiction detector deferred.

### R007 — Reviewer independence/self-approval guard on high-risk surfaces (INV-008)
- Class: compliance/security
- Status: validated
- Description: Reviewer decision creation is fail-closed on high-risk surfaces when independence/self-approval policy is violated, absent supported exception artifacts.
- Why it matters: Prevents authority drift and self-approval on critical surfaces; required by CTL-11A and INV-008.
- Source: spec (spec.md section 8.5/14.4; CTL-11A; INV-008)
- Primary owning slice: M003/S02
- Supporting slices: none
- Validation: proved (Postgres integration tests — self-approval → 403 + guard_assertion_id=INV-SPS-REV-001 + INV-008 + no DB row; distinct reviewer → 201 + reviewer_independence_status=PASS in DB)
- Notes: Threshold-metrics enforcement may be deferred, but self-approval prohibition is now enforced and proven.

### R006 — Reviewer service records ReviewDecision and unblocks workflows
- Class: core-capability
- Status: validated
- Description: A reviewer service (HTTP API) is the sole authoritative writer of ReviewDecision records, enforces idempotency and policy denials, and signals waiting Temporal workflows to resume.
- Why it matters: Reviewer approval is the permission gate for protected transitions; Phase 2 test-only signal injection must be replaced by a governed reviewer-owned authority boundary.
- Source: spec (spec.md section 10.3; tasks E-001)
- Primary owning slice: M003/S01
- Supporting slices: none
- Validation: proved (Temporal+Postgres integration tests + operator runbook verify_m003_s01.sh)
- Notes: Proved HTTP POST → Postgres review_decisions row → Temporal signal → workflow APPROVED_FOR_SUBMISSION; 409 on idempotency conflict; 401 on missing/wrong key.

### R004 — Temporal harness runs PermitCaseWorkflow with replay-safe semantics
- Class: core-capability
- Status: validated
- Description: Temporal worker can run a PermitCaseWorkflow (minimal end-to-end flow with stubbed activities) and is replay-safe and idempotent.
- Why it matters: Temporal is the authoritative harness; without a working workflow substrate, reviewer gates and authority controls can’t be enforced or audited.
- Source: spec (runtime-implementation-profile.md; tasks D-001–D-004)
- Primary owning slice: M002/S01
- Supporting slices: M002/S02, M002/S03
- Validation: proved (Temporal+Postgres integration tests + offline history replay + post-commit activity retry failpoints + runbook)
- Notes: S01 proved a representative wait→signal→resume path (Temporal + Postgres) via `tests/m002_s01_temporal_permit_case_workflow_test.py`. S03 proved offline determinism replay (`temporalio.worker.Replayer`) on a real captured history and exactly-once Postgres effects under real activity retries (post-commit failpoints) and the operator runbook.

### R001 — Authoritative Postgres schema for core SPS entities
- Class: core-capability
- Status: validated
- Description: Postgres schema + migrations exist for PermitCase, Project, review records, contradiction records, transition ledger, and evidence metadata.
- Why it matters: Everything else (Temporal workflows, reviewer gates, release controls) depends on authoritative state being durable and queryable.
- Source: inferred (spec Phase 1 / tasks B-001)
- Primary owning slice: M001/S01
- Supporting slices: M001/S02, M001/S03
- Validation: proved (alembic upgrade + Postgres-backed integration tests)
- Notes: Schema is intentionally thin in some places (string enums, JSONB payloads) in Phase 1; tighten with constraints as guarded workflows land.

### R002 — Evidence registry with stable IDs and object storage binding
- Class: integration
- Status: validated
- Description: Evidence artifacts can be registered, stored, and retrieved by stable ID; content lives in S3-compatible storage and is correlated to metadata in Postgres.
- Why it matters: Review, audit, and release gates are evidence-driven; evidence must be queryable and durable.
- Source: inferred (spec tasks B-002, F-010, INV-SPS-EVID-001)
- Primary owning slice: M001/S02
- Supporting slices: M001/S03
- Validation: proved (MinIO-backed adapter tests + end-to-end roundtrip)
- Notes: Retrieval SLA enforcement is later; Phase 1 focuses on correctness and stable identifiers.

### R003 — Legal hold prevents purge or destructive delete of bound evidence (INV-004)
- Class: compliance/security
- Status: validated
- Description: Any purge/destructive delete of evidence is denied while a legal hold is active.
- Why it matters: Tier 3 compliance; audit reconstruction depends on evidence preservation.
- Source: spec (INV-004; SEC-004; runbook legal-hold.md)
- Primary owning slice: M001/S03
- Supporting slices: none
- Validation: proved (hold bindings + INV-004 guard + denial + purge exclusion tests)
- Notes: Phase 1 proves fail-closed denial semantics; destructive purge remains disabled.

### R005 — State transition guard enforces protected transitions and emits denials
- Class: compliance/security
- Status: validated
- Description: All authoritative PermitCase state mutations are mediated by a state transition guard enforcing the transition table + guard assertions + relevant invariants; denials include guard/invariant identifiers.
- Why it matters: Prevents authority drift and direct specialist mutation; provides the core governance enforcement point.
- Source: spec (sections 9, 13, 20A; invariants/guard-assertions; tasks C-002–C-004)
- Primary owning slice: M002/S02
- Supporting slices: M002/S03
- Validation: proved (Temporal+Postgres integration tests; idempotent transition ledger)
- Notes: Proved the canonical protected transition gate: `REVIEW_PENDING -> APPROVED_FOR_SUBMISSION` is denied without a persisted valid ReviewDecision (durable `APPROVAL_GATE_DENIED` ledger event including `guard_assertion_id=INV-SPS-STATE-002` + `normalized_business_invariants=[INV-001]`), then succeeds after signal-driven ReviewDecision persistence and re-attempt.

## Deferred

(none)

## Out of Scope

### R900 — Payment processing
- Class: anti-feature
- Status: out-of-scope
- Description: SPS does not process permit fee payments in v1.
- Why it matters: Prevents scope creep and regulatory expansion; explicitly excluded in spec.
- Source: spec (Section 2.6; clarifications C-010B)
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Any change requires new intent + major spec revision.

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| R001 | core-capability | validated | M001/S01 | M001/S02,M001/S03 | proved (alembic + pytest) |
| R002 | integration | validated | M001/S02 | M001/S03 | proved (minio + e2e pytest) |
| R003 | compliance/security | validated | M001/S03 | none | proved (deny + purge tests) |
| R004 | core-capability | validated | M002/S01 | M002/S02,M002/S03 | proved (Temporal+Postgres + replay + retry idempotency + runbook) |
| R005 | compliance/security | validated | M002/S02 | M002/S03 | proved (Temporal+Postgres integration tests) |
| R006 | core-capability | validated | M003/S01 | none | proved (Temporal+Postgres integration tests + operator runbook) |
| R007 | compliance/security | validated | M003/S02 | none | proved (Postgres integration tests — self-approval → 403 + INV-SPS-REV-001 + INV-008 + no DB row; distinct reviewer → 201 + PASS) |
| R008 | compliance/security | validated | M003/S03 | none | proved (Postgres integration tests — blocking → CONTRADICTION_ADVANCE_DENIED + INV-SPS-CONTRA-001 + INV-003; resolve → CASE_STATE_CHANGED; runbook ok) |
| R009 | governance | validated | M003/S04 | none | proved (Postgres integration tests — ACCEPT_WITH_DISSENT → dissent_artifacts row queryable; ACCEPT → no row; runbook ok) |
| R010 | core-capability | active | M004/S01 | none | pending (integration tests + runbook) |
| R011 | integration | active | M004/S01 | none | pending (integration tests + runbook) |
| R012 | integration | active | M004/S01 | none | pending (integration tests + runbook) |
| R013 | integration | active | M005/S01 | none | pending (integration tests + runbook) |
| R014 | integration | active | M005/S01 | none | pending (integration tests + runbook) |
| R015 | integration | active | M006/S01 | none | pending (integration tests + runbook) |
| R016 | integration | active | M007/S01 | none | pending (integration tests + runbook) |
| R017 | integration | active | M007/S01 | none | pending (integration tests + runbook) |
| R018 | integration | active | M007/S01 | none | pending (integration tests + runbook) |
| R019 | compliance/security | active | M007/S01 | none | pending (integration tests + runbook) |
| R900 | anti-feature | out-of-scope | none | none | n/a |

## Coverage Summary

- Active requirements: 10
- Mapped to slices: 19
- Validated: 9
- Unmapped active requirements: 0
