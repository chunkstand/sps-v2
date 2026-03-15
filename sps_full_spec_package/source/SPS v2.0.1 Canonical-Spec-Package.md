\# Solar Permitting System (SPS) \- BUILD\_APPROVED Canonical Spec Package  
\#\# Document Control  
| Field | Value |  
| \--- | \--- |  
| Title | Solar Permitting System (SPS) \- BUILD\_APPROVED Canonical Spec Package |  
| Spec ID | SPS-001-BUILD |  
| Version | 2.0.1 |  
| Status | BUILD\_APPROVED |  
| Owners | Product Manager; Architecture Lead; Compliance Lead |  
| Reviewers | Engineering Lead; Operations Lead; Security Lead; Governance Lead |  
| Approvers | VP Engineering; VP Operations; Compliance Counsel |  
| Created Date | 2026-03-11 |  
| Last Updated | 2026-03-11 |  
| Supersedes | SPS-001 v1.0.0; SPS Clarifications Register; SPS Hardening Notes |  
| Superseded By | \- |  
| Release State | Build approved |  
| Lifecycle Stage | Pre-release |  
| Authority Level | Production authoritative |  
| Compliance Profile | Tier 3 |  
| Trigger Traits | Mutable production authority; reviewer approval gates; regulated workflow; asynchronous workflows; external dependencies; time-based obligations; rollback-sensitive migration; multi-party review; incident-driven operational burden |  
| Normative Precedence | Signed enforcement artifacts \> release artifacts \> schemas/policies/model exports \> normative prose \> generated diagrams \> informative notes |  
| Changelog | 2.0.1 \- Closure revision adding binding artifact contracts, runtime guard placement matrix, external status normalization policy, manual fallback proof sufficiency rules, reviewer independence hardening, and release compatibility rules |  
\#\# Executive Verdict  
This package is the authoritative execution contract for SPS. It supersedes the earlier pre-implementation SPS specification and closes the remaining build blockers by defining complete state models, authoritative mutation paths, contracts, control allocation, runbooks, release/rollback rules, contradiction handling, reviewer independence rules, binding artifact contracts, status normalization rules, compatibility matrices, and queryable evidence obligations.  
\*\*Final build-readiness verdict: BUILD\_APPROVED\*\*  
BUILD\_APPROVED is granted under these conditions:  
1\. Implementation MUST conform to this package without narrowing reviewer gates, evidence obligations, runtime guards, or release controls.  
2\. No production release may occur without the release bundle, rollback rehearsal evidence, compatibility validation, and post-release validation report defined here.  
3\. Any deviation from this package on authority-bearing surfaces is a blocker until resolved through intent, review, and approval artifacts.  
4\. Binding artifact contracts defined in this package are normative and release-blocking where marked.  
5\. Examples in this package are explanatory unless explicitly marked normative.  
\#\# Why the compliance profile is Tier 3  
SPS qualifies as Tier 3 because it is not just an internal workflow aid. It prepares and submits regulated permit packages to external authorities, relies on reviewer gates, stores evidence that must remain reconstructible, must handle emergency and unsupported-case paths without silent authority drift, and can materially affect commercial project outcomes. The system therefore requires stronger release conditions, reviewer independence thresholds, runtime guard placement, operational readiness evidence, and rollback rehearsal rather than Tier 2 minimums.  
\#\# Package Completeness Statement  
This package is intentionally longer than the Standing Framework canonical instruction set because it is not doctrine. It is the actual product-specific execution contract for SPS. It contains the doctrine-required sections plus SPS-specific decisions, state models, interfaces, data contracts, policies, incident rules, artifact metadata rules, and operator procedures.  
\---  
\# 1\. Overview  
SPS is a planner \-\> executors \-\> reviewer permitting system for commercial solar and adjacent commercial energy projects. It transforms intake information into validated permit packages, submits them to authorities, tracks status, resolves review comments, records approvals, and captures incentive intelligence across federal, state, utility, and local programs.  
SPS exists because permit preparation and submission are fragmented across jurisdiction research, code review, document preparation, portal-specific filing, and post-submission coordination. Manual workflows are slow, inconsistent, hard to audit, and difficult to scale across jurisdictions. SPS provides deterministic orchestration, evidence-backed validation, controlled submission, and durable audit reconstruction.  
The outcome produced by SPS is not merely a draft analysis. The system produces a governed permit case with validated requirements, compliance status, generated documents, reviewer decisions, submission evidence, resubmission records, approval records, and incentive findings.  
Adjacent systems include city and county permit portals, state building code systems, utility interconnection portals, GIS/geocoding services, document storage, observability systems, CI/CD, identity services, and organizational ticketing and incident systems.  
The boundary of this spec ends at SPS orchestration, storage, governance, evidence, and integration contracts. It does not cover structural design engineering, electrical design authoring by licensed engineers, construction execution, payment processing, procurement, or installer ERP functions.  
\---  
\# 2\. Purpose and Scope  
\#\# 2.1 Functional Scope  
SPS MUST support:  
\- project intake  
\- normalization into structured project data  
\- jurisdiction discovery  
\- permit requirement research  
\- zoning and code compliance verification  
\- incentive discovery  
\- permit document generation  
\- reviewer approval and dissent handling  
\- portal submission  
\- permit tracking  
\- review comment resolution  
\- resubmission workflows  
\- final approval tracking  
\- audit reconstruction  
\#\# 2.2 Operational Scope  
SPS runs as a multi-tenant cloud service. Authoritative state exists only in controlled production environments. All authority-bearing actions MUST be mediated by orchestrator services and reviewer controls defined in this package.  
\#\# 2.3 Deployment Scope  
SPS is deployed through staged release: dev \-\> staging \-\> canary \-\> limited production \-\> full production. Rollout is permissioned, not automatic. Database and model migrations are governed separately from code rollout but bound into the same release bundle.  
\#\# 2.4 Governance Scope  
SPS operates under Standing Framework doctrine. AI outputs are proposals only. Reviewer approval is a permission gate. Evidence must be queryable. Contradictions must be surfaced and resolved. Exceptions must remain exceptional.  
\#\# 2.5 Integration Scope  
Covered integrations:  
\- geocoding and parcel lookup  
\- zoning and jurisdiction data sources  
\- AHJ permit portals  
\- utility interconnection portals where applicable  
\- incentive data sources  
\- document generation and storage  
\- identity and access management  
\- observability, audit, ticketing, and incident systems  
\#\# 2.6 Explicit Non-Goals  
SPS does not:  
\- perform engineering calculations as the authority of record  
\- stamp plans  
\- process permit fee payments in v1  
\- guarantee permit approval  
\- replace legal review or licensed professional judgment  
\- manage construction scheduling  
\- support residential permitting in this package version  
\- silently mutate authoritative state from observability or autonomous feedback loops  
\---  
\# 3\. Audience and Roles  
| Role | Responsibilities | Required Decisions | Escalation Path | Authority Limits | Required Artifacts |  
| \--- | \--- | \--- | \--- | \--- | \--- |  
| Product Manager | Defines product intent and bounded policy choices | Scope decisions, source coverage, roadmap gating | VP Product | Cannot bypass reviewer or release controls | Intent artifacts, policy sign-off |  
| Architecture Lead | Owns architecture, control model, domain model | Authority paths, service boundaries, model semantics | CTO / VP Engineering | Cannot unilaterally waive governance controls | Architecture sections, model export, control allocation |  
| Planner Service | Decomposes cases into tasks and sequences work | Task graph computation only | Reviewer or operator for blocked cases | Cannot approve authoritative mutation alone | Task graph, orchestration events |  
| Specialist Agents | Produce domain outputs | No final authority decisions | Planner \-\> Reviewer | Cannot commit authoritative state directly | Structured outputs with citations |  
| Reviewer | Accepts, blocks, or accepts-with-dissent | Approval of task outputs, contradictions, releases where delegated | Governance Lead | Cannot approve own high-risk work except bounded emergency exception | Review decisions, dissent records |  
| Operator | Executes runbooks, monitors cases, handles manual fallbacks | Incident and runbook actions | On-call manager / escalation owner | Cannot bypass authority gates except documented emergency procedures | Incident records, handoff evidence |  
| Release Manager | Bundles releases and enforces release gates | Release or rollback decision | VP Engineering | Cannot lower build or release criteria | Release bundle manifest, approvals, rollback record |  
| Escalation Owner | Handles emergency declarations, overrides, redesign triggers | Emergency declaration, time-bounded override | Executive leadership / compliance counsel | Cannot silently normalize exceptions | Override records, emergency records |  
| Compliance Counsel | Reviews regulatory and retention posture | Legal hold, retention override, regulatory interpretation | General Counsel | Cannot directly mutate permit case state | Legal hold artifact, compliance sign-off |  
\---  
\# 4\. Goals, SLOs, and Non-Goals  
\#\# 4.1 Goals  
| Metric | Target | Window | Evidence |  
| \--- | \--- | \--- | \--- |  
| Submission readiness | \>= 90% of packages accepted without missing-material rejection | Quarterly | Submission and rejection analytics |  
| Time to package readiness | Median \<= 5 business days | Quarterly | PermitCase state timing metrics |  
| Critical evidence retrieval | 99% of evidence retrieval requests \<= 5s | Monthly | API latency dashboards |  
| Availability | 99.9% | Monthly | Service SLO dashboards |  
| Reviewer independence | \<= 25% repeated same author-reviewer pair on high-risk surfaces; \> 25% warning; \> 35% release escalation | Rolling quarter | Review metrics export |  
| Unsupported portal safe-stop compliance | 100% of unsupported portal cases enter bounded manual state | Each release | Manual fallback test suite |  
| Contradiction handling | 100% of same-rank source contradictions create contradiction artifact and block auto-advance | Each release | Contradiction workflow tests |  
\#\# 4.2 Non-Goals  
The non-goals listed in Section 2.6 are binding. Any attempt to add payment processing, residential scope, or autonomous self-approving behavior requires a new intent artifact and a major-version spec revision.  
\---  
\# 5\. Stories and Acceptance Criteria  
\#\# 5.1 Developer Story  
As a commercial solar developer, I want to submit project facts and receive an evidence-backed permit package, so that I can file with fewer rejections and trace every decision.  
Acceptance criteria:  
\- SPS MUST normalize freeform intake into a structured Project object.  
\- SPS MUST determine jurisdiction stack and portal support status.  
\- SPS MUST assemble authoritative requirement and compliance findings with citations and source ranking.  
\- SPS MUST block submission until review approval exists.  
\- SPS MUST expose all generated documents, checklists, and evidence by stable IDs.  
\#\# 5.2 Reviewer Story  
As a reviewer, I need to inspect outputs, contradictions, and evidence before allowing state mutation.  
Acceptance criteria:  
\- Each review surface MUST present producer, version, confidence, citations, and unresolved contradictions.  
\- Reviewer MUST be able to ACCEPT, ACCEPT\_WITH\_DISSENT, or BLOCK.  
\- High-risk surfaces MUST require reviewer independence checks.  
\- Dissent on high-risk surfaces MUST tighten release conditions.  
\#\# 5.3 Operator Story  
As an operator, I need executable runbooks for submission failure, unsupported portals, stale rules, emergency declaration, rollback, and legal hold.  
Acceptance criteria:  
\- Each critical runbook MUST define trigger, diagnostics, exact actions, forbidden actions, closure evidence, and escalation owner.  
\- Unsupported portal cases MUST generate a ManualFallbackPackage.  
\- Emergency mode MUST expire within the defined maximum duration unless re-approved through override.  
\#\# 5.4 External Authority Story  
As an AHJ or utility portal, I need a correctly formatted, correlated submission package.  
Acceptance criteria:  
\- Payload MUST contain correlation IDs, manifest ID, package version, and artifact digests.  
\- Submission adapter MUST be idempotent.  
\- Portal receipts MUST be persisted as evidence artifacts.  
\#\# 5.5 Admin Story  
As an administrator, I need to update portal support metadata, source rules, and incentive programs without creating hidden authority drift.  
Acceptance criteria:  
\- Admin changes MUST flow through reviewed configuration or policy mutation paths.  
\- Every admin change MUST leave an intent, review, and audit trail.  
\- Config changes affecting authority behavior MUST be classified as high-risk surfaces.  
\---  
\# 6\. Requirements and Traceability  
\#\# 6.1 Functional Requirements  
| ID | Requirement | Owner | Verification | Linked Objects | Linked Controls |  
| \--- | \--- | \--- | \--- | \--- | \--- |  
| F-001 | SPS MUST create a PermitCase from intake and persist a normalized Project object. | Platform | Unit \+ integration tests | PermitCase, Project | CTL-01 |  
| F-002 | SPS MUST determine complete authority stack: city, county, state, utility, overlays, special district. | Research/Geo | Integration tests | JurisdictionResolution, AuthorityProfile | CTL-02 |  
| F-003 | SPS MUST retrieve requirements from ranked authoritative sources and preserve provenance. | Research | Retrieval tests | RequirementSet, EvidenceArtifact | CTL-03 |  
| F-004 | SPS MUST evaluate zoning, building, electrical, fire, and program eligibility rules against project facts. | Compliance | Rule engine tests | ComplianceEvaluation, IncentiveAssessment | CTL-04 |  
| F-005 | SPS MUST generate a SubmissionPackage with documents, manifest, artifact digests, and required attachments. | Document | Document tests | SubmissionPackage, DocumentArtifact | CTL-05 |  
| F-006 | SPS MUST submit only after review approval and pre-submission validation passes. | Submission | Negative \+ integration tests | SubmissionAttempt | CTL-06 |  
| F-007 | SPS MUST track status changes and comments after submission. | Tracking | Polling/webhook tests | ExternalStatusEvent, ReviewComment | CTL-07 |  
| F-008 | SPS MUST support reviewer-driven correction and resubmission loops. | Comment Resolution | Workflow tests | CorrectionTask, ResubmissionPackage | CTL-08 |  
| F-009 | SPS MUST record approvals, conditions, and inspection milestones. | Tracking | End-to-end tests | ApprovalRecord, InspectionMilestone | CTL-09 |  
| F-010 | SPS MUST expose queryable evidence for review, release, operations, and audit. | Platform | SLA \+ retrieval tests | EvidenceArtifact, AuditEvent | CTL-10 |  
\#\# 6.2 Governance Requirements  
| ID | Requirement | Owner | Verification | Controls |  
| \--- | \--- | \--- | \--- | \--- |  
| GOV-001 | Every authority-bearing state mutation MUST require explicit allowed mutation path and evidence. | Governance | Workflow tests | CTL-01, CTL-06 |  
| GOV-002 | Reviewer approval MUST gate all progression into submission or authoritative publish states. | Governance | Negative tests | CTL-01 |  
| GOV-003 | Reviewer independence MUST be enforced on high-risk surfaces except bounded emergency exceptions. | Governance | Metrics \+ policy tests | CTL-11 |  
| GOV-004 | Dissent MUST be preserved and MUST tighten release or advancement conditions on high-risk surfaces. | Governance | Review workflow tests | CTL-12 |  
| GOV-005 | Exception, waiver, and emergency use MUST be time-bounded and anti-normalized. | Governance | Policy tests \+ dashboards | CTL-13 |  
| GOV-006 | Same-rank authoritative-source contradiction MUST block auto-advance and require reviewer resolution. | Compliance | Contradiction tests | CTL-14 |  
\#\# 6.3 Security Requirements  
| ID | Requirement | Owner | Verification |  
| \--- | \--- | \--- | \--- |  
| SEC-001 | All interactive and service APIs MUST use authenticated identities. | Security | Auth integration tests |  
| SEC-002 | RBAC MUST separate user, reviewer, operator, admin, release-manager, and escalation-owner capabilities. | Security | Authorization tests |  
| SEC-003 | Sensitive fields MUST be redacted from logs and lower-trust observability views. | Security/Ops | Log inspection tests |  
| SEC-004 | Legal hold MUST prevent deletion or purge of held evidence and case records. | Compliance | Retention tests |  
| SEC-005 | Service-to-service communication MUST use mTLS and signed service principals. | Security | Integration tests |  
\#\# 6.4 Observability Requirements  
| ID | Requirement | Owner | Verification |  
| \--- | \--- | \--- | \--- |  
| OBS-001 | Every critical action MUST emit structured audit events with correlation fields. | Ops | Event schema tests |  
| OBS-002 | Dashboards MUST show queue depth, time in state, stale-rule cases, unsupported portal cases, and release health. | Ops | Dashboard validation |  
| OBS-003 | Alerts MUST exist for evidence retrieval SLA breach, stalled review, submission failure spikes, and contradiction backlog. | Ops | Alert drills |  
| OBS-004 | Observation MUST NOT auto-mutate policy or state except through governed authority path. | Governance | Negative tests |  
\#\# 6.5 Validation and Release Requirements  
| ID | Requirement | Owner | Verification |  
| \--- | \--- | \--- | \--- |  
| VAL-001 | All requirements MUST map to tests, controls, model elements, or runbooks. | Architecture | Traceability export |  
| VAL-002 | Runtime guards MUST exist for high-severity failures where review-only or CI-only enforcement is insufficient. | Architecture | Runtime guard tests |  
| REL-001 | Release is blocked if any blocker contradiction, unresolved dissent on high-risk surfaces, or stale generated binding artifact exists. | Release | Release gate tests |  
| REL-002 | Every release MUST include rollback rehearsal evidence for critical paths. | Release | Release bundle review |  
| REL-003 | Production rollout MUST follow canary then staged rollout unless emergency rollback or security containment requires otherwise. | Release/Ops | Runbook drills |  
\---  
\# 7\. Architecture  
\#\# 7.1 System Boundary  
Within boundary:  
\- Planner service  
\- Specialist execution services  
\- Reviewer service and UI/API  
\- Orchestrator and state machine engine  
\- Policy and rule services  
\- Submission adapters  
\- Evidence store  
\- Audit/event store  
\- Case database  
\- Release gating and governance validation pipeline  
Outside boundary:  
\- AHJ portals  
\- utility portals  
\- 3rd-party GIS providers  
\- external code repositories  
\- external incentive sources  
\- human authorities and applicants  
\#\# 7.2 Authoritative vs Non-Authoritative Layers  
\*\*Authoritative layer\*\*  
\- PermitCase state store  
\- Review decisions  
\- Policy versions  
\- Release approvals  
\- Evidence metadata registry  
\- Audit event store  
\*\*Non-authoritative layer\*\*  
\- Specialist agent computations  
\- Retrieval caches  
\- search indexes  
\- analytics projections  
\- preview renders  
\- observability summaries  
No non-authoritative component may write authoritative state except through the orchestrator’s governed mutation endpoints.  
\#\# 7.3 Control Plane vs Data Plane  
\*\*Control plane\*\*  
\- planner  
\- reviewer  
\- orchestrator  
\- policy engine  
\- release gating pipeline  
\- identity and authorization  
\*\*Data plane\*\*  
\- retrieval workers  
\- rule evaluation workers  
\- document generation workers  
\- portal adapters  
\- tracking workers  
\#\# 7.4 Component Inventory  
| Component | Purpose | Inputs | Outputs | Failure Modes |  
| \--- | \--- | \--- | \--- | \--- |  
| Planner | Builds task graph and next actions | Intake, case state, policy versions | TaskGraph, MissingDataRequest | Incorrect dependency graph, stale inputs |  
| Intake Agent | Normalizes freeform project data | User text, attachments | NormalizedProjectDraft | Misclassification, missing extraction |  
| Jurisdiction Agent | Resolves authority stack | Address, parcel, geo data | JurisdictionResolutionDraft | Ambiguous parcel, conflicting geo sources |  
| Research Agent | Retrieves permit requirements and source evidence | JurisdictionResolution, policy | RequirementSetDraft | Missing source, stale source, contradiction |  
| Compliance Agent | Applies code and policy rules | Project facts, requirements | ComplianceEvaluationDraft | Rule mismatch, stale rules |  
| Incentive Agent | Identifies programs and eligibility | Project facts, location, rules | IncentiveAssessmentDraft | Coverage gap, conflicting eligibility |  
| Document Agent | Generates forms, packages, manifests | Approved data | SubmissionPackageDraft | Template mismatch, missing attachment |  
| Reviewer | Accepts, blocks, or dissents | Draft outputs, evidence | ReviewDecision | Incomplete evidence, contradiction unresolved |  
| Submission Adapter | Sends package to portal | Approved package | SubmissionReceipt or failure | Portal timeout, unsupported workflow |  
| Tracking Agent | Monitors external status | Submission IDs, webhook/poll events | ExternalStatusEvents | Polling failure, unmapped status |  
| Comment Resolution Agent | Classifies review comments and produces remediation tasks | Review comments, evidence | CorrectionTaskDrafts | Misclassification, incomplete loopback |  
\#\# 7.5 Trust Boundaries  
Boundary A: User and browser/API client \-\> SPS frontend/API  
Boundary B: Internal services \-\> authoritative storage  
Boundary C: Internal services \-\> external authoritative sources  
Boundary D: Submission adapters \-\> AHJ portals  
Boundary E: Observability \-\> audit retrieval consumers  
All cross-boundary calls require authentication, correlation IDs, and timeout behavior.  
\#\# 7.6 Failure Domains  
\- Planner failure: queue stall but no silent state mutation  
\- Reviewer failure: progression blocked, case held in review-pending or blocked state  
\- Portal adapter failure: submission safe-stop or manual fallback  
\- Evidence store failure: release block and audit incident  
\- Policy/rule failure: stale-rule block or contradiction block  
\- Identity failure: read-only containment, no privileged mutation  
\#\# 7.7 Scaling and Isolation  
Cases are tenant-scoped and sharded by organization and region. External polling workers are isolated from authoritative mutation workers. Document generation uses worker pools. Manual fallback handling is queue-based and does not share execution lanes with automated submission lanes.  
\---  
\# 8\. Machine-Usable Domain Model  
\#\# 8.1 Domain Model Purpose  
The SPS domain model governs workflow, validation, review, evidence, release, and audit behavior. Removal of the model would break task planning, rule application, release gating, evidence retrieval, and contradiction handling.  
\#\# 8.2 Core Objects  
\#\#\# 8.2.1 PermitCase  
Purpose: canonical case-level authority record.  
| Property | Type | Required | Source of Truth | Mutability | Sensitivity | Example |  
| \--- | \--- | \--- | \--- | \--- | \--- | \--- |  
| case\_id | string | yes | case DB | immutable | internal | CASE-2026-000123 |  
| tenant\_id | string | yes | case DB | immutable | internal | TEN-001 |  
| project\_id | string | yes | case DB | immutable | internal | PROJ-001 |  
| case\_state | enum | yes | case DB | governed | internal | REVIEW\_PENDING |  
| review\_state | enum | yes | case DB | governed | internal | PENDING |  
| submission\_mode | enum | yes | case DB | governed | internal | AUTOMATED |  
| portal\_support\_level | enum | yes | case DB | governed | internal | FULLY\_SUPPORTED |  
| current\_package\_id | string | no | case DB | governed | internal | PKG-001 |  
| current\_release\_profile | string | yes | policy store | governed | internal | TIER3-V1 |  
| created\_at | datetime | yes | case DB | immutable | internal | 2026-03-11T00:00:00Z |  
| updated\_at | datetime | yes | case DB | governed | internal | 2026-03-11T02:00:00Z |  
| legal\_hold | boolean | yes | compliance store | governed | restricted | false |  
| closure\_reason | enum | no | case DB | governed | internal | APPROVED |  
\#\#\# 8.2.2 Project  
Purpose: normalized project facts used by research, compliance, incentives, and documents.  
Fields include address, parcel\_id, project\_type, system\_size\_kw, battery\_flag, service\_upgrade\_flag, trenching\_flag, structural\_modification\_flag, roof\_type, occupancy\_classification, utility\_name, and applicant/contact metadata.  
\#\#\# 8.2.3 JurisdictionResolution  
Purpose: resolved authority stack and support classification.  
Key fields: city\_authority\_id, county\_authority\_id, state\_authority\_id, utility\_authority\_id, zoning\_district, overlays, permitting\_portal\_family, support\_level, manual\_requirements, evidence\_ids.  
\#\#\# 8.2.4 RequirementSet  
Purpose: authoritative requirement bundle tied to source evidence and freshness.  
Key fields: requirement\_set\_id, jurisdiction\_ids, permit\_types, forms\_required, attachments\_required, fee\_rules, source\_rankings, freshness\_expires\_at, contradiction\_state.  
\#\#\# 8.2.5 ComplianceEvaluation  
Purpose: rule-by-rule pass/fail/unknown evaluation.  
Key fields: evaluation\_id, rule\_results\[\], overall\_status, blockers\[\], warnings\[\], stale\_rule\_flag, contradiction\_ids\[\], reviewer\_notes.  
\#\#\# 8.2.6 IncentiveAssessment  
Purpose: incentive eligibility and evidence-backed program assessment.  
Key fields: assessment\_id, candidate\_programs\[\], eligibility\_status, stacking\_conflicts\[\], deadlines\[\], source\_ids\[\], advisory\_value\_range, authoritative\_value\_state.  
\#\#\# 8.2.7 SubmissionPackage  
Purpose: sealed package for review and submission.  
Key fields: package\_id, package\_version, manifest\_id, artifact\_ids\[\], hash\_digest, target\_portal\_family, package\_status, approved\_for\_submission\_at.  
\#\#\# 8.2.8 SubmissionAttempt  
Purpose: each distinct submission or resubmission transaction.  
Key fields: submission\_attempt\_id, package\_id, adapter\_id, idempotency\_key, attempt\_number, outcome, external\_tracking\_id, receipt\_artifact\_id, submitted\_at.  
\#\#\# 8.2.9 ReviewDecision  
Purpose: authoritative reviewer outcome artifact.  
Key fields: decision\_id, object\_type, object\_id, decision\_outcome, reviewer\_id, reviewer\_independence\_status, evidence\_ids\[\], contradiction\_resolution, dissent\_flag, notes, decision\_at.  
\#\#\# 8.2.10 EvidenceArtifact  
Purpose: queryable evidence unit.  
Key fields: artifact\_id, artifact\_class, producing\_service, linked\_case\_id, linked\_object\_id, retention\_class, checksum, storage\_uri, authoritativeness, provenance, created\_at, expires\_at, legal\_hold\_flag.  
\#\#\# 8.2.11 ContradictionArtifact  
Purpose: explicit record of conflicting normative or source inputs.  
Key fields: contradiction\_id, scope, source\_a, source\_b, ranking\_relation, detected\_by, blocking\_effect, reviewer\_resolution\_required, resolution\_status.  
\#\# 8.3 Enumerations  
\- CaseState: DRAFT, INTAKE\_PENDING, INTAKE\_COMPLETE, JURISDICTION\_PENDING, JURISDICTION\_COMPLETE, RESEARCH\_PENDING, RESEARCH\_COMPLETE, COMPLIANCE\_PENDING, COMPLIANCE\_COMPLETE, INCENTIVES\_PENDING, INCENTIVES\_COMPLETE, DOCUMENT\_PENDING, DOCUMENT\_COMPLETE, REVIEW\_PENDING, BLOCKED, APPROVED\_FOR\_SUBMISSION, SUBMISSION\_PENDING, SUBMITTED, COMMENT\_REVIEW\_PENDING, CORRECTION\_PENDING, RESUBMISSION\_PENDING, APPROVED, CLOSED, CANCELLED, MANUAL\_SUBMISSION\_REQUIRED, EMERGENCY\_HOLD, ROLLED\_BACK  
\- ReviewOutcome: ACCEPT, ACCEPT\_WITH\_DISSENT, BLOCK  
\- SubmissionMode: AUTOMATED, MANUAL  
\- PortalSupportLevel: FULLY\_SUPPORTED, PARTIALLY\_SUPPORTED\_READ\_ONLY, PARTIALLY\_SUPPORTED\_UPLOAD\_ONLY, UNSUPPORTED  
\- FreshnessState: FRESH, STALE, INVALIDATED  
\- ArtifactClass: REQUIREMENT\_EVIDENCE, COMPLIANCE\_REPORT, INCENTIVE\_REPORT, DOCUMENT, MANIFEST, RECEIPT, AUDIT\_EVENT, REVIEW\_RECORD, INCIDENT\_RECORD, OVERRIDE\_RECORD  
\- ContradictionState: NONE, SAME\_RANK\_BLOCKING, HIGHER\_RANK\_OVERRIDE, RESOLVED  
\- RetentionClass: CASE\_CORE\_7Y, CASE\_CORE\_EXTENDED, LEGAL\_HOLD, TRANSIENT\_CACHE, RELEASE\_EVIDENCE  
\#\# 8.4 Link Types  
| Source | Target | Cardinality | Ownership | Integrity Rule |  
| \--- | \--- | \--- | \--- | \--- |  
| PermitCase | Project | 1:1 | case owns | required |  
| PermitCase | JurisdictionResolution | 1:N versioned | case owns historical versions | latest active exactly one |  
| PermitCase | RequirementSet | 1:N versioned | case owns | latest reviewed version exactly one active |  
| PermitCase | ComplianceEvaluation | 1:N versioned | case owns | reviewed before advance |  
| PermitCase | IncentiveAssessment | 1:N versioned | case owns | advisory until reviewed |  
| PermitCase | SubmissionPackage | 1:N versioned | case owns | one current active package |  
| SubmissionPackage | EvidenceArtifact | 1:N | package references | all artifacts resolvable |  
| PermitCase | ReviewDecision | 1:N | case references | immutable once recorded |  
| PermitCase | SubmissionAttempt | 1:N | case owns | attempt numbers monotonic |  
| PermitCase | ContradictionArtifact | 1:N | case references | blocking contradictions must resolve before advance |  
\#\# 8.5 Action Types  
\#\#\# CreateCase  
\- Initiator: authenticated user or trusted intake API  
\- Preconditions: minimum intake payload present; tenant valid  
\- Postconditions success: PermitCase created in INTAKE\_PENDING; audit event emitted  
\- Postconditions failure: no case created; error response and audit attempt event  
\#\#\# ApproveOutput  
\- Initiator: reviewer  
\- Preconditions: reviewed object exists; reviewer authorized; reviewer independence passes or explicit exception artifact exists  
\- Side effects: ReviewDecision created; case may advance if all downstream preconditions met  
\- Forbidden conditions: same-rank blocking contradiction unresolved; stale required evidence; reviewer self-approval on high-risk surface without exception  
\#\#\# SubmitPackage  
\- Initiator: submission service  
\- Preconditions: case state APPROVED\_FOR\_SUBMISSION; active package sealed; manifest and artifact digests valid; support level not UNSUPPORTED  
\- Side effects: SubmissionAttempt created; portal call executed; receipt or failure artifact persisted  
\- Failure postconditions: case remains in bounded pending or manual state; no ambiguous submission state  
\#\#\# DeclareEmergency  
\- Initiator: escalation owner  
\- Preconditions: emergency criteria met; incident record created; declared scope bounded  
\- Side effects: case or subsystem enters EMERGENCY\_HOLD or emergency exception mode  
\- Forbidden conditions: silent skipping of logging, final evidence capture, or retroactive cleanup obligations  
\#\# 8.6 Authority Rules  
\- PermitCase.case\_state writable only by orchestrator runtime with valid transition preconditions.  
\- ReviewDecision writable only by reviewer service.  
\- Policy versions writable only by approved policy mutation workflow.  
\- EvidenceArtifact metadata writable by producing service through evidence registry API.  
\- Observability systems are read-only with respect to authoritative surfaces.  
\#\# 8.7 Invariant Linkage  
This model is consumed by:  
\- planner DAG builder  
\- rule engine  
\- reviewer UI/API  
\- release gate validator  
\- evidence retrieval API  
\- state transition runtime guard  
\- contradiction detector  
\---  

\#\# 8.8 Typed Schema Completion Rule  
Any object referenced by:  
\- requirements  
\- state transitions  
\- runtime guards  
\- release gates  
\- manual fallback policy  
\- external status normalization  
\- audit reconstruction  
\- evidence retrieval  

MUST exist as a typed schema in /model/sps/model.yaml and, where externally or inter-service consumed, as a contract schema in /model/sps/contracts/*.json.  

Objects listed only by “fields include” or “key fields” in this document are explanatory summaries unless and until the corresponding typed schema exists in the binding model export.  

The following objects are mandatory typed schemas in the binding model export for this package version:  
\- Project  
\- JurisdictionResolution  
\- RequirementSet  
\- ComplianceEvaluation  
\- IncentiveAssessment  
\- SubmissionPackage  
\- SubmissionAttempt  
\- ReviewDecision  
\- EvidenceArtifact  
\- ContradictionArtifact  
\- ExternalStatusEvent  
\- ReviewComment  
\- CorrectionTask  
\- ApprovalRecord  
\- InspectionMilestone  
\- ManualFallbackPackage  
\- AuthorityProfile  

Each typed schema MUST define:  
\- required fields  
\- optional fields  
\- enum ownership  
\- nullability rules  
\- immutability rules  
\- versioning rules  
\- compatibility class  
\- authority effect  
\---  
\# 9\. PermitCase State Model  
\#\# 9.1 Initial and Terminal States  
Initial state: DRAFT or INTAKE\_PENDING depending on intake mode.  
Terminal states: CLOSED, CANCELLED.  
Quasi-terminal recovery states: MANUAL\_SUBMISSION\_REQUIRED, EMERGENCY\_HOLD, ROLLED\_BACK.  
\#\# 9.2 Full Transition Table  
| Source State | Event | Initiator | Preconditions | Forbidden Conditions | Evidence Required | Target State | Failure Postcondition |  
| \--- | \--- | \--- | \--- | \--- | \--- | \--- | \--- |  
| DRAFT | case\_created | user/api | minimum intake present | unauthorized tenant | intake request artifact | INTAKE\_PENDING | no case |  
| INTAKE\_PENDING | intake\_completed | intake agent \+ reviewer | normalized project valid | missing required fields | normalized project \+ review decision | INTAKE\_COMPLETE | remain INTAKE\_PENDING or BLOCKED |  
| INTAKE\_COMPLETE | jurisdiction\_started | planner | project approved | missing parcel/address | task graph event | JURISDICTION\_PENDING | remain INTAKE\_COMPLETE |  
| JURISDICTION\_PENDING | jurisdiction\_completed | jurisdiction agent \+ reviewer | authority stack resolved | unresolved geo contradiction | jurisdiction resolution \+ review | JURISDICTION\_COMPLETE | BLOCKED |  
| JURISDICTION\_COMPLETE | research\_started | planner | authority stack current | support metadata stale | task event | RESEARCH\_PENDING | remain JURISDICTION\_COMPLETE |  
| RESEARCH\_PENDING | research\_completed | research agent \+ reviewer | requirements retrieved; freshness valid | same-rank source contradiction unresolved | requirement set \+ review | RESEARCH\_COMPLETE | BLOCKED |  
| RESEARCH\_COMPLETE | compliance\_started | planner | requirement set active | stale rule sources | task event | COMPLIANCE\_PENDING | remain RESEARCH\_COMPLETE |  
| COMPLIANCE\_PENDING | compliance\_completed | compliance agent \+ reviewer | rule evaluation complete | unknown blocking rule unresolved | evaluation \+ review | COMPLIANCE\_COMPLETE | BLOCKED |  
| COMPLIANCE\_COMPLETE | incentives\_started | planner | project and requirement context valid | incentive source freshness invalid | task event | INCENTIVES\_PENDING | remain COMPLIANCE\_COMPLETE |  
| INCENTIVES\_PENDING | incentives\_completed | incentive agent \+ reviewer | assessment complete | stacking contradiction unresolved | incentive assessment \+ review | INCENTIVES\_COMPLETE | BLOCKED |  
| INCENTIVES\_COMPLETE | documents\_started | planner | reviewed data current | missing template coverage | task event | DOCUMENT\_PENDING | remain INCENTIVES\_COMPLETE |  
| DOCUMENT\_PENDING | documents\_completed | document agent \+ reviewer | package assembled; manifest valid | missing attachment or digest mismatch | package \+ manifest \+ review | DOCUMENT\_COMPLETE | BLOCKED |  
| DOCUMENT\_COMPLETE | review\_started | planner | all required upstream reviews exist | stale upstream artifact | review request | REVIEW\_PENDING | remain DOCUMENT\_COMPLETE |  
| REVIEW\_PENDING | block\_issued | reviewer | issue detected | none | review decision | BLOCKED | remain REVIEW\_PENDING |  
| REVIEW\_PENDING | approval\_issued | reviewer | no blocking contradictions, stale artifacts, or missing evidence | reviewer independence failure without exception | review decision | APPROVED\_FOR\_SUBMISSION | remain REVIEW\_PENDING |  
| BLOCKED | correction\_started | planner | block reasons materialized into tasks | no correction plan | correction task set | CORRECTION\_PENDING | remain BLOCKED |  
| CORRECTION\_PENDING | corrected\_package\_ready | reviewer | corrected outputs approved | unresolved prior blocker | new review decision | REVIEW\_PENDING | remain CORRECTION\_PENDING |  
| APPROVED\_FOR\_SUBMISSION | submission\_triggered | planner/system | portal support level supported | package hash changed after approval | submission command | SUBMISSION\_PENDING | remain APPROVED\_FOR\_SUBMISSION |  
| SUBMISSION\_PENDING | submission\_succeeded | adapter | receipt captured | missing receipt correlation | receipt artifact | SUBMITTED | BLOCKED or MANUAL\_SUBMISSION\_REQUIRED |  
| SUBMISSION\_PENDING | submission\_failed\_retryable | adapter | retryable failure class | ambiguous portal acceptance state | failure artifact | RESUBMISSION\_PENDING | remain SUBMISSION\_PENDING after bounded retries |  
| SUBMISSION\_PENDING | unsupported\_workflow\_detected | adapter/operator | unsupported path confirmed | none | ManualFallbackPackage | MANUAL\_SUBMISSION\_REQUIRED | remain SUBMISSION\_PENDING until bounded transition |  
| MANUAL\_SUBMISSION\_REQUIRED | manual\_submission\_recorded | operator \+ reviewer | fallback instructions executed | no external proof | manual receipt evidence \+ review | SUBMITTED | remain MANUAL\_SUBMISSION\_REQUIRED |  
| SUBMITTED | external\_comment\_received | tracking agent | comment correlated | malformed external status | comment artifact | COMMENT\_REVIEW\_PENDING | remain SUBMITTED |  
| SUBMITTED | external\_approval\_received | tracking agent \+ reviewer | approval evidence valid | contradictory external status | approval artifact \+ review | APPROVED | remain SUBMITTED or BLOCKED |  
| COMMENT\_REVIEW\_PENDING | comment\_classified | comment resolution agent | comment parsed | no classification confidence and no operator fallback | classification artifact | CORRECTION\_PENDING | remain COMMENT\_REVIEW\_PENDING |  
| CORRECTION\_PENDING | resubmission\_ready | reviewer | corrected package approved | unresolved comment blocker | package \+ review | RESUBMISSION\_PENDING | remain CORRECTION\_PENDING |  
| RESUBMISSION\_PENDING | resubmitted | adapter/operator | package approved; support valid | package drift after approval | receipt artifact | SUBMITTED | remain RESUBMISSION\_PENDING |  
| APPROVED | close\_case | system/operator | conditions captured; required milestones recorded | missing approval evidence | closure artifact | CLOSED | remain APPROVED |  
| any active | cancel\_case | authorized user/operator | cancellation reason recorded | legal hold preventing purge behavior but not closure | cancellation artifact | CANCELLED | remain prior state |  
| any non-terminal | emergency\_declared | escalation owner | incident exists; criteria met | unauthorized declaration | emergency record | EMERGENCY\_HOLD | remain prior state |  
| EMERGENCY\_HOLD | emergency\_released | escalation owner \+ reviewer | cleanup obligations recorded | no retroactive review plan | emergency cleanup artifact | prior safe state | remain EMERGENCY\_HOLD |  
| any non-terminal | rollback\_triggered | release manager/operator | rollback criteria met | undefined rollback target | rollback artifact | ROLLED\_BACK | remain prior state |  
| ROLLED\_BACK | replay\_authorized | reviewer/release manager | rollback verification passed | unresolved root cause | replay authorization | prior stable state | remain ROLLED\_BACK |  
\#\# 9.3 Disallowed Transitions  
\- REVIEW\_PENDING \-\> SUBMISSION\_PENDING without approval\_issued  
\- any state \-\> SUBMITTED without submission receipt or manual submission proof  
\- BLOCKED \-\> APPROVED\_FOR\_SUBMISSION directly  
\- EMERGENCY\_HOLD \-\> SUBMITTED directly  
\- CLOSED \-\> any active state except through new case creation and linked supersession intent  
\#\# 9.4 Timeout and Escalation Rules  
\- REVIEW\_PENDING \> 2 business days \-\> escalation alert  
\- SUBMISSION\_PENDING \> adapter-specific timeout window \-\> failure classification required  
\- COMMENT\_REVIEW\_PENDING \> 1 business day \-\> operator escalation  
\- EMERGENCY\_HOLD \> 24 hours \-\> mandatory escalation and redesign review trigger  
\---  
\# 10\. Data Flows and Interface Contracts  
\#\# 10.1 API Contract Standards  
Every API or internal event contract MUST define:  
\- schema version  
\- producer  
\- consumer  
\- required fields  
\- optional fields  
\- invalid cases  
\- error classes  
\- idempotency behavior  
\- correlation fields  
\- authority effect  
\- emitted audit fields  
\#\# 10.2 Create Case API  
\*\*POST /api/v1/cases\*\*  
Request:  
\`\`\`json  
{  
  "tenant\_id": "TEN-001",  
  "intake\_mode": "interactive",  
  "project\_description": "Install 500 kW rooftop solar on warehouse with no battery.",  
  "site\_address": {  
    "line1": "100 Example St",  
    "city": "Helena",  
    "state": "MT",  
    "postal\_code": "59601"  
  },  
  "requester": {  
    "name": "Applicant Name",  
    "email": "applicant@example.com"  
  }  
}  
\`\`\`  
Response 201:  
\`\`\`json  
{  
  "case\_id": "CASE-2026-000123",  
  "case\_state": "INTAKE\_PENDING",  
  "audit\_event\_id": "AUD-0001"  
}  
\`\`\`  
\#\# 10.3 Review Decision Contract  
\*\*POST /api/v1/reviews/decisions\*\*  
\`\`\`json  
{  
  "decision\_id": "REV-001",  
  "schema\_version": "1.0",  
  "case\_id": "CASE-2026-000123",  
  "object\_type": "SubmissionPackage",  
  "object\_id": "PKG-004",  
  "decision\_outcome": "ACCEPT\_WITH\_DISSENT",  
  "reviewer\_id": "USR-REVIEW-01",  
  "reviewer\_independence\_status": "PASS",  
  "evidence\_ids": \["ART-010", "ART-011"\],  
  "contradiction\_resolution": "RESOLVED\_WITH\_HIGHER\_RANK\_SOURCE",  
  "dissent\_flag": true,  
  "notes": "Proceed, but portal family migration should be audited during first canary release.",  
  "decision\_at": "2026-03-11T12:00:00Z",  
  "idempotency\_key": "idem-123"  
}  
\`\`\`  
Error cases:  
\- 400 invalid schema  
\- 403 reviewer lacks authority  
\- 409 duplicate idempotency key with non-identical payload  
\- 422 unresolved blocking contradiction or missing required evidence  
\#\# 10.4 Evidence Retrieval API  
\*\*GET /api/v1/evidence/{artifact\_id}\*\*  
Response:  
\`\`\`json  
{  
  "artifact\_id": "ART-010",  
  "artifact\_class": "REQUIREMENT\_EVIDENCE",  
  "linked\_case\_id": "CASE-2026-000123",  
  "linked\_object\_id": "REQSET-002",  
  "authoritativeness": "authoritative",  
  "retention\_class": "CASE\_CORE\_7Y",  
  "checksum": "sha256:abc123",  
  "storage\_uri": "s3://evidence/ART-010.json",  
  "provenance": {  
    "producer": "research-service",  
    "source\_system": "city-code-source",  
    "source\_reference": "HELENA-CODE-SECTION-XYZ"  
  }  
}  
\`\`\`  
SLA: 99% \<= 5 seconds for non-archived artifacts.  
\#\# 10.5 ManualFallbackPackage Contract  
\`\`\`json  
{  
  "manual\_fallback\_package\_id": "MFP-001",  
  "case\_id": "CASE-2026-000123",  
  "package\_id": "PKG-004",  
  "package\_version": "4",  
  "package\_hash": "sha256:...",  
  "reason": "UNSUPPORTED\_PORTAL\_WORKFLOW",  
  "portal\_support\_level": "UNSUPPORTED",  
  "channel\_type": "official\_authority\_email",  
  "proof\_bundle\_state": "PENDING\_REVIEW",  
  "required\_attachments": ["ART-200", "ART-201"],  
  "operator\_instructions": [  
    "Verify package manifest hash.",  
    "Submit via city email channel.",  
    "Upload external proof of submission."  
  ],  
  "required\_proof\_types": ["email\_receipt", "portal\_screenshot", "signed\_receipt\_pdf"],  
  "escalation\_owner": "OPS-ONCALL",  
  "created\_at": "2026-03-11T12:30:00Z"  
}  
\`\`\`  
\#\# 10.6 Submission Adapter Request Contract  
\`\`\`json  
{  
  "submission\_attempt\_id": "SUBATT-001",  
  "case\_id": "CASE-2026-000123",  
  "package\_id": "PKG-004",  
  "manifest\_id": "MAN-004",  
  "target\_portal\_family": "CITY\_PORTAL\_FAMILY\_A",  
  "artifact\_digests": {  
    "ART-300": "sha256:...",  
    "ART-301": "sha256:..."  
  },  
  "idempotency\_key": "submit-CASE-2026-000123-1"  
}  
\`\`\`  
Success response:  
\`\`\`json  
{  
  "submission\_attempt\_id": "SUBATT-001",  
  "outcome": "SUCCESS",  
  "external\_tracking\_id": "HEL-PORTAL-9981",  
  "receipt\_artifact\_id": "ART-RECEIPT-001",  
  "submitted\_at": "2026-03-11T12:45:00Z"  
}  
\`\`\`  
Failure classes:  
\- TRANSIENT\_FAILURE  
\- AUTH\_FAILURE  
\- VALIDATION\_FAILURE  
\- UNSUPPORTED\_WORKFLOW  
\- AMBIGUOUS\_PORTAL\_STATE  
\- TIMEOUT  
\#\# 10.7 Internal Event Envelope  
\`\`\`json  
{  
  "event\_id": "EVT-001",  
  "event\_type": "CASE\_STATE\_CHANGED",  
  "schema\_version": "1.0",  
  "case\_id": "CASE-2026-000123",  
  "object\_type": "PermitCase",  
  "object\_id": "CASE-2026-000123",  
  "actor\_type": "service",  
  "actor\_id": "orchestrator",  
  "correlation\_id": "CORR-001",  
  "causation\_id": "REV-001",  
  "occurred\_at": "2026-03-11T12:46:00Z",  
  "payload": {  
    "from\_state": "REVIEW\_PENDING",  
    "to\_state": "APPROVED\_FOR\_SUBMISSION"  
  }  
}  
\`\`\`  
\---  

\---  
\# 10A. Binding Artifact Contracts  

\#\# 10A.1 Purpose  
The following artifacts are binding where marked in this section. A missing, stale, schema-invalid, or unapproved binding artifact has the failure effect listed here and MUST be enforced by release gates, runtime guards, reviewer checks, or all three where stated.  

\#\# 10A.2 Artifact Contract Matrix  
| Artifact | Canonical Path | Binding | Owner | Generation Authority | Required Fields | Freshness Rule | Validation Rule | Primary Consumers | Failure Effect |  
| \--- | \--- | \--- | \--- | \--- | \--- | \--- | \--- | \--- | \--- |  
| model export | /model/sps/model.yaml | yes | Architecture Lead | approved model generation workflow | model_id, spec_id, spec_version, schema_version, generated_at, object_defs, enum_defs, link_defs, action_defs, authority_rules, compatibility | MUST match current spec version and approved schema set for release | schema validation + compatibility validation + reviewer sign-off | services, release gate, reviewers | release_block |  
| contract schemas | /model/sps/contracts/*.json | yes | Architecture Lead / Platform | approved contract generation workflow | $id, title, version, type, required, properties, additionalProperties rule | MUST match current model export for release | schema validation + contract lint + compatibility checks | services, CI, reviewers | merge_block or release_block depending on surface |  
| invariants index | /invariants/sps/index.yaml | yes | Architecture Lead / Ops | approved invariant registry workflow | spec_version, generated_at, invariant_ids, severities, enforcement_map, test_refs, runtime_guard_refs | MUST match current release bundle | index integrity + referential integrity + test linkage | runtime guards, ops, release gate | release_block |  
| traceability export | /traceability/sps/traceability.yaml | yes | Architecture Lead | approved traceability export workflow | spec_version, generated_at, requirement_map, control_map, test_map, runbook_map, invariant_map, unresolved_gaps | MUST be regenerated for every release candidate | completeness validation with zero blocker gaps | reviewers, release gate, audit | release_block |  
| review artifact | /reviews/sps/*.yaml | yes for gated surfaces | Reviewer | reviewer service only | review_id, reviewed_object_type, reviewed_object_id, outcome, reviewer_id, independence_status, evidence_ids, contradiction_state, created_at | no staleness window; object reviewed MUST still be current at use time | schema validation + object/version match | orchestrator, release gate, audit | review_invalid |  
| dissent artifact | /dissent/sps/*.yaml | yes where dissent exists | Reviewer | reviewer service only | dissent_id, linked_review_id, scope, rationale, required_followup, resolution_state, created_at | active until resolved | schema validation + linked review existence | release gate, audit | release_block where unresolved on high-risk surface |  
| override artifact | /overrides/sps/*.yaml | yes when exception used | Escalation Owner | override workflow only | override_id, scope, justification, start_at, expires_at, affected_surfaces, approver_id, cleanup_required | MUST not be expired at time of use | schema validation + scope validation + duration policy check | runtime guards, governance, audit | release_block or runtime_deny |  
| incident linkage | /incidents/sps/*.yaml | yes for emergency/rollback/security events | Ops / Security | incident workflow only | incident_id, severity, opened_at, linked_cases_or_surfaces, owner, status | active incidents must reflect current state | schema validation + linkage checks | ops, audit, emergency workflow | audit_reconstruction_failure |  
| release bundle manifest | /releases/sps/*/manifest.yaml | yes | Release Manager | release workflow only | release_id, spec_version, app_version, schema_version, model_version, policy_bundle_version, adapter_versions, invariant_pack_version, artifact_digests, approvals, created_at | unique per release candidate | manifest integrity + digest verification + compatibility checks | release manager, audit, rollback | release_block |  
| rollback artifact | /releases/sps/*/rollback.yaml | yes | Release Manager / Ops | rollback workflow only | rollback_id, trigger, target_versions, affected_surfaces, executed_steps, verification_evidence, completed_at | required for every executed rollback and every rehearsal for critical paths | schema validation + evidence linkage | ops, audit | release_block if required and missing |  
| post-release validation report | /releases/sps/*/post-release-validation.yaml | yes | Release Manager / Ops | post-release validation workflow only | release_id, validation_window, checks_executed, check_results, incidents, unresolved_findings, signed_at | MUST be produced for each production rollout stage before next stage | schema validation + required-check completeness | release manager, audit | release_block |  
| emergency record | /overrides/sps/emergency-*.yaml | yes when emergency used | Escalation Owner | emergency workflow only | emergency_id, incident_id, scope, declared_by, started_at, expires_at, allowed_bypasses, forbidden_bypasses, cleanup_due_at | MUST not exceed policy max duration without renewed override | schema validation + scope and duration policy checks | governance, audit, runtime guards | release_block |  
| manual fallback proof bundle | /evidence/sps/manual-fallback/*.yaml | yes when manual path used | Operator + Reviewer | operator workflow plus reviewer validation | bundle_id, case_id, package_id, channel_type, proof_artifact_ids, package_hash, reviewer_validation_id, recorded_at | proof MUST correspond to current approved package version | evidence linkage + sufficiency policy validation | orchestrator, audit | runtime_deny or review_invalid |  

\#\# 10A.3 Binding Interpretation Rule  
Where a binding artifact and normative prose conflict, precedence is determined by the package precedence order in Document Control. Where a non-binding example conflicts with a binding artifact, the example is non-authoritative and MUST be ignored.  

\#\# 10A.4 Freshness Rule for Generated Binding Artifacts  
Generated binding artifacts used in release decisions MUST be regenerated for the specific release candidate unless this package explicitly allows carry-forward use. Carry-forward use is prohibited for:  
\- model export  
\- traceability export  
\- invariants index  
\- release bundle manifest  
\- post-release validation report  

\#\# 10A.5 Required Validation Outcomes  
A binding artifact validation outcome MUST be one of:  
\- VALID  
\- VALID_WITH_WARNING  
\- INVALID_BLOCKING  

Artifacts marked INVALID_BLOCKING MUST prevent merge, review approval, state advancement, or release as specified in the artifact contract matrix.  
\# 11\. Preconditions and Postconditions  
| Operation | Preconditions | Success Postconditions | Failure Postconditions | Rollback / Cleanup |  
| \--- | \--- | \--- | \--- | \--- |  
| CreateCase | Authenticated requester; minimum intake fields | Case created, audit emitted | No case, error response, audit attempt | none |  
| ApproveResearch | RequirementSet exists, freshness valid, contradiction state not blocking | ReviewDecision persisted, state may advance | Case blocked or held, review note recorded | none |  
| GeneratePackage | Upstream reviewed artifacts current | Sealed package \+ manifest created | Package draft remains non-authoritative | delete incomplete drafts, keep failure evidence |  
| SubmitPackage | Approved package, digests valid, support level supported | SubmissionAttempt \+ receipt persisted, state SUBMITTED | Retry or manual fallback state entered | preserve package immutable; no silent resubmission |  
| ResolveComment | Comment classified and remediation plan approved | Correction tasks created and linked | Comment remains pending with escalation | keep original and corrected artifacts versioned |  
| DeclareEmergency | Incident exists, criteria met, owner authorized | Emergency record created, emergency hold or bounded bypass enabled | No emergency change | none |  
| RollbackRelease | Trigger condition met, target version identified | Rollback artifact created, system returned to prior stable version | Remain in incident state, release blocked | verify data and model compatibility |  
\---  
\# 12\. Workflow and Runtime Behavior  
\#\# 12.1 Planner Workflow  
1\. Create case.  
2\. Build task graph from Project shape, jurisdiction, support level, and missing data.  
3\. Route to specialist agents.  
4\. Wait for reviewed outputs before advancing authority-bearing state.  
5\. On comment arrival, create correction branch and resubmission branch.  
Planner does not approve. Planner sequences only.  
\#\# 12.2 Specialist Agent Runtime Rules  
Each specialist agent:  
\- receives versioned inputs  
\- emits typed outputs  
\- emits evidence references  
\- cannot directly mutate PermitCase.case\_state  
\- must classify confidence and unresolved ambiguity  
\- must attach source provenance when retrieval-based  
\#\# 12.3 Reviewer Workflow  
1\. Retrieve pending review object and evidence.  
2\. Validate completeness, freshness, contradictions, and independence.  
3\. Record ACCEPT, ACCEPT\_WITH\_DISSENT, or BLOCK.  
4\. If BLOCK, materialize block reasons into correction tasks.  
5\. If ACCEPT\_WITH\_DISSENT on high-risk surface, apply tightened release conditions.  
\#\# 12.4 Submission Workflow  
1\. Verify active package hash.  
2\. Verify current review approval and no stale artifacts.  
3\. Call adapter with idempotency key.  
4\. Persist receipt or failure artifact.  
5\. Transition to SUBMITTED only on verified proof.  
6\. If unsupported workflow detected, generate ManualFallbackPackage and enter MANUAL\_SUBMISSION\_REQUIRED.  
\#\# 12.5 Tracking Workflow  
1\. Poll or receive webhook.  
2\. Normalize external status into ExternalStatusEvent.  
3\. Correlate with case and submission attempt.  
4\. If status is approval-like, rejection-like, unknown, or contradictory, apply the external status normalization rules in Section 18A before any authority-bearing state change is considered.  
5\. If status includes comments, create ReviewComment artifacts and correction tasks.  
\---  
\# 13\. Error Handling, Retries, Rollback, and Cancellation  
\#\# 13.1 Error Classes  
\- USER\_ERROR  
\- VALIDATION\_ERROR  
\- DEPENDENCY\_FAILURE  
\- TRANSIENT\_FAILURE  
\- PERMANENT\_FAILURE  
\- POLICY\_DENIAL  
\- AUTH\_FAILURE  
\- DATA\_INTEGRITY\_FAILURE  
\- INVARIANT\_VIOLATION  
\- CANCELLATION  
\- TIMEOUT  
\- UNSUPPORTED\_WORKFLOW  
\- AMBIGUOUS\_EXTERNAL\_STATE  
\- STALE\_RULE\_FAILURE  
\- EMERGENCY\_INTERRUPTION  
\#\# 13.2 Retry Policy  
| Error Class | Retryable | Max Attempts | Backoff | Escalation |  
| \--- | \--- | \--- | \--- | \--- |  
| TRANSIENT\_FAILURE | yes | 5 | exponential with jitter | operator after max |  
| TIMEOUT | yes | 3 | bounded exponential | operator if repeated |  
| DEPENDENCY\_FAILURE | conditional | 3 | linear or exponential by adapter | operator \+ incident on sustained failure |  
| VALIDATION\_ERROR | no | 0 | none | correction required |  
| POLICY\_DENIAL | no | 0 | none | reviewer or product/governance decision |  
| AUTH\_FAILURE | no until credentials fixed | 0 | none | security escalation |  
| UNSUPPORTED\_WORKFLOW | no | 0 | none | manual fallback |  
| AMBIGUOUS\_EXTERNAL\_STATE | no auto retry that mutates state | 0 | none | operator investigation |  
\#\# 13.3 Cancellation  
Cancellation closes the case operationally but does not erase evidence. If legal hold is true, purge actions remain prohibited. Cancellation records must include actor, timestamp, reason, and linked artifacts.  
\#\# 13.4 Rollback Mechanics  
Runtime rollback covers release and migration states, not historical permit submission actions already accepted by external authorities. For submission-related rollback, SPS creates corrective follow-up artifacts; it does not pretend an external submission never happened. Rollback safety is determined by the compatibility matrix in Section 26. A release candidate that can restore code but cannot safely restore authority semantics for already-advanced cases is not rollback-safe.  
\---  
\# 14\. Security, Identity, and Authority Boundaries  
\#\# 14.1 Identity Types  
\- end\_user  
\- admin\_user  
\- reviewer  
\- operator  
\- release\_manager  
\- escalation\_owner  
\- service\_principal  
\- external\_system\_proxy  
\#\# 14.2 Authentication Model  
Decision: \*\*native authentication for v1 with OIDC-ready boundary\*\*.  
Rationale:  
\- BUILD\_APPROVED requires a bounded auth decision now.  
\- Native auth reduces initial federation complexity.  
\- Interfaces and policy surfaces remain compatible with later enterprise federation.  
Mandatory controls:  
\- MFA for reviewer, operator, release manager, escalation owner, and admin roles  
\- service principals for internal services  
\- mTLS for service-to-service calls  
\- session risk logging for privileged actions  
\#\# 14.3 Authorization Model  
RBAC plus scoped policy checks. High-risk actions require both role and surface-specific permission.  
\#\# 14.4 Forbidden Actions  
\- specialist agent direct state mutation  
\- observability-triggered automatic policy mutation  
\- reviewer self-approval on high-risk surfaces without emergency exception artifact  
\- deletion of held evidence  
\- release with unresolved blocker contradiction  
\---  
\# 15\. Change Surface Taxonomy  
| Surface | Description | Risk | Required Review |  
| \--- | \--- | \--- | \--- |  
| AUTHORITY\_LOGIC | state transitions, mutation paths, reviewer gates | critical | architecture \+ governance \+ independent reviewer |  
| POLICIES | source ranking, emergency, retention, portal support, incentive coverage | high | domain \+ compliance |  
| SCHEMA | contracts, model, storage schema | high | architecture \+ platform |  
| CONFIG | portal metadata, source metadata, thresholds | medium/high if authority-affecting | admin \+ reviewer |  
| PROMPTS | agent instructions affecting proposal outputs | medium | prompt governance \+ reviewer |  
| OBSERVABILITY | dashboards, alerts, sampling | medium | ops |  
| INFRA\_ONLY | scaling, deployment, networking not altering authority model | medium | ops \+ platform |  
Dissent on AUTHORITY\_LOGIC, POLICIES, or SCHEMA tightens release requirements.  
\---  
\# 16\. Intent Lineage  
Every meaningful change MUST link to an intent artifact:  
\- intent\_id  
\- problem  
\- out\_of\_scope  
\- must\_not  
\- affected\_surfaces  
\- owner  
\- created\_date  
\- lineage: extends, narrows, supersedes, violates  
Example:  
\`\`\`yaml  
intent\_id: INT-SPS-0042  
problem: Add support for portal family B upload-only mode  
out\_of\_scope:  
  \- Auto-payment  
  \- Residential permit support  
must\_not:  
  \- bypass reviewer gate  
  \- change evidence retention classes  
affected\_surfaces:  
  \- AUTHORITY\_LOGIC  
  \- CONFIG  
  \- SCHEMA  
owner: integrations-lead  
created\_date: 2026-03-11  
extends:  
  \- INT-SPS-0010  
narrows: \[\]  
supersedes: \[\]  
violates: \[\]  
\`\`\`  
\---  
\# 17\. Reviewer Independence and Dissent  
\#\# 17.1 High-Risk Surfaces Requiring Independence  
\- authority logic changes  
\- state model changes  
\- portal support classification changes  
\- release gating logic  
\- contradiction resolution on authoritative source conflicts  
\- emergency exceptions affecting approval or submission paths  
\- external status mapping changes that can influence approval, submission, rollback, or closure state  
\- manual fallback proof validation for authority-bearing submission recording  

\#\# 17.2 Measurement Scope  
Reviewer independence metrics apply only to authority-bearing reviews on high-risk surfaces. Low-risk and advisory reviews MUST be excluded from threshold calculations.  

The following dimensions MUST be measured:  
\- author-reviewer pair concentration  
\- reviewer concentration by surface  
\- author concentration by surface  
\- emergency/override-assisted review concentration  
\- same pair recurrence on critical-path objects  

\#\# 17.3 Rolling Window and Denominator  
\- default rolling window: 90 days  
\- denominator: all completed authority-bearing high-risk reviews in the window  
\- repeated pair frequency = count of high-risk reviews where the same primary author and primary reviewer pair appear / denominator  
\- critical-path repeated pair frequency = count of high-risk reviews affecting AUTHORITY_LOGIC, POLICIES, SCHEMA, release gating, status mapping, or manual proof validation using the same pair / denominator for critical-path reviews  
\- resubmission reviews count separately if they approve a distinct object version  

\#\# 17.4 Thresholds  
General high-risk threshold:  
\- <= 25% repeated same author-reviewer pair frequency: pass  
\- > 25%: warning and dashboard alert  
\- > 35%: release escalation required  
\- > 50%: blocker pending redesign review  

Critical-path threshold:  
\- <= 20% repeated same author-reviewer pair frequency: pass  
\- > 20%: warning  
\- > 30%: release escalation required  
\- > 40%: blocker pending redesign review  

Emergency or override-assisted threshold:  
\- any repeated emergency-assisted use by the same pair on the same surface more than once in 30 days triggers mandatory redesign review  
\- any emergency-assisted approval by the same pair above 10% of high-risk review volume in a rolling 90 days is a blocker  

\#\# 17.5 Small-Team Exception Rules  
Small-team pressure does not waive independence. Where staffing makes normal independence impossible:  
\- an explicit override artifact is required  
\- a second-look review MUST occur within 2 business days by a different qualified reviewer  
\- the exception MUST be tagged in review metrics exports  
\- repeated use on the same surface within 30 days is a blocker pending staffing or workflow redesign  

\#\# 17.6 Dissent Rules  
\- ACCEPT_WITH_DISSENT on high-risk surfaces requires a second independent reviewer or explicit escalation-owner override  
\- BLOCK stops advancement immediately  
\- dissent is preserved indefinitely with linked resolution artifact  
\- unresolved dissent on AUTHORITY_LOGIC, POLICIES, SCHEMA, release gating, external status mapping, or manual submission proof validation is release-blocking  

\#\# 17.7 Export and Audit Requirements  
Each release candidate MUST include a reviewer independence metrics export containing:  
\- rolling window  
\- denominator counts  
\- pair-frequency table  
\- critical-path pair-frequency table  
\- emergency-assisted review counts  
\- exceptions with linked override artifacts  
\- blocker determination  
\---  
\# 18\. Contradiction Handling and Source Ranking  
\#\# 18.1 Source Ranking  
1\. Direct AHJ portal instructions or receipts for the specific case  
2\. Current official AHJ published permit instructions/forms  
3\. Official state statutes, regulations, or code agency publications  
4\. Official utility tariffs/program rules  
5\. Official local incentive or financing program administrators  
6\. Official federal program sources  
7\. Approved commercial aggregators used only as advisory acceleration sources  
\#\# 18.2 Contradiction Rules  
\- Higher-ranked source overrides lower-ranked source, but contradiction artifact is still recorded if lower-ranked source influenced any draft output.  
\- Same-rank contradiction is blocking until reviewer resolution.  
\- If official source freshness cannot be established, resulting requirement set is STALE and cannot auto-advance.  
\#\# 18.3 Contradiction Artifact Schema  
\`\`\`json  
{  
  "contradiction\_id": "CON-001",  
  "case\_id": "CASE-2026-000123",  
  "scope": "permit\_requirement",  
  "source\_a": "official\_city\_form\_page",  
  "source\_b": "official\_city\_fee\_schedule\_pdf",  
  "ranking\_relation": "same\_rank",  
  "blocking\_effect": true,  
  "resolution\_status": "OPEN"  
}  
\`\`\`  
\---  

\---  
\# 18A. Freshness Policy and External Status Normalization  

\#\# 18A.1 Freshness Policy by Source Type  
Freshness is an authority property, not a cache property. The system MUST evaluate both source freshness and retrieval freshness.  

| Source Type | Freshness Requirement | Failure Result |  
| \--- | \--- | \--- |  
| direct case-specific portal instruction or receipt | must correspond to the active case and active package or active submission attempt | INVALIDATED |  
| official AHJ forms/instructions | must be checked nightly for configured jurisdictions and revalidated at review time if older than 7 days | STALE |  
| official statutes/regulations/code publications | must be checked nightly and revalidated if ingestion metadata is older than 7 days | STALE |  
| utility program or interconnection rules | must be checked nightly and revalidated if older than 7 days | STALE |  
| local/state/federal incentive program sources | must be checked nightly and revalidated if older than 3 days during active incentive evaluation | STALE |  
| approved commercial aggregators | advisory only; never sufficient alone for authority-bearing advancement | advisory_only |  

If official source freshness cannot be established, the resulting RequirementSet or IncentiveAssessment MUST be marked STALE and cannot auto-advance.  

\#\# 18A.2 Canonical Internal Status Vocabulary  
External statuses MUST normalize only into the following internal status classes:  
\- RECEIVED_UNCONFIRMED  
\- RECEIVED_CONFIRMED  
\- IN_REVIEW  
\- COMMENT_ISSUED  
\- RESUBMISSION_REQUESTED  
\- APPROVAL_REPORTED  
\- APPROVAL_CONFIRMED  
\- REJECTION_REPORTED  
\- WITHDRAWN_REPORTED  
\- CLOSED_REPORTED  
\- UNKNOWN_EXTERNAL_STATUS  
\- CONTRADICTORY_EXTERNAL_STATUS  

These classes do not themselves mutate PermitCase state unless the rules below permit it.  

\#\# 18A.3 Status Mapping Ownership  
Each adapter family MUST have a versioned status mapping file under reviewed configuration control. The mapping file MUST define:  
\- external raw status value  
\- normalized internal status class  
\- confidence level  
\- allowed case states  
\- auto-advance eligibility  
\- mandatory evidence requirements  
\- reviewer-confirmation requirement  
\- contradiction triggers  

Unmapped external statuses MUST normalize to UNKNOWN_EXTERNAL_STATUS and MUST fail closed.  

\#\# 18A.4 Confidence Policy  
Confidence levels:  
\- HIGH: direct case-correlated source with deterministic mapping  
\- MEDIUM: known mapped source with minor ambiguity  
\- LOW: partial or ambiguous source input  
\- NONE: unmapped or contradictory source input  

Rules:  
\- LOW or NONE confidence MUST prevent auto-advance  
\- MEDIUM confidence may update tracking views but not authority-bearing case state without reviewer confirmation  
\- HIGH confidence may still not auto-advance into APPROVED, CLOSED, or any approval-equivalent case state without required evidence and reviewer confirmation where this package requires it  

\#\# 18A.5 No-Auto-Advance States  
No external status event may directly mutate PermitCase into:  
\- APPROVED  
\- CLOSED  
\- CANCELLED  
\- ROLLED_BACK  
\- any state implying final authority recognition  

External status events may directly create tracking artifacts. They may only support case-state advancement through the orchestrator after evidence checks, contradiction checks, and reviewer approval where required.  

\#\# 18A.6 Contradictory Status Handling  
The following MUST normalize to CONTRADICTORY_EXTERNAL_STATUS:  
\- two active approval/rejection-like signals for the same submission attempt  
\- approval-like signal with unresolved comment or deficiency signal  
\- status referring to a different package version or tracking ID than the active submission attempt  
\- approval-like signal lacking minimum proof defined in the evidence policy  

CONTRADICTORY_EXTERNAL_STATUS is blocking and MUST create:  
\- ExternalStatusEvent artifact  
\- ContradictionArtifact  
\- operator alert  
\- reviewer task  

\#\# 18A.7 Minimum Evidence for Approval-Reported External Status  
An approval-reported external status may support reviewer confirmation only if at least one of the following exists:  
\- authoritative portal approval page or downloadable notice tied to the case  
\- official email or signed communication from the authority with matching case identifiers  
\- official utility approval artifact with matching submission tracking ID  

Absent such proof, the event remains APPROVAL_REPORTED and MUST NOT promote to APPROVAL_CONFIRMED.  

\#\# 18A.8 Tracking Workflow Rule  
Tracking views may show external normalized status immediately. Authoritative case-state mutation MUST remain governed by orchestrator transition checks, evidence sufficiency checks, contradiction handling, and reviewer decisions.  
\# 19\. Clarifications Register \- Closed Decisions  
| ID | Final Decision |  
| \--- | \--- |  
| C-001 | Incentive sources use official federal, state, utility, and local program sources as authority. Approved aggregators are advisory only. |  
| C-002 | Initial adapter scope supports two portal families plus bounded unsupported-case handling. |  
| C-003 | Reviewer independence required on high-risk surfaces; small-team exceptions require explicit emergency or override artifact and second-look follow-up. |  
| C-004 | Emergency requires incident linkage, authorized declaration, bounded scope, and 24h maximum active duration absent renewed override. |  
| C-005 | Rule ingestion cadence: nightly checks for configured jurisdictions, immediate stale-state if freshness window exceeded. |  
| C-006 | Native auth only in v1 with OIDC-ready boundary for later federation. |  
| C-007 | Seven-year default retention, jurisdictional override support, and legal-hold supersession. |  
| C-008 | Production prompts are versioned, reviewed, redaction-controlled, and cannot silently mutate authority rules. |  
| C-009 | This package is US-only. Internationalization is explicitly out of scope. |  
| C-010A | SPS outputs estimated fees as advisory until authoritative portal or official schedule confirmation is captured. |  
| C-010B | Payment processing is out of scope in v1. |  
| C-011 | SPS compliance profile is Tier 3 in this package. |  
| C-012 | Same-rank contradictions block advancement; source ranking is explicit. |  
| C-013 | Unsupported workflows enter MANUAL\_SUBMISSION\_REQUIRED with ManualFallbackPackage. |  
| C-014 | Evidence retrieval SLA is 99% \<= 5s for non-archived artifacts and all binding evidence uses stable IDs. |  
\---  
\# 20\. Invariant Registry  
| Invariant ID | Severity | Statement | Prevention | Detection | Runtime Guard | Owner |  
| \--- | \--- | \--- | \--- | \--- | \--- | \--- |  
| INV-001 | critical | No case may enter APPROVED\_FOR\_SUBMISSION without a valid review decision for the active package. | reviewer gate | audit query | orchestrator state guard | governance |  
| INV-002 | critical | No case may enter SUBMITTED without verified external proof or manual proof artifact. | submission adapter validation | receipt reconciliation | submission guard | platform |  
| INV-003 | critical | Same-rank authoritative contradiction must block auto-advance. | contradiction detector | review queue metrics | state guard | compliance |  
| INV-004 | critical | Legal hold prevents purge or destructive delete of bound evidence. | retention service | purge audit jobs | storage guard | compliance |  
| INV-005 | high | Observability outputs may not mutate authoritative state. | network and auth separation | audit anomaly detection | API auth guard | security |  
| INV-006 | high | Emergency exceptions cannot remain active past allowed duration without renewed override. | emergency timer | dashboard alerts | orchestrator timer guard | ops |  
| INV-007 | high | Every active package manifest digest must match referenced artifact digests at submission time. | package sealing | digest verification logs | submission preflight guard | document service |  
| INV-008 | high | Reviewer self-approval on high-risk surface is prohibited absent exception artifact. | reviewer policy | metrics and review audit | review API guard | governance |  
\---  

\---  
\# 20A. Guard Placement Matrix  

\#\# 20A.1 Purpose  
The following matrix binds control intent to concrete runtime enforcement locations. Review-only, CI-only, or documentation-only enforcement is insufficient for these surfaces.  

| Control ID | Protected Surface | Forbidden or Required Condition | Enforcing Component | Enforcing Endpoint/Event/Handler | Fail Mode | Denial Audit Event | Linked Invariant |  
| \--- | \--- | \--- | \--- | \--- | \--- | \--- | \--- |  
| CTL-01A | PermitCase state mutation | specialist agent direct state mutation forbidden | orchestrator API | case state mutation handlers | fail closed | CASE_MUTATION_DENIED | INV-SPS-STATE-001 |  
| CTL-01B | reviewer gate | no advancement into submission-bearing states without valid ReviewDecision | orchestrator runtime | approval transition handler | fail closed | APPROVAL_GATE_DENIED | INV-SPS-STATE-002 |  
| CTL-03A | requirement freshness | stale or unknown-freshness RequirementSet cannot auto-advance | orchestrator runtime | research_complete and compliance_start handlers | fail closed | STALE_REQUIREMENTSET_DENIED | INV-SPS-RULE-001 |  
| CTL-05A | package integrity | package hash or manifest drift after approval forbidden | submission service | submit package preflight | fail closed | PACKAGE_DIGEST_MISMATCH_DENIED | INV-SPS-PKG-001 |  
| CTL-06A | submission recording | no SUBMITTED state without verified receipt or validated manual proof | orchestrator runtime | submission_succeeded and manual_submission_recorded handlers | fail closed | SUBMISSION_PROOF_DENIED | INV-SPS-SUB-001 |  
| CTL-07A | external status mapping | unmapped or contradictory external status cannot auto-advance | tracking normalizer + orchestrator | external_status_ingested handler | fail closed | EXTERNAL_STATUS_ADVANCE_DENIED | INV-SPS-TRACK-001 |  
| CTL-07B | approval normalization | approval-reported external status requires proof sufficiency and reviewer confirmation where applicable | orchestrator runtime | external_approval_received handler | fail closed | EXTERNAL_APPROVAL_DENIED | INV-SPS-TRACK-002 |  
| CTL-09A | approval record creation | ApprovalRecord requires linked approval evidence and reviewer confirmation where required | tracking/reviewer service | approval record creation handler | fail closed | APPROVAL_RECORD_DENIED | INV-SPS-APPROVAL-001 |  
| CTL-10A | evidence retrieval | missing stable-ID evidence on binding surfaces blocks release/review | evidence API + release gate | evidence retrieval and release validation | fail closed | EVIDENCE_RESOLUTION_DENIED | INV-SPS-EVID-001 |  
| CTL-11A | reviewer independence | independence threshold failure blocks high-risk approval unless valid override exists | reviewer service | review decision creation | fail closed | REVIEW_INDEPENDENCE_DENIED | INV-SPS-REV-001 |  
| CTL-13A | emergency scope | emergency bypass outside declared scope forbidden | orchestrator runtime | emergency-bypass-eligible handlers | fail closed | EMERGENCY_SCOPE_DENIED | INV-SPS-EMERG-001 |  
| CTL-14A | contradiction handling | same-rank blocking contradiction forbids advancement | orchestrator runtime | all advancement handlers on governed surfaces | fail closed | CONTRADICTION_ADVANCE_DENIED | INV-SPS-CONTRA-001 |  

\#\# 20A.2 Enforcement Allocation Rule  
Each runtime guard listed here MUST have:  
\- linked invariant  
\- linked negative test  
\- linked audit event schema  
\- owner  
\- monitored alert path if repeated denial occurs  

\#\# 20A.3 Guard Failure Escape Rule  
If a release or runtime incident shows a listed guard failed open on a critical path, BUILD_APPROVED status for the affected surface is revoked until:  
\- root cause is identified  
\- guard is repaired  
\- regression test is added  
\- rollback or containment evidence is completed  
\# 21\. Incident Registry Model  
Incident fields:  
\- incident\_id  
\- severity  
\- subsystem  
\- summary  
\- detection\_source  
\- linked\_invariants\[\]  
\- linked\_case\_ids\[\]  
\- blast\_radius  
\- mitigation\_status  
\- owner  
\- analysis\_events\[\]  
\- opened\_at  
\- resolved\_at  
Incident severities: SEV1, SEV2, SEV3, SEV4.  
SEV1 examples:  
\- unauthorized submission path  
\- evidence retrieval outage affecting release or audit  
\- silent contradiction bypass  
\- legal-hold purge risk  
\---  
\# 22\. Enforcement Allocation and Control-Core Summary  
| Control ID | Protected Path | Authoritative State Holder | Allowed Mutation Path | Prevention | Detection | Runtime Guard | Release Gate | Rollback Trigger | Owner |  
| \--- | \--- | \--- | \--- | \--- | \--- | \--- | \--- | \--- | \--- |  
| CTL-01 | reviewed state advancement | PermitCase | reviewer \-\> orchestrator | review API validation | audit queries | state transition guard | yes | invalid transition detected | governance |  
| CTL-02 | jurisdiction authority resolution | JurisdictionResolution | reviewed agent output \-\> orchestrator | geo conflict validation | contradiction metrics | freshness and support-level guard | yes | stale authority map | research |  
| CTL-03 | requirement provenance | RequirementSet | reviewed retrieval output | source ranking validation | evidence audits | contradiction/staleness guard | yes | invalidated requirements | research |  
| CTL-04 | compliance integrity | ComplianceEvaluation | reviewed rule output | rule freshness checks | stale-rule dashboards | evaluation guard | yes | stale rules or unresolved unknown blocker | compliance |  
| CTL-05 | package sealing | SubmissionPackage | document service \-\> reviewer \-\> orchestrator | manifest hashing | digest mismatch logs | package preflight guard | yes | hash mismatch | document |  
| CTL-06 | submission control | SubmissionAttempt | approved package \-\> adapter | idempotency and support checks | receipt reconciliation | submission guard | yes | ambiguous external state | submission |  
| CTL-07 | post-submit status ingestion | ExternalStatusEvent | tracking normalization | correlation validation | unmapped status alerts | status mapping guard | yes for approval states | contradictory status | tracking |  
| CTL-08 | resubmission correction loop | CorrectionTask set | blocked review \-\> planner \-\> reviewer | block reason materialization | correction backlog metrics | resubmission preflight guard | yes | unresolved comment blockers | comment resolution |  
| CTL-09 | approval recording | ApprovalRecord | tracking/reviewer | approval proof validation | approval mismatch alerts | final-approval guard | yes | invalid approval evidence | tracking |  
| CTL-10 | queryable evidence | EvidenceArtifact | evidence registry API | stable ID requirement | retrieval SLA monitors | retrieval auth/metadata guard | yes | retrieval failure sustained | platform |  
| CTL-11 | reviewer independence | ReviewDecision | reviewer API | author-reviewer pair policy | metrics dashboards | review authorization guard | yes on thresholds | repeated pair threshold breach | governance |  
| CTL-12 | dissent tightening | ReviewDecision \+ release pipeline | reviewer \-\> release manager | release policy checks | dissent backlog dashboards | release pipeline gate | yes | unresolved dissent on high-risk surface | governance |  
| CTL-13 | exception anti-normalization | Override/Emergency records | escalation workflow | max duration and renewal rules | exception usage dashboards | emergency timer guard | yes | repeated exception threshold | governance |  
| CTL-14 | contradiction block | ContradictionArtifact | detector \-\> reviewer | ranking rules | contradiction queue metrics | auto-advance guard | yes | unresolved contradiction | compliance |  
Control sufficiency rule: for every critical control above, review-only or CI-only enforcement is insufficient. Each has runtime guards because the failure remains runtime-reachable.  
\---  
\# 23\. Observability and Audit Semantics  
\#\# 23.1 Required Audit Fields  
\- event\_id  
\- event\_type  
\- case\_id  
\- object\_type  
\- object\_id  
\- actor\_type  
\- actor\_id  
\- correlation\_id  
\- causation\_id  
\- timestamp  
\- result  
\- evidence\_ids\[\]  
\#\# 23.2 Dashboards  
\- Case funnel and time-in-state  
\- Review backlog and independence metrics  
\- Unsupported portal case count  
\- Contradiction queue  
\- Evidence retrieval latency and failure rate  
\- Emergency exception dashboard  
\- Release health dashboard  
\#\# 23.3 Alerts  
\- evidence retrieval p99 \> 5s  
\- SUBMISSION\_PENDING timeout breaches  
\- EMERGENCY\_HOLD approaching expiration  
\- same-rank contradiction backlog \> threshold  
\- reviewer independence threshold breach  
\- digest mismatch on submission preflight  
\---  
\# 24\. Testing and Conformance Validation  
Required test classes:  
\- unit tests for contract validation and state guards  
\- integration tests for planner, review, submission, and tracking loops  
\- end-to-end tests for automated and manual submission paths  
\- schema validation tests  
\- contradiction handling tests  
\- stale-rule tests  
\- authority-boundary negative tests  
\- release-gate bypass tests  
\- rollback rehearsal tests  
\- evidence queryability SLA tests  
\- chaos tests for external dependency failures  
Conformance proof requires:  
\- passing CI suite  
\- current traceability export  
\- no blocker incidents open on affected surfaces  
\- release bundle completeness  
\- rollback rehearsal evidence current for release line  
\---  
\# 25\. CI and Merge Authorization  
The governance pipeline sequence is:  
1\. spec validation  
2\. schema validation  
3\. model export freshness check  
4\. traceability coverage check  
5\. surface classification check  
6\. invariant compatibility check  
7\. reviewer independence metrics evaluation where applicable  
8\. governance policy evaluation  
9\. merge authorization artifact issuance  
Blocking conditions:  
\- missing binding artifact  
\- stale generated binding artifact  
\- unresolved blocker contradiction  
\- failed runtime guard tests  
\- release-gate bypass test failure  
\- missing rollback rehearsal evidence for affected critical paths  
\---  
\# 26\. Release, Rollout, Migration, and Rollback  
\#\# 26.1 Release Prerequisites  
\- approved code changes  
\- current spec version reference  
\- current model export  
\- traceability report  
\- control-core summary  
\- runbook updates  
\- release bundle manifest  
\- rollback plan  
\- rollback rehearsal evidence  
\- unresolved dissent disposition  
\- no blocker contradictions  
\#\# 26.2 Rollout Stages  
1\. staging validation  
2\. canary deployment  
3\. limited production cohort  
4\. full production rollout  
\#\# 26.3 Rollback Triggers  
\- invariant violation on critical path  
\- submission path ambiguity  
\- evidence retrieval failure impacting review/release/audit  
\- schema compatibility failure  
\- sustained security/auth failure on privileged paths  
\#\# 26.4 Rollback Rules  
\- release manager owns rollback execution  
\- ops validates service health restoration  
\- reviewer/governance validates no authority drift occurred  
\- rollback artifact MUST capture trigger, executed steps, affected versions, verification evidence  
\---  
\# 27\. Emergency Path  
\#\# 27.1 Emergency Criteria  
Emergency exists only when one of the following is true:  
\- authority-bearing workflow is blocked or unsafe and normal mitigation cannot restore safe service quickly  
\- a security incident threatens privileged access or evidence integrity  
\- evidence or state integrity is at risk  
\- external dependency failure creates sustained inability to safely progress or contain cases through normal paths  
\#\# 27.2 What May Be Skipped  
Only the following may be conditionally bypassed under emergency with explicit artifact:  
\- reviewer independence check in narrowly scoped cases  
\- staged rollout pacing for rollback or containment actions  
\- normal queue ordering  
\#\# 27.3 What May Never Be Skipped  
\- audit logging  
\- evidence capture  
\- explicit authorization for authority-bearing mutation  
\- incident linkage  
\- retroactive cleanup obligations  
\#\# 27.4 Duration and Cleanup  
\- max active duration: 24 hours  
\- cleanup artifact due within 4 hours of emergency end  
\- repeated emergency use on same surface within 30 days triggers mandatory redesign review  
\---  
\# 28\. Runbooks  
\#\# 28.1 Unsupported Portal Manual Fallback Runbook  
Trigger:  
\- adapter returns UNSUPPORTED_WORKFLOW  
\- portal support metadata = UNSUPPORTED  
\- operator confirms configured portal family does not support the required submission path  
\- automated submission enters ambiguous state and fallback is explicitly approved by operator escalation path  

Required diagnostics:  
\- case_id  
\- active package_id  
\- active package_version  
\- manifest_id  
\- package digest verification result  
\- portal support metadata version  
\- adapter logs  
\- current review decision id  
\- current contradiction state  
\- current release profile  

Actions:  
1\. Verify active package hash, manifest digest, and review decision still match the current package version.  
2\. Generate ManualFallbackPackage.  
3\. Determine fallback channel type:  
   \- authoritative portal upload-only remainder  
   \- official authority email channel  
   \- official mailed or in-person submission path  
   \- utility-specific manual intake path  
4\. Execute only the documented channel-specific fallback instructions for that authority.  
5\. Capture channel-appropriate proof artifacts.  
6\. Bind proof to the approved package hash.  
7\. Submit proof bundle for reviewer validation.  
8\. Transition case only after reviewer validates proof sufficiency.  

Forbidden actions:  
\- manually marking SUBMITTED without validated proof bundle  
\- modifying package contents after reviewer approval without new review  
\- mixing proof from different package versions  
\- treating operator notes alone as sufficient proof  
\- treating a generic sent-email screenshot without authority correlation as sufficient proof  

\#\# 28.1.1 Channel-Specific Proof Sufficiency Policy  
| Channel Type | Minimum Proof Set | Insufficient Proof Examples | Allowed State After Operator Action |  
| \--- | \--- | \--- | \--- |  
| portal upload with confirmation page | confirmation page or official receipt artifact + package hash binding | local browser screenshot without case identifiers | SUBMITTED after reviewer validation |  
| official authority email channel | sent message artifact + delivery evidence or reply from authority + package hash binding + matched recipient address | unsent draft, screenshot without recipient, email lacking package binding | SUBMISSION_PENDING_VERIFICATION until reviewer validation, then SUBMITTED |  
| mailed or in-person filing | signed receipt, stamped intake copy, or official acceptance record + package hash binding | shipping label alone, operator declaration alone | SUBMISSION_PENDING_VERIFICATION until reviewer validation, then SUBMITTED |  
| utility manual intake | official utility acknowledgement with matching tracking or case identifiers + package hash binding | internal notes or call summary without official acknowledgement | SUBMISSION_PENDING_VERIFICATION until reviewer validation, then SUBMITTED |  

\#\# 28.1.2 Proof Bundle Requirements  
The manual fallback proof bundle MUST include:  
\- bundle_id  
\- case_id  
\- package_id  
\- package_version  
\- package_hash  
\- channel_type  
\- proof_artifact_ids  
\- operator_id  
\- recorded_at  
\- reviewer_validation_id once validated  

\#\# 28.1.3 Closure Evidence  
\- ManualFallbackPackage  
\- proof bundle  
\- reviewer validation decision  
\- state change audit event  
\- contradiction artifact if any proof ambiguity was encountered  
\#\# 28.2 Submission Failure Runbook  
Trigger:  
\- submission adapter returns retryable or ambiguous failure  
Actions:  
1\. Classify failure.  
2\. Retry only if class allows.  
3\. If ambiguous external state, stop automatic retries.  
4\. Create incident if ambiguity persists.  
5\. Require operator investigation.  
\#\# 28.3 Stale Rule Runbook  
Trigger:  
\- rule freshness expired or authoritative source unavailable  
Actions:  
1\. Mark RequirementSet or ComplianceEvaluation stale.  
2\. Block advancement.  
3\. Notify domain owner.  
4\. Refresh source or escalate contradiction.  
\#\# 28.4 Emergency Declaration Runbook  
Trigger:  
\- SEV1 or bounded SEV2 that meets emergency criteria  
Actions:  
1\. Open incident.  
2\. Confirm criteria.  
3\. Declare emergency with scope, owner, and duration.  
4\. Apply only allowed bypasses.  
5\. Maintain evidence and logging.  
6\. Exit and complete cleanup artifact.  
\#\# 28.5 Release Rollback Runbook  
Trigger:  
\- release rollback criteria met  
Actions:  
1\. Freeze further rollout.  
2\. Execute rollback steps.  
3\. Verify service, model, and evidence retrieval health.  
4\. Record rollback artifact.  
5\. Decide replay or hold.  
\---  
\# 29\. Artifact Applicability Matrix  
| Artifact | Required By | Authoritative | Consumer | Failure if Missing |  
| \--- | \--- | \--- | \--- | \--- |  
| spec.md | Tier 3 / pre-release | yes | builders, reviewers, release | release\_block |  
| model.yaml | Tier 3 / authority-bearing | yes | planner, runtime guards, release | release\_block |  
| traceability.yaml | Tier 3 / pre-release | yes | CI, reviewers | merge\_block |  
| invariants index | Tier 3 | yes | runtime guards, ops | release\_block |  
| incident linkage | Tier 3 / prod authority | yes | ops, audit | audit\_reconstruction\_failure |  
| runbooks | operator-critical paths | yes for emergency/release, otherwise operational | operators | operator\_execution\_degraded |  
| review artifacts | approval gates | yes | orchestrator, audit | review\_invalid |  
| dissent artifacts | high-risk surfaces | yes | release, audit | release\_block |  
| override artifacts | emergency or exception | yes | governance, audit | release\_block |  
| release bundle manifest | pre-release/release | yes | release manager | release\_block |  
| post-release validation report | release | yes | release manager, audit | release\_block |  
\---  
\# 30\. Repo Wiring  
\`\`\`  
/specs/sps/build-approved/spec.md  
/specs/sps/build-approved/plan.md  
/specs/sps/build-approved/tasks.md  
/specs/sps/build-approved/clarifications.md  
/model/sps/model.yaml  
/model/sps/contracts/\*.json  
/invariants/sps/index.yaml  
/invariants/sps/INV-\*/invariant.yaml  
/incidents/sps/\*.yaml  
/reviews/sps/\*.yaml  
/dissent/sps/\*.yaml  
/overrides/sps/\*.yaml  
/waivers/sps/\*.yaml  
/traceability/sps/traceability.yaml  
/runbooks/sps/\*.md  
/observability/sps/\*.yaml  
/releases/sps/\*  
/diagrams/sps/\*.mmd  
\`\`\`  
\---  
\# 31\. BUILD\_APPROVED Verdict Record  
\#\# 31.1 Closed Blockers  
Closed in this package:  
\- incomplete PermitCase state machine  
\- narrative-only emergency handling  
\- unresolved unsupported portal behavior  
\- missing evidence retrieval contract  
\- unresolved clarification register  
\- missing control-core summary  
\- insufficient runtime guard mapping  
\- incomplete release and rollback boundaries  
\- incomplete contradiction handling  
\#\# 31.2 Remaining Risks That Do Not Revoke BUILD\_APPROVED  
These are implementation risks, not specification blockers:  
\- adapter-specific portal quirks still require per-family implementation and test evidence  
\- jurisdiction content breadth expands over time and requires ongoing data operations  
\- incentive program churn requires disciplined source freshness operations  
\#\# 31.3 Conditions That Revoke BUILD\_APPROVED  
BUILD\_APPROVED is revoked if any of the following become true without approved package update:  
\- release path changes without updated controls and tests  
\- new portal family added without support classification and runbook coverage  
\- evidence retrieval ceases to be queryable by stable IDs  
\- emergency exception use becomes normalized without redesign review  
\- implementation introduces direct specialist-agent mutation of PermitCase state  
