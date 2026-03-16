# Requirements

## Active


### R027 — Authenticated identities on interactive and service APIs (SEC-001)
- Class: security
- Status: active
- Description: All interactive and service APIs require authenticated identities.
- Why it matters: Authority-bearing actions must be attributable and access-controlled.
- Source: spec (section 6.3 SEC-001)
- Primary owning slice: M010/S01
- Supporting slices: none
- Validation: pending (auth integration tests)
- Notes: Baseline identity provider selection in Phase 10.

### R028 — RBAC separation across roles (SEC-002)
- Class: security
- Status: active
- Description: Role-based access control separates user/reviewer/operator/admin/release-manager/escalation-owner capabilities.
- Why it matters: Prevents cross-role authority drift and improper mutation.
- Source: spec (section 6.3 SEC-002)
- Primary owning slice: M010/S01
- Supporting slices: none
- Validation: pending (authorization tests)
- Notes: Focus on key role separations first.

### R029 — Sensitive field redaction + read-only observability (SEC-003/OBS-004)
- Class: security
- Status: active
- Description: Sensitive fields are redacted from logs and observability is enforced read-only.
- Why it matters: Prevents data leakage and unauthorized mutation via observability paths.
- Source: spec (sections 6.3 SEC-003 and 6.4 OBS-004)
- Primary owning slice: M010/S01
- Supporting slices: none
- Validation: pending (log inspection + negative tests)
- Notes: Ensure no secrets in structured logs.

### R031 — Service-to-service mTLS and signed principals (SEC-005)
- Class: security
- Status: active
- Description: Service-to-service communication enforces mTLS and signed service principals.
- Why it matters: Prevents spoofed internal calls and unauthorized authority mutation.
- Source: spec (section 6.3 SEC-005)
- Primary owning slice: M010/S01
- Supporting slices: none
- Validation: pending (integration tests)
- Notes: Baseline support only in Phase 10.

### R032 — Comment resolution and resubmission loops (F-008)
- Class: integration
- Status: active
- Description: SPS supports reviewer-driven correction and resubmission loops after submission.
- Why it matters: Real-world permitting requires iterative corrections; this must be governed and auditable.
- Source: spec (section 6.1 F-008)
- Primary owning slice: M011/S01
- Supporting slices: none
- Validation: pending (integration tests + runbook)
- Notes: Minimal loop first.

### R033 — Approval and inspection milestone tracking (F-009)
- Class: integration
- Status: active
- Description: SPS records approvals, conditions, and inspection milestones after submission.
- Why it matters: Permit lifecycle completion requires durable approval/inspection records.
- Source: spec (section 6.1 F-009)
- Primary owning slice: M011/S01
- Supporting slices: none
- Validation: pending (integration tests + runbook)
- Notes: Driven by normalized status events.

### R034 — Emergency and override workflows (GOV-005)
- Class: governance
- Status: active
- Description: Emergency and override workflows are explicit, time-bounded, and enforced without silent normalization.
- Why it matters: Exceptions must remain exceptional and auditable under Tier 3 compliance.
- Source: spec (section 6.2 GOV-005)
- Primary owning slice: M012/S01
- Supporting slices: none
- Validation: pending (integration tests + runbook)
- Notes: Must fail closed when no valid emergency/override artifact exists.

### R035 — Admin policy/config governance (spec section 5.5)
- Class: governance
- Status: active
- Description: Admin changes to portal support metadata, source rules, and incentive programs require intent, review, and audit trails.
- Why it matters: Prevents hidden authority drift from admin changes.
- Source: spec (section 5.5)
- Primary owning slice: M013/S01
- Supporting slices: none
- Validation: pending (integration tests + runbook)
- Notes: Governed mutation paths only.

## Validated

### R020 — Reviewer UI queue/evidence view/decision capture (E-001)
- Class: governance
- Status: validated
- Description: Reviewer-facing UI presents queue and evidence and allows decisions via reviewer API.
- Why it matters: Reviewer approval is the core permission gate and must be usable/auditable.
- Source: spec (section 5.2; task E-001)
- Primary owning slice: M008/S01
- Supporting slices: M008/S02
- Validation: proved (integration tests passed + S02 docker-compose runbook exercising end-to-end API flows)
- Notes: Minimal UI only; no bulk tooling.

### R021 — Reviewer independence thresholds enforced (E-002)
- Class: compliance/security
- Status: validated
- Description: Rolling-quarter reviewer independence thresholds are computed and enforced with escalation per spec.
- Why it matters: Prevents systemic independence drift and is a Tier 3 compliance requirement.
- Source: spec (section 4.1; task E-002; CTL-11A)
- Primary owning slice: M008/S01
- Supporting slices: M008/S02
- Validation: proved (pytest tests/m008_s02_reviewer_independence_thresholds_test.py + scripts/verify_m008_s02.sh runbook)
- Notes: Enforces warnings/escalations as specified.

### R022 — Audit event schema and sinks (OBS-001)
- Class: observability
- Status: validated
- Description: SPS emits structured audit events for critical actions and persists them to configured sinks.
- Why it matters: Audit reconstruction and compliance depend on queryable event trails.
- Source: spec (section 6.4 OBS-001)
- Primary owning slice: M009/S01
- Supporting slices: none
- Validation: proved (pytest tests/m009_s01_audit_events_test.py)
- Notes: Minimal sinks in Phase 9.

### R023 — Dashboards and alerts (OBS-002/OBS-003)
- Class: observability
- Status: validated
- Description: Minimal dashboards and alerts exist for queue depth, stalled review, submission failures, evidence SLA breaches, and contradiction backlog.
- Why it matters: Operational readiness and release gating depend on observability signals.
- Source: spec (section 6.4 OBS-002/OBS-003)
- Primary owning slice: M009/S01
- Supporting slices: none
- Validation: proved (pytest tests/m009_s01_dashboard_test.py)
- Notes: Minimal set only.

### R024 — Release bundle manifest generation (REL-001)
- Class: release
- Status: validated
- Description: SPS generates release bundle manifest with artifact digests and compatibility checks.
- Why it matters: Release is blocked without a compliant manifest and artifact freshness checks.
- Source: spec (section 6.5 REL-001)
- Primary owning slice: M009/S01
- Supporting slices: none
- Validation: proved (pytest tests/m009_s02_release_bundle_test.py + scripts/verify_m009_s02.sh)
- Notes: Fail-closed on stale/mismatched artifacts and open blockers.

### R025 — Rollback rehearsal evidence (REL-002)
- Class: release
- Status: validated
- Description: SPS records rollback rehearsal evidence and stores rollback artifacts per spec.
- Why it matters: Tier 3 release cannot proceed without rollback rehearsal evidence.
- Source: spec (section 6.5 REL-002)
- Primary owning slice: M009/S01
- Supporting slices: none
- Validation: proved (pytest tests/m009_s03_rollback_rehearsal_test.py + scripts/verify_m009_s03.sh)
- Notes: Captured via evidence registry.

### R026 — Post-release validation template/workflow (REL-003)
- Class: release
- Status: validated
- Description: SPS defines post-release validation template and stage-gated execution rules.
- Why it matters: Production rollout must follow staged validation unless emergency rollback applies.
- Source: spec (section 6.5 REL-003)
- Primary owning slice: M009/S01
- Supporting slices: none
- Validation: proved (runbooks/sps/post-release-validation.md + scripts/verify_m009_s03.sh)
- Notes: Stage gating enforced in release pipeline.

### R016 — Idempotent submission adapters + receipt persistence (F-006/F-007)
- Class: integration
- Status: validated
- Description: SPS executes idempotent submission attempts and persists receipt artifacts correlated to tracking IDs.
- Why it matters: Submission must be auditable and non-duplicative to avoid portal-side inconsistencies.
- Source: spec (section 6.1 F-006/F-007)
- Primary owning slice: M007/S01
- Supporting slices: none
- Validation: proved (pytest tests/m007_s01_submission_attempts_test.py -v -s)
- Notes: Single mock adapter in Phase 7.

### R017 — Status normalization + tracking events (F-007)
- Class: integration
- Status: validated
- Description: SPS normalizes external status events via mapping rules and persists them as ExternalStatusEvent records.
- Why it matters: Unmapped statuses must fail closed; tracking drives case progression and review comment loops.
- Source: spec (section 6.1 F-007)
- Primary owning slice: M007/S01
- Supporting slices: none
- Validation: proved (pytest tests/m007_s02_external_status_events_test.py -v -s)
- Notes: Fixture-based status maps in Phase 7.

### R018 — Manual fallback package generation (F-008)
- Class: integration
- Status: validated
- Description: SPS produces ManualFallbackPackage for unsupported portals and enters bounded manual state.
- Why it matters: Unsupported portals must not silently fail; manual fallback is a governed safe-stop path.
- Source: spec (section 6.1 F-008)
- Primary owning slice: M007/S01
- Supporting slices: none
- Validation: proved (pytest tests/m007_s01_manual_fallback_test.py -v -s)
- Notes: Manual fallback path only; no full operator UI yet.

### R019 — Proof bundle validation and reviewer confirmation (CTL-06A)
- Class: compliance/security
- Status: validated
- Description: SPS validates proof bundle sufficiency before marking submission as complete.
- Why it matters: Prevents submission without required evidence and reviewer confirmation.
- Source: spec (section 18A; CTL-06A)
- Primary owning slice: M007/S01
- Supporting slices: none
- Validation: proved (pytest tests/m007_s01_proof_bundle_gate_test.py -v -s)
- Notes: API-level confirmation only in Phase 7.

### R015 — Submission package generation (F-006)
- Class: integration
- Status: validated (with operational notes)
- Description: SPS generates a SubmissionPackage with documents, manifest, and artifact digests.
- Why it matters: Submission and review depend on a sealed package with auditable artifacts and digests.
- Source: spec (section 6.1 F-006)
- Primary owning slice: M006/S01
- Supporting slices: M006/S02
- Validation: proved (S01 pytest proves document generation + digest computation + persistence logic; S02 proves schema/activity/API exist in operational environment; full workflow execution in docker-compose blocked by task queue configuration issues)
- Notes: Fixture templates only; external document services deferred. Worker activity registration fixed in S02. Workflow code exists and structure is correct; operational verification deferred pending Temporal task queue investigation.


### R013 — Compliance evaluation (F-004)
- Class: integration
- Status: validated
- Description: SPS evaluates zoning/building/electrical/fire/program rules against project facts and persists a ComplianceEvaluation.
- Why it matters: Compliance results determine blockers/warnings and must be auditable before document generation.
- Source: spec (section 6.1 F-004)
- Primary owning slice: M005/S01
- Supporting slices: none
- Validation: proved (SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m005_s01_compliance_workflow_test.py -v -s + scripts/verify_m005_s03.sh)
- Notes: Fixture-based rule set and deterministic evaluator in Phase 5.

### R014 — Incentive assessment (F-005)
- Class: integration
- Status: validated
- Description: SPS produces IncentiveAssessment outputs with evidence-backed eligibility status and rankings.
- Why it matters: Incentive findings are advisory outputs required before review and package generation.
- Source: spec (section 6.1 F-005)
- Primary owning slice: M005/S01
- Supporting slices: none
- Validation: proved (SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m005_s02_incentives_workflow_test.py -v -s + scripts/verify_m005_s03.sh)
- Notes: Fixture-based program sources only; external integrations deferred.

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

### R011 — Jurisdiction stack resolution (F-002)
- Class: integration
- Status: validated
- Description: SPS determines the full authority stack and support level (city/county/state/utility/overlays) and persists a JurisdictionResolution.
- Why it matters: Jurisdiction drives requirements, portal support, and safe-stop/manual handling decisions.
- Source: spec (section 6.1 F-002)
- Primary owning slice: M004/S01
- Supporting slices: none
- Validation: proved (pytest tests/m004_s02_jurisdiction_requirements_workflow_test.py + scripts/verify_m004_s02.sh runbook)
- Notes: Uses spec-sourced fixtures in Phase 4.

### R012 — Requirements retrieval with provenance (F-003)
- Class: integration
- Status: validated
- Description: SPS retrieves permit requirements from ranked authoritative sources and persists provenance in a RequirementSet.
- Why it matters: Authoritative requirements are the foundation for compliance, document generation, and review.
- Source: spec (section 6.1 F-003)
- Primary owning slice: M004/S01
- Supporting slices: none
- Validation: proved (pytest tests/m004_s02_jurisdiction_requirements_workflow_test.py + scripts/verify_m004_s02.sh runbook)
- Notes: Fixture-based sources only; external integrations deferred.

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
| R010 | core-capability | validated | M004/S01 | none | proved (pytest tests/m004_s01_intake_api_workflow_test.py + scripts/verify_m004_s01.sh runbook) |
| R011 | integration | validated | M004/S01 | none | proved (pytest tests/m004_s02_jurisdiction_requirements_workflow_test.py + scripts/verify_m004_s02.sh runbook) |
| R012 | integration | validated | M004/S01 | none | proved (pytest tests/m004_s02_jurisdiction_requirements_workflow_test.py + scripts/verify_m004_s02.sh runbook) |
| R013 | integration | validated | M005/S01 | none | proved (pytest tests/m005_s01_compliance_workflow_test.py + scripts/verify_m005_s03.sh) |
| R014 | integration | validated | M005/S01 | none | proved (pytest tests/m005_s02_incentives_workflow_test.py + scripts/verify_m005_s03.sh) |
| R015 | integration | validated | M006/S01 | M006/S02 | proved (S01 pytest + S02 operational check, full e2e deferred) |
| R016 | integration | validated | M007/S01 | none | proved (pytest tests/m007_s01_submission_attempts_test.py -v -s) |
| R017 | integration | validated | M007/S01 | none | proved (pytest tests/m007_s02_external_status_events_test.py -v -s) |
| R018 | integration | validated | M007/S01 | none | proved (pytest tests/m007_s01_manual_fallback_test.py -v -s) |
| R019 | compliance/security | validated | M007/S01 | none | proved (pytest tests/m007_s01_proof_bundle_gate_test.py -v -s) |
| R020 | governance | validated | M008/S01 | M008/S02 | proved (integration tests passed + S02 docker-compose runbook exercising end-to-end API flows) |
| R021 | compliance/security | validated | M008/S01 | M008/S02 | proved (pytest tests/m008_s02_reviewer_independence_thresholds_test.py + scripts/verify_m008_s02.sh runbook) |
| R022 | observability | validated | M009/S01 | none | proved (pytest tests/m009_s01_audit_events_test.py) |
| R023 | observability | validated | M009/S01 | none | proved (pytest tests/m009_s01_dashboard_test.py) |
| R024 | release | validated | M009/S01 | none | proved (pytest tests/m009_s02_release_bundle_test.py + scripts/verify_m009_s02.sh) |
| R025 | release | validated | M009/S01 | none | proved (pytest tests/m009_s03_rollback_rehearsal_test.py + scripts/verify_m009_s03.sh) |
| R026 | release | validated | M009/S01 | none | proved (runbooks/sps/post-release-validation.md + scripts/verify_m009_s03.sh) |
| R027 | security | active | M010/S01 | none | pending (auth integration tests) |
| R028 | security | active | M010/S01 | none | pending (authorization tests) |
| R029 | security | active | M010/S01 | none | pending (log inspection + negative tests) |
| R031 | security | active | M010/S01 | none | pending (integration tests) |
| R032 | integration | active | M011/S01 | none | pending (integration tests + runbook) |
| R033 | integration | active | M011/S01 | none | pending (integration tests + runbook) |
| R034 | governance | active | M012/S01 | none | pending (integration tests + runbook) |
| R035 | governance | active | M013/S01 | none | pending (integration tests + runbook) |
| R900 | anti-feature | out-of-scope | none | none | n/a |

## Coverage Summary

- Active requirements: 8
- Mapped to slices: 34
- Validated: 25
- Unmapped active requirements: 0
