Standing Framework — Canonical Spec Package Instructions  
Version: 1.3  
Status: Canonical instruction set  
Purpose: Define the mandatory standard for producing complete, execution-grade spec packages for any project under Standing Framework.

## **1\. Non-negotiable purpose**

A spec package is a normative execution contract.

It is not a brainstorm, not a design memo, and not a product brief. Explanatory material may exist, but it is non-authoritative unless explicitly marked otherwise.

A canonical spec package must be complete enough that:

* builders can implement from it without guessing about authority-bearing behavior  
* reviewers can block against it using artifact-backed objections  
* operators can run it using the package and its runbooks  
* release managers can determine exact gating conditions  
* auditors can reconstruct intent, review, dissent, incident history, and release decisions from durable artifacts rather than memory or informal explanation

Standing Framework treats intent, review, release, observation, invariants, dissent, rollback, and authority boundaries as first-class execution concerns rather than after-the-fact governance theater.

If speed and discipline conflict, the system is wrong, not the developer. The package must optimize for buildability, authority safety, auditability, explicitness, maintainability, and operational clarity.

## **2\. Core stance**

Every meaningful change must be explainable through artifacts, not just diffs.

At minimum:

* every authority-bearing behavior must be explicit  
* every critical runtime claim must be enforced or durably disproven at a control point whose placement is sufficient for the actual runtime risk  
* every review and release decision must leave durable evidence  
* every production safety property must be mechanically enforced where runtime failure could violate it  
* every override of normal process must be narrow, explicit, time-bounded, and auditable  
* every required artifact must justify its existence through implementation, enforcement, operation, review, release, or audit value

Standing Framework preserves these rules:

* AI output is always a proposal, never authority  
* review is a permission gate, not style commentary  
* passing tests does not equal permission to release  
* production observation must not become self-modification  
* dissent must be preserved, not socially erased  
* time-based obligations cannot rely on CI alone; they require authoritative backend enforcement  
* documentation volume is not evidence of control sufficiency

## **3\. Definitions for enforcement**

The following definitions are binding for package evaluation.

**Authority-bearing behavior**  
Any behavior that can directly mutate authoritative state, approve or deny such mutation, alter policy execution, alter release permission, modify review rights, or change required decision rights.

**Meaningful change**  
Any change that affects authority logic, state transitions, interfaces, invariants, policies, release criteria, rollback behavior, operational obligations, observability required for production decision-making, or audit reconstruction.

**Critical runtime claim**  
Any claim whose falsity could cause unsafe mutation, policy bypass, release error, audit failure, integrity loss, hidden drift, incident escalation delay, or inability to reconstruct system behavior.

**High-risk surface**  
Any change surface where failure can alter authority, policy, security posture, release permission, data integrity, regulated behavior, or broad operational outcomes.

**Mechanically enforced**  
Enforced by a deterministic system, validator, gate, policy engine, runtime guard, or other control point that can prevent, block, or durably surface violation without relying primarily on human memory, voluntary compliance, or discretionary review.

**Control point**  
A specific place where a rule is prevented, detected, gated, audited, or remediated.

**Authoritative artifact**  
An artifact explicitly designated as normative for a given control, decision, or enforcement outcome, where at least one declared consumer or gate normatively depends on it.

**Generated artifact**  
An artifact derived reproducibly from declared authoritative inputs.

**Contradiction**  
A condition in which two normative artifacts, or a normative artifact and live runtime behavior, express materially incompatible meanings for the same control, interface, state rule, or authority path.

**Compliance profile**  
The binding requirement set produced by the combination of declared package tier, lifecycle stage, and trigger traits.

**Minimum viable compliance**  
The smallest artifact and control set that fully satisfies all binding requirements of the declared compliance profile without leaving authority-bearing behavior, critical runtime claims, release obligations, rollback obligations, or audit reconstruction materially underspecified.

**Critical control**  
A control whose absence, misplacement, or ineffectiveness could permit unsafe mutation, authority bypass, release of a nonconforming system, unresolved contradiction on an authority-bearing path, or inability to detect or reconstruct a materially significant failure in time for meaningful response.

**Control sufficiency**  
The demonstrated adequacy of a control’s placement and enforcement method relative to the risk and runtime reachability of the behavior being controlled.

**Spec-authority mismatch**  
A condition in which the declared authority model, control boundaries, or mutation rights in normative artifacts cannot be reconciled with actual implementation paths, runtime behavior, operational procedures, or system topology.

**Queryable evidence**  
Evidence that is stably identifiable, machine-addressable where applicable, retrievable through predictable locations or APIs, linked by stable IDs or references, and usable during review, release, operation, or audit without tribal knowledge.

## **4\. Applicability and tiering**

Not every project requires the same package depth. Canonical packages must scale by authority, risk, and operational criticality.

Every package must declare:

* package tier  
* authority profile  
* risk profile  
* lifecycle stage  
* trigger traits  
* artifact applicability matrix

### **4.1 Package tiers**

**Tier 0 — Exploratory / pre-authoritative**  
Use for early exploration, internal prototypes, or non-production experiments with no direct production authority.

**Tier 1 — Internal operational**  
Use for internal systems with limited operational effect, limited authority, or reversible impact.

**Tier 2 — Production authoritative**  
Use for systems that mutate production state, influence release or approval decisions, enforce policy, or operate in business-critical paths.

**Tier 3 — High-impact authoritative**  
Use for systems with high-risk authority, safety implications, regulatory significance, broad blast radius, irreversible effects, or complex multi-party governance.

### **4.2 Trigger traits**

Regardless of tier, the following traits trigger stronger package requirements:

* mutable production authority  
* user or operator approval gates  
* time-based obligations  
* asynchronous workflows  
* external service dependencies  
* policy enforcement  
* regulated or compliance-sensitive domain  
* user data or sensitive data handling  
* rollback-sensitive migration  
* multi-party review or override paths  
* incident-driven operational burden

### **4.3 Lifecycle stages**

Every package must declare one lifecycle stage:

* concept  
* pre-implementation  
* implementation-active  
* pre-merge  
* pre-release  
* released  
* incident-remediation  
* deprecation or migration

The package must define what is binding at the declared stage and what is not yet complete.

### **4.4 Artifact applicability matrix**

Every required section and artifact must declare:

* required\_by\_tier  
* required\_by\_trigger\_trait  
* required\_by\_lifecycle\_stage  
* authoritative\_or\_informative  
* authored\_or\_generated  
* consumer\_list  
* failure\_if\_missing

An artifact without a declared consumer is non-compliant unless explicitly marked informative.

### **4.4A Minimum viable compliance rule**

For a given package, compliance MUST be determined by the declared compliance profile.

Authors MUST produce the smallest artifact and control set that fully satisfies that profile.

Reviewers MUST reject both:

* under-specification that leaves required controls or authority-bearing behavior materially undefined  
* unjustified overproduction that adds artifacts, process, or modeled structure without a declared consumer or control benefit

Tiering, lifecycle stage, and trigger traits MUST NOT be used to evade known authority-bearing behavior, known operational obligations, or known release and rollback risk.

When two artifact or control designs provide materially equivalent enforcement, auditability, and operational clarity, the lower-maintenance design is mandatory unless a higher-cost design has an explicitly stated control advantage.

### **4.5 Mandatory by tier**

All tiers must satisfy binding core requirements appropriate to declared lifecycle stage.

Tier 2 and Tier 3 packages must additionally include:

* explicit authority diagrams  
* invariant registry  
* incident handling model  
* release bundle definition  
* rollback plan  
* runtime guard mapping  
* dissent and override workflow  
* machine-usable domain model  
* traceability coverage report  
* enforcement allocation table  
* contradiction handling rules

Tier 3 packages must also include:

* reviewer independence rules with thresholds  
* stronger release conditions tied to dissent and risk  
* control-failure testing where appropriate  
* explicit emergency-state monitoring rules  
* stricter migration and rollback sequencing  
* operational readiness evidence before release  
* rollback rehearsal or equivalent proof for critical paths where feasible

For Tier 2 and Tier 3 packages, the package MUST also state why the chosen artifact depth is the minimum viable compliant depth for the declared compliance profile.

For any package claiming reduced artifact depth due to lifecycle stage or lower tier, known authority-bearing surfaces, runtime mutation paths, release conditions, rollback obligations, and contradiction risks remain binding and MUST still be explicitly covered.

## **5\. What the package must achieve**

A canonical spec package must let the organization answer, without guessing:

* what is being built  
* why it exists  
* what is in scope  
* what is out of scope  
* what the system must do  
* what it must never do  
* what data and entities exist  
* how state changes  
* which actions are allowed  
* which constraints block actions  
* which invariants must always hold  
* where authority lives  
* which actions can mutate authority-bearing state  
* what blocks unsafe mutation  
* where runtime guards exist  
* how contradictions are detected and resolved  
* which surfaces are high risk  
* who can approve what  
* how dissent is recorded  
* how incidents are created and escalated  
* how CI and release gates enforce the rules  
* what evidence proves conformance  
* how rollout, rollback, and emergency handling work

If the package cannot answer those questions directly, it is incomplete.

## **6\. Mandatory control-core summary**

Every canonical package MUST include a concise control-core summary. This is a blocker requirement.

The control-core summary is the shortest authoritative index of the system’s control structure. It is not a substitute for detailed artifacts.

The control-core summary MUST be structured, not freeform prose. It MUST be presented as a table or equivalent machine-parseable structure with one row per critical control path or critical control cluster.

Each entry MUST identify:

* control or control-path ID  
* protected requirement, invariant, or authority path  
* authoritative state holder  
* authoritative artifact  
* allowed mutation path  
* prevention point  
* detection point  
* runtime guard location if any  
* merge or release gate dependency if any  
* rollback trigger  
* rollback owner  
* emergency-path boundary if applicable  
* evidence source  
* linked contradiction risk if applicable

The control-core summary MUST be short enough to inspect as a single review object. It MUST NOT duplicate whole sections of the spec.

If this summary is missing, contradictory, structurally incomplete, or dependent on hunting across many artifacts to reconstruct a single critical control path, the package is blocker-noncompliant.

## **7\. Normative precedence**

When package artifacts conflict, precedence is:

1. signed machine-readable enforcement artifacts  
2. signed release artifacts and bundle manifests  
3. machine-readable schemas, invariants, policies, and domain model exports  
4. normative prose in spec documents  
5. generated diagrams, reports, and rendered views  
6. informative notes, examples, and commentary

Diagrams are explanatory unless explicitly marked normative.

Runbooks are operational guidance unless explicitly designated as authority-bearing release or incident procedures.

## **8\. Contradiction and drift handling**

Normative precedence does not excuse contradiction.

If two normative artifacts conflict, the package is blocker-noncompliant until one of the following occurs:

* the conflict is resolved  
* one artifact is explicitly deprecated  
* an emergency exception permits temporary divergence and records cleanup obligations

If runtime behavior conflicts with higher-precedence normative artifacts, release must be blocked unless an explicitly declared emergency path allows temporary divergence.

The package must define:

* contradiction detection rules  
* contradiction severity classes  
* who owns reconciliation  
* maximum allowed drift duration by artifact class  
* regeneration obligations for generated artifacts  
* incident linkage rules when runtime behavior diverges from normative controls

Generated artifacts are invalid if authoritative inputs changed, consumer compatibility changed, or declared regeneration obligations were not satisfied.

A declared precedence order does not cure a spec-authority mismatch.

If normative artifacts are internally consistent but their declared authority boundaries, mutation rights, control points, or enforcement claims cannot be reconciled with real implementation paths, runtime behavior, or operational procedures, the package is blocker-noncompliant.

The package MUST define how spec-authority mismatches are:

* detected  
* classified  
* linked to incidents or release blocks where applicable  
* corrected  
* prevented from recurring

## **9\. Binding core vs conditional controls**

Every package must distinguish:

* binding core requirements: mandatory given the declared tier and lifecycle stage  
* conditional controls: required only above a threshold or when triggered by declared traits  
* informative guidance: useful but non-binding

Reviewers must block any package that:

* presents optional or conditional material as universally mandatory without basis  
* omits required controls while claiming lower applicability without declared justification  
* uses lifecycle stage as an excuse to hide known authority-bearing behavior

Conditionality MUST be derived from declared tier, lifecycle stage, trigger traits, or explicitly stated thresholds. It MUST NOT be used as a blanket excuse to defer specification of known risky behavior.

A package is noncompliant if it declares a control as conditional while relying on that control’s effect elsewhere in the package.

## **10\. Standard output format**

For every project, produce a complete package containing these canonical documents or equivalent sections:

* spec.md  
* plan.md  
* tasks.md  
* clarifications.md  
* machine-readable schemas  
* governance artifacts  
* domain model export  
* diagram set  
* validation and release artifacts

Repository layout must be predictable enough that automation can discover and validate specifications, schemas, governance artifacts, CI definitions, runtime references, observability definitions, and runbooks.

## **11\. Canonical package structure**

### **11.1 Document control**

Every package must begin with document control metadata:

* title  
* spec ID  
* version using semantic versioning  
* status  
* owners  
* reviewers  
* approvers  
* created date  
* last updated date  
* related specs  
* supersedes  
* superseded-by  
* release state  
* lifecycle stage  
* changelog

All specifications must have semantic versions and a changelog.

### **11.2 Overview**

State plainly:

* what it is  
* who it serves  
* what problem it solves  
* what outcome it produces  
* why this matters now  
* what adjacent systems it touches  
* where the boundary of this spec ends

This section must be short, concrete, and falsifiable.

### **11.3 Purpose and scope**

Define:

* functional scope  
* operational scope  
* environment scope  
* deployment scope  
* governance scope  
* integration scope  
* explicit non-goals

Non-goals are mandatory.

### **11.4 Audience and roles**

Define:

* spec authors  
* reviewers  
* implementers  
* operators  
* release managers  
* on-call owners  
* escalation owners

For each role define:

* responsibilities  
* required decisions  
* escalation path  
* authority limits  
* expected artifacts or outputs

### **11.5 Goals and non-goals**

Define measurable goals with metrics, targets, and time windows where applicable:

* reliability  
* performance  
* resilience  
* observability coverage  
* security  
* scalability  
* availability  
* compliance

Goals must map to metrics, SLOs, or objectively verifiable thresholds.

### **11.6 Stories and acceptance criteria**

Define stories for:

* end users  
* administrators  
* reviewers  
* operators  
* external systems  
* automation components

Each story must include testable acceptance criteria.

Every binding MUST requirement must map to a story, acceptance criterion, enforcement rule, or explicit policy basis.

### **11.7 Requirements and traceability**

Create numbered requirement sets:

* functional  
* non-functional  
* operational  
* governance  
* security  
* observability  
* validation  
* rollout

For each requirement include:

* ID  
* statement  
* rationale  
* priority  
* affected surfaces  
* owning team  
* verification method  
* linked test or check  
* linked invariant if applicable  
* linked domain-model element if applicable  
* linked control point  
* lifecycle applicability

Vague language is forbidden in binding requirements.

### **11.8 Architecture**

Define:

* system boundary  
* component model  
* authoritative vs non-authoritative layers  
* control plane vs data plane  
* state ownership  
* execution model  
* data stores  
* external dependencies  
* trust boundaries  
* failure domains  
* scaling model  
* isolation boundaries

The package must state where truth lives and which components may mutate authoritative state.

### **11.9 Machine-usable domain model**

A machine-usable domain model is mandatory for canonical packages. A full ontology is required when domain semantics drive workflow, validation, authority, evidence, or audit behavior.

The domain model is not a glossary. It is the machine-usable representation of the system’s governed entities, states, actions, constraints, relationships, and evidence hooks needed for orchestration, validation, review, state transition, evidence capture, or audit.

The package must explicitly justify the modeling depth chosen:

* why this system requires a minimal state/entity model or a full ontology  
* which runtime, validation, review, audit, or workflow consumers depend on it  
* what would fail if the model were absent or underspecified

A decorative model is non-compliant. A model is compliant only if at least one binding validator, workflow step, runtime decision, review or release gate, audit process, generated authoritative artifact, or runtime guard consumes model elements directly or through declared generated outputs.

#### **11.9.1 Domain model validity rule**

A model does not count as valid merely because an export file exists.

A model export file does not count as valid merely because it exists, parses, or appears structurally complete.

A valid model must include:

* typed objects representing real domain entities where applicable  
* state models for stateful entities  
* action definitions with preconditions and postconditions  
* authority-bearing fields and mutation rules  
* event semantics where events affect control, audit, or workflows  
* invariant linkage  
* at least one declared consuming system, validator, workflow, audit process, release gate, or runtime guard

A valid model MUST have declared consumers that materially depend on model semantics. If removal of the model would not break a real validation, workflow, audit, gate, or control function, the package MUST justify why the model remains binding.

#### **11.9.2 Domain model purpose**

State:

* what domain is being modeled  
* what decisions depend on the model  
* what is inside the model boundary  
* what is outside the model boundary  
* which systems consume it  
* which parts are authoritative

#### **11.9.3 Modeling rules**

State these baseline rules:

* object types represent real domain entities, not UI views  
* properties represent facts or controlled state  
* action types represent allowed domain operations  
* links represent meaningful semantic relationships  
* lifecycle states are finite and enumerated  
* derived fields declare inputs and derivation logic  
* authority-bearing fields define who may mutate them  
* authoritative state must be distinguished from projections and caches

#### **11.9.4 Object types**

For each object type include:

* canonical name  
* API name  
* purpose  
* owner  
* primary key  
* title key  
* mutability model  
* lifecycle participation  
* required links  
* related actions  
* retention rule  
* example instance

#### **11.9.5 Property tables**

For each property include:

* name  
* type  
* required or optional  
* enum if applicable  
* default  
* source of truth  
* validation rule  
* mutability rule  
* sensitivity class  
* whether indexed  
* whether authoritative or derived  
* example value

#### **11.9.6 Enumerations**

Define controlled vocabularies for:

* statuses  
* decisions  
* severities  
* artifact classes  
* review outcomes  
* policy categories  
* authority levels  
* event types

#### **11.9.7 Link types**

For each link include:

* source object  
* target object  
* cardinality  
* ownership semantics  
* delete or cascade behavior  
* integrity constraints  
* whether the relationship carries attributes

#### **11.9.8 Action types**

For each action include:

* canonical name  
* target object types  
* initiator types  
* authority required  
* required inputs  
* optional inputs  
* preconditions  
* validation rules  
* side effects  
* state changes  
* emitted events  
* output artifacts  
* idempotency rule  
* retry behavior  
* forbidden conditions  
* audit requirements  
* postconditions on success  
* postconditions on failure

No action may exist without explicit preconditions and postconditions.

#### **11.9.9 Lifecycle state models**

For each stateful object define:

* state field  
* allowed states  
* initial state  
* terminal states  
* allowed transitions  
* disallowed transitions  
* evidence required for transition  
* rollback or reopen rules  
* timeout or escalation rules  
* who may initiate transitions

#### **11.9.10 Constraints and invariants**

Constraints must cover validation, sequencing, eligibility, exclusivity, deadlines, approvals, and dependency rules.

Invariants must be versioned, testable, mapped to enforcement points, and linked to incidents when violated.

#### **11.9.11 Event semantics**

For each event type define:

* name  
* trigger  
* payload  
* source object  
* related objects  
* actor  
* correlation fields  
* append-only behavior  
* retention rule  
* audit significance

#### **11.9.12 Authority rules**

For each object and action specify:

* authoritative writer  
* allowed readers  
* approval requirements  
* review gate if required  
* append-only vs overwrite  
* backend-only vs user-proposed vs reviewer-approved mutation path

#### **11.9.13 Domain model traceability**

Map model elements to:

* requirements  
* workflows  
* APIs  
* schemas  
* invariants  
* tests  
* incidents  
* dashboards  
* runbooks  
* release gates where applicable

#### **11.9.14 Machine-readable export**

Every model must be exported as JSON or YAML and versioned.

Where machine-checking is claimed, export freshness and compatibility with consuming systems MUST be automatically testable.

### **11.10 Data flows and interface contracts**

Define all major flows:

* inbound requests  
* outbound responses  
* internal messages  
* event emissions  
* artifact movement  
* persistence operations  
* external service integrations

For each interface specify:

* schema  
* examples  
* required fields  
* defaults  
* invalid cases  
* error codes  
* compatibility rules  
* idempotency keys if applicable  
* correlation IDs  
* security expectations

### **11.11 Preconditions and postconditions**

For every major operation, workflow step, state transition, and release action, define:

* preconditions  
* postconditions on success  
* postconditions on failure  
* rollback obligations  
* cleanup behavior  
* persistence obligations  
* emitted telemetry  
* notification obligations if any

### **11.12 Workflow and runtime behavior**

If the system executes steps, tasks, jobs, sessions, pipelines, or DAGs, define them explicitly.

For each step include:

* purpose  
* initiator  
* inputs  
* outputs  
* dependencies  
* secrets used  
* timeout  
* retry policy  
* idempotency behavior  
* state mutations  
* artifacts created  
* logs, metrics, traces emitted  
* terminal conditions  
* failure behavior  
* rollback behavior

### **11.13 Error handling, retries, rollback, and cancellation**

Define error classes:

* user error  
* validation error  
* dependency failure  
* transient system failure  
* permanent system failure  
* policy denial  
* authorization failure  
* data integrity failure  
* invariant violation  
* operator cancellation  
* timeout  
* emergency interruption

For each class define:

* retryability  
* backoff  
* max attempts  
* escalation rule  
* operator visibility  
* incident creation rule  
* rollback mechanics  
* affected state transitions

### **11.14 Security, identity, and authority boundaries**

Define:

* identity types  
* authn/authz model  
* RBAC or policy model  
* secret handling  
* privileged actions  
* forbidden actions  
* service-to-service trust rules  
* network trust boundaries  
* audit logging requirements  
* redaction rules  
* data sensitivity classes

Production observation may log, measure, sample, alert, and report. It must not mutate prompts, policies, rules, or other authority surfaces unless an explicitly authorized separate mutation path exists.

### **11.15 Change surface taxonomy**

Every package that can produce implementation work must classify its change surfaces.

At minimum:

* AUTHORITY\_LOGIC  
* PROMPTS  
* POLICIES  
* CONFIG  
* SCHEMA  
* OBSERVABILITY  
* INFRA\_ONLY

For each surface define:

* description  
* examples  
* authority impact  
* risk level  
* required reviewers  
* required tests  
* dissent sensitivity  
* release restrictions  
* multi-surface restrictions

### **11.16 Intent lineage**

Every meaningful change must be tied to an intent artifact.

Each intent must include:

* intent\_id  
* problem  
* out\_of\_scope  
* must\_not  
* affected\_surfaces  
* owner  
* created\_date

Each intent must also declare lineage:

* extends  
* narrows  
* supersedes  
* violates

Intent artifacts are append-only and stateful.

The package must define:

* intent model  
* intent state model  
* lineage rules  
* PR linkage rules  
* conflict detection rules  
* approval rules for violations or supersessions

### **11.17 Reviewer independence and entropy**

Reviewer independence must be evaluated for high-risk surfaces and higher tiers.

Metrics may include:

* author-reviewer pair frequency  
* team distribution  
* geography if relevant  
* role diversity  
* anchored comment depth  
* approval latency  
* phrasing reuse similarity  
* repeated reviewer loops

The package must specify:

* which surfaces require reviewer independence evaluation  
* which thresholds are warnings, escalations, or blocks  
* data sources  
* emergency exceptions  
* audit output format

Reviewer entropy metrics are heuristics, not proof of review quality. They must not substitute for required evidence, role separation, dissent effects, or release gating.

Reviewer independence and entropy signals MAY be used to escalate, require additional review, or require written justification.

They MUST NOT by themselves constitute proof of review quality, proof of independence, or sufficient basis for approval.

They MUST NOT independently block or approve unless a separate explicit policy states the exact thresholded behavior and the reason that behavior is control-relevant.

### **11.18 Review, dissent, and override workflow**

Review outcomes are:

* ACCEPT  
* ACCEPT\_WITH\_DISSENT  
* BLOCK

Dissent is preserved uncertainty, not failure.

Every package must define:

* review artifact schema  
* reviewer obligations  
* minimum evidence requirements  
* dissent artifact schema  
* override artifact schema  
* final outcome computation rules  
* follow-up requirements for dissent  
* block override rules  
* override expiration rules  
* monitoring conditions tied to dissent

For high-risk surfaces, dissent must tighten release conditions.

### **11.19 Invariant and incident registry**

This is mandatory for Tier 2 and Tier 3 packages and any package with authority-bearing production mutation.

**Invariants**

Each invariant must include:

* invariant ID  
* version  
* title  
* severity  
* scope  
* statement  
* rationale  
* prevention entries  
* detection entries  
* audit entries  
* enforcement entries  
* owner group  
* tags

Statements must be falsifiable.

**Incidents**

Each incident must include:

* ID  
* timestamp  
* severity  
* subsystem or service  
* summary  
* detection source  
* violated invariants  
* blast radius  
* mitigation status  
* follow-up action  
* assignee or owner  
* append-only analysis events

The package must explicitly define runtime guards for critical invariants, not just CI checks.

If incidents are tracked in an external authoritative system, the package must declare:

* system of record  
* synchronization rules if mirrored locally  
* freshness expectations  
* conflict handling  
* minimum retained linkage from package artifacts

### **11.20 Enforcement allocation**

Every critical requirement and invariant must declare where it is:

* prevented  
* detected  
* gated  
* audited  
* remediated

For each control include:

* control ID  
* linked requirement or invariant  
* failure severity  
* prevention point  
* detection point  
* runtime guard if applicable  
* CI/static validation if applicable  
* review dependency if applicable  
* release gate dependency if applicable  
* remediation owner  
* sufficiency rationale

For high-severity failures, review-only or CI-only enforcement is insufficient unless the package explicitly proves the behavior cannot occur at runtime.

For every critical control, the package MUST include a control sufficiency rationale.

A critical control is insufficient if its only effective enforcement is one or more of:

* discretionary human memory  
* voluntary process adherence  
* review-only enforcement for runtime-reachable violations  
* CI-only enforcement for behavior that can still fail or drift at runtime  
* post hoc audit without timely prevention or detection

For high-severity or authority-critical failures, the package MUST explain why the chosen prevention, detection, runtime guard, gate placement, and remediation allocation are sufficient relative to actual failure reachability.

### **11.21 Observability and audit semantics**

Define:

* log schema  
* metric schema  
* trace model  
* correlation IDs  
* event taxonomy  
* dashboards  
* alert rules  
* burn-rate triggers  
* retention  
* redaction  
* immutable audit records  
* runbooks  
* release health checks

Observation may produce:

* metrics  
* incidents  
* samples  
* reports

Observation must not auto-fix authority-bearing production surfaces unless explicitly routed through a governed authority path.

Observation and audit outputs that are required as evidence for review, release, incident response, or reconstruction MUST satisfy the package’s queryability requirements.

Evidence that cannot be predictably retrieved and correlated during review, release, operation, or audit does not satisfy a binding evidence obligation.

### **11.22 Testing and conformance validation**

Testing must be mapped to requirements and invariants.

Include as applicable:

* unit tests  
* integration tests  
* end-to-end tests  
* schema validation  
* conformance tests  
* regression suites  
* replay tests  
* compatibility tests  
* failure injection  
* chaos tests where warranted  
* release-readiness checks  
* governance-path negative tests  
* release-gate bypass tests  
* stale-artifact detection tests  
* authority-boundary violation tests  
* rollback proof or rehearsal where warranted

The package must state:

* what proves conformance  
* what blocks merge  
* what blocks release  
* what evidence is retained

### **11.23 CI and merge authorization**

The governance pipeline must be documented as a deterministic sequence.

At minimum:

* spec validation  
* schema validation  
* surface classification  
* intent lineage verification  
* invariant compatibility check  
* reviewer independence evaluation where required  
* governance policy evaluation  
* merge authorization

The package must define:

* workflow file locations  
* required artifacts  
* blocking conditions  
* signature or attestation rules  
* artifact retention  
* auditability of gate outcomes

### **11.24 Release, rollout, migration, and rollback**

Release is permissioned, not automatic.

The package must define:

* release prerequisites  
* approvers  
* bundle contents  
* rollout stages  
* migration sequencing  
* canary or staged rollout if applicable  
* rollback triggers  
* rollback steps  
* rollback ownership  
* artifact integrity expectations  
* version compatibility  
* post-release verification

### **11.25 Emergency path**

Emergency behavior must be defined once, clearly, and narrowly.

Every package must define:

* what qualifies as an emergency  
* who can declare it  
* what process may be skipped  
* what cannot be skipped  
* maximum allowed duration of emergency state  
* mandatory retroactive obligations  
* maximum delay before cleanup artifacts are due  
* rollback or mitigation rules if cleanup does not happen  
* required monitoring during emergency state  
* required incident linkage  
* explicit prohibition on silent authority drift during emergency handling

### **11.26 Repo wiring**

The package must specify where artifacts live.

A canonical layout should cover at least:

* specs  
* schemas  
* intent artifacts  
* invariant artifacts  
* incident artifacts  
* dissent artifacts  
* surface maps and policies  
* review metrics  
* CI definitions  
* enforcement scripts  
* runbooks  
* dashboards  
* machine-readable model exports

## **12\. Required artifact set**

### **12.0 Artifact obligation classes**

The package MUST classify artifacts into the following obligation classes:

**Baseline required artifacts**  
Artifacts always required for the declared compliance profile.

**Conditionally required artifacts**  
Artifacts required only when triggered by declared tier, lifecycle stage, trigger traits, system shape, or risk thresholds.

**Derived or discoverable artifacts**  
Artifacts not necessarily authored as standalone deliverables but required to be reproducibly discoverable, regenerable, or computable from authoritative inputs.

**External authoritative linkages**  
References to external systems of record that are authoritative for incidents, approvals, release records, or other governed evidence.

Section 12 examples and filenames do not override applicability rules.

An artifact named in the canonical set is not automatically mandatory unless the declared compliance profile or trigger conditions require it.

### **12.1 Core docs**

* spec.md  
* plan.md  
* tasks.md  
* clarifications.md

### **12.2 Governance artifacts**

* intent.md  
* lineage.yaml  
* .surface-map.yaml  
* .surface-policy.yaml  
* .review-metrics.yaml  
* reviews/PR-\<n\>.yaml  
* dissent/DIS-\<id\>.yaml  
* overrides/OVR-\<id\>.yaml  
* waivers/WVR-\<id\>.yaml

### **12.3 Invariant and incident artifacts**

* invariants/INV-\*/invariant.yaml  
* invariants/index.yaml  
* incidents/INC-\*.yaml or authoritative external record linkage

### **12.4 Domain model artifacts**

* model.md or ontology.md where applicable  
* model.json or model.yaml  
* state diagrams  
* entity relationship diagrams  
* action flow diagrams  
* authority diagrams  
* event flow diagrams

### **12.5 CI and release artifacts**

* required workflow definitions  
* merge authorization artifact  
* release bundle manifest  
* rollback artifact or plan  
* post-release validation report

### **12.6 Artifact metadata requirements**

Every artifact must declare or inherit:

* authoritative\_or\_informative  
* authored\_or\_generated  
* consumer\_list  
* source\_inputs if generated  
* regeneration\_method if generated  
* owner  
* freshness expectation if synchronized  
* failure\_if\_missing

For all binding artifacts and binding evidence, metadata MUST support queryability.

At minimum this includes, where applicable:

* stable identifier  
* predictable location or retrieval path  
* owner  
* artifact class  
* authoritative or informative status  
* authored, generated, or synchronized status  
* consumer list  
* linkage to governing requirement, invariant, control, review, release, or incident record

**failure\_if\_missing** MUST use bounded categories, not freeform prose.

Allowed values should include one or more of:

* merge\_block  
* release\_block  
* runtime\_unsafe  
* audit\_reconstruction\_failure  
* review\_invalid  
* operator\_execution\_degraded  
* informative\_only

Package-specific extensions MAY be added only if explicitly defined.

### **12.7 Authored vs generated artifact classification**

Every package must declare which artifacts are:

* authored  
* modeled  
* generated  
* authoritative external sync outputs

Generated artifacts must be reproducible from declared sources.

A generated artifact is compliant only if:

* its authoritative inputs are declared  
* regeneration is deterministic enough for the claimed use  
* consumer compatibility rules are defined where applicable  
* freshness expectations are defined  
* stale or incompatible generation can be detected where machine-checking is claimed

An artifact MUST NOT be labeled authoritative merely because it is generated, signed, or difficult to edit.

## **13\. Diagram instructions**

Diagrams are mandatory when they remove ambiguity in control, authority, state, sequencing, or trust boundaries.

Mandatory diagram triggers include:

* a stateful object with more than three lifecycle states  
* an approval or review path involving more than one role  
* a cross-boundary mutation path  
* an asynchronous workflow with retries, cancellation, or rollback  
* a system spanning more than one trust boundary  
* a deployment with distinct authoritative and non-authoritative layers

Where applicable include:

* system context diagram  
* component diagram  
* trust boundary diagram  
* deployment or topology diagram  
* data flow diagram  
* entity diagram  
* state machine diagrams  
* sequence diagrams for golden and failure paths  
* workflow or DAG diagram  
* authority map  
* event flow diagram  
* governance pipeline diagram

Diagram rules:

* use Mermaid by default  
* every diagram needs a title  
* every diagram needs a one-sentence purpose  
* every node must map to named entities in the text  
* every edge must correspond to a real relationship or flow  
* highlight authoritative boundaries  
* highlight high-risk control points  
* include failure paths, not just happy paths  
* identify the section or requirement IDs the diagram clarifies

Decorative diagrams are non-compliant.

## **14\. Canonical section quality rules**

Every section must answer, as applicable:

* what it is  
* why it exists  
* who owns it  
* what it depends on  
* what it produces  
* what can fail  
* how failure is detected  
* how failure is handled  
* what evidence proves it worked  
* what invariants govern it  
* what authority boundary constrains it

Every MUST statement should be traceable to one or more of:

* acceptance criteria  
* tests  
* CI checks  
* invariants  
* runtime guards  
* release gates  
* runbooks  
* model elements

The reverse must also hold for binding controls: every acceptance criterion, invariant, runtime guard, and release gate must map back to at least one requirement, story, or policy basis.

## **15\. Anti-bloat and anti-theater rules**

Canonical packages must be complete, but not ceremonial.

The following are prohibited:

* duplicate normative content spread across multiple artifacts without declared precedence  
* diagrams that restate tables without adding control or state clarity  
* models that are not consumed by any validation, workflow, guard, audit, or release process  
* traceability links that are present only for appearance and not machine-checkable where machine checking is claimed  
* review or dissent artifacts created without effect on gate computation, monitoring, or audit  
* placeholder sections that contain only slogans, narrative filler, or unbounded future work  
* required artifacts with no declared consumer  
* control claims with no named prevention, detection, or audit point  
* generated artifacts with no declared source or regeneration method  
* producing full-fidelity governance or modeling artifacts where a smaller structure would satisfy the same binding controls  
* using canonical filenames or artifact count as evidence of rigor  
* retaining a binding artifact whose declared consumer has been removed without either removing, downgrading, or re-justifying the artifact  
* repeatedly using exceptions, waivers, or emergency procedures as standing substitutes for missing controls

Each artifact must justify itself by at least one of:

* implementation clarity  
* enforcement  
* operational execution  
* review quality  
* release control  
* auditability

If an artifact does not change implementation, operation, enforcement, review, release, or audit outcomes, it should be removed or downgraded to informative material.

If two approaches provide equivalent control sufficiency, auditability, and operational usefulness, the lower-maintenance approach is required.

## **16\. Writing rules**

The package must be written like an engineering control document.

It must be:

* blunt  
* explicit  
* structured  
* falsifiable  
* machine-friendly  
* traceable

Do not use:

* filler  
* marketing language  
* “works well”  
* “robust”  
* “intuitive”  
* “should not break”  
* “unexpected”  
* “best effort” without exact mechanics  
* “TBD” without an explicit blocking note, owner, and closure path

Normative language:

* MUST / MUST NOT \= binding  
* SHOULD / SHOULD NOT \= deviation requires documented rationale  
* MAY \= optional  
* examples are non-normative unless explicitly marked otherwise

Assumptions must be labeled and tracked for closure.

## **17\. Spec versioning, compatibility, and migration**

All packages must use semantic versioning.

### **17.1 Version meaning**

* major: breaking change to requirements, authority model, interfaces, model semantics, invariants, or release expectations  
* minor: backward-compatible addition or strengthening that does not invalidate compliant prior implementations  
* patch: clarification, correction, typo fix, or non-behavioral cleanup

### **17.2 Breaking change rule**

A change is breaking if it changes:

* required behavior  
* allowed or forbidden actions  
* authority paths  
* schema compatibility  
* model object meaning  
* invariant interpretation  
* release or rollback obligations  
* required evidence for approval or operation

### **17.3 Migration obligations**

When a breaking change is introduced, the package must define:

* affected artifacts  
* migration path  
* compatibility window  
* deprecation timeline if any  
* enforcement date  
* rollback implications  
* required downstream updates

If a breaking change alters authority paths, control allocation, or evidence obligations, the package MUST explicitly identify any temporary mismatches permitted during migration, their expiration, their monitoring requirements, and the rollback or cleanup path if migration stalls.

## **18\. Noncompliance severity classes**

Review findings must classify noncompliance as:

* Blocker  
* Major  
* Minor

### **18.1 Blocker**

Missing or contradictory definition in any of:

* authority model  
* critical state transitions  
* rollback path  
* release gating  
* invariant mapping for safety-critical or authority-critical behavior  
* authoritative source of truth  
* required interface contract  
* required incident or runtime guard behavior  
* control-core summary  
* contradiction handling  
* enforcement allocation for critical controls  
* spec-authority mismatch  
* critical control with insufficient enforcement placement  
* binding evidence that is not queryable  
* repeated exception path functioning as a de facto permanent control substitute  
* control-core summary not in required structured form

### **18.2 Major**

Material weakness that undermines implementation, operation, or auditability but is not immediately authority-fatal.

Examples:

* incomplete traceability  
* undefined escalation owner  
* partial observability coverage  
* incomplete dissent handling on a high-risk surface  
* missing compatibility rule on a critical interface  
* artifact with weakly declared consumer or regeneration path  
* unbounded or weakly defined failure\_if\_missing categories  
* generated artifact with unclear freshness or regeneration obligations  
* reviewer independence metrics used without declared policy meaning

### **18.3 Minor**

Defect that reduces clarity or maintainability but does not create immediate control failure.

Examples:

* weak examples  
* incomplete non-goal explanation  
* missing diagram where text is still sufficient  
* formatting or naming inconsistency

## **19\. Minimum shippable spec thresholds**

Different lifecycle stages require different minimum package completeness.

### **19.1 Before implementation begins**

At minimum:

* overview  
* scope and non-goals  
* control-core summary  
* core requirements  
* authority model  
* major workflows  
* key interfaces  
* initial model shape  
* critical invariants list  
* open assumptions and owners

At minimum, the package MUST also state the declared compliance profile and why the chosen artifact depth is the minimum viable compliant depth.

### **19.2 Before merge of implementation affecting controlled surfaces**

At minimum:

* traceability coverage  
* updated schemas  
* updated model where relevant  
* tests mapped to requirements  
* review artifacts  
* dissent artifacts if applicable  
* runtime guard definitions for critical invariants  
* CI gate conformance  
* enforcement allocation for affected critical controls

At minimum, the package MUST also demonstrate control sufficiency for changed critical controls and identify any introduced spec-authority mismatch risk.

### **19.3 Before production release**

At minimum:

* release bundle definition  
* rollback plan  
* operational runbooks  
* observability and alerting definitions  
* release approval evidence  
* post-release verification criteria  
* incident linkage and on-call ownership  
* version compatibility statement  
* contradiction-free normative artifacts  
* required generated artifacts regenerated from current authoritative inputs

At minimum, the package MUST also confirm:

* no unresolved spec-authority mismatch exists on any release-relevant path  
* required binding evidence is queryable  
* no temporary exception has silently become standing operating practice

## **20\. Standing Framework red-flag language**

If the spec, implementation notes, review discussion, or release discussion contains statements equivalent to:

* “the model figured it out”  
* “it passed tests so it’s fine”  
* “we’ll document later”  
* “we can fix it in prod”  
* “it changed on its own”

treat that as an authority leak and stop for review.

## **21\. Completion standard**

A spec package is complete only when all of the following are true:

* a builder could implement core behavior without guessing about authority-bearing behavior  
* a reviewer could block with specific artifact-backed objections  
* an operator could run it using the package and runbooks  
* a release manager could determine exact gating conditions  
* an auditor could reconstruct intent, review, dissent, incident history, release decisions, and control evidence from durable artifacts  
* requirements, workflows, tests, invariants, model artifacts, enforcement allocation, and CI wiring are mutually consistent  
* no authority-bearing behavior relies on informal memory  
* production safety properties are mechanically enforced where they must be  
* critical controls have sufficient prevention, detection, gating, audit, and remediation placement for their risk  
* no unresolved spec-authority mismatch exists at the declared lifecycle stage  
* artifact set is minimum viable compliant, non-duplicative, and justified by implementation, enforcement, operation, review, release, or audit value  
* binding evidence is queryable  
* contradiction handling is defined and no unresolved blocker contradiction remains at the declared lifecycle stage  
* repeated exceptions have not become a shadow operating model

## **21A. Exception, waiver, and emergency anti-normalization rule**

No waiver, override, or emergency exception may permanently weaken a binding control through repetition, serial renewal, or silent carry-forward.

The package MUST define:

* maximum renewal count or equivalent anti-rollover rule where applicable  
* who may approve repeated use  
* what threshold triggers mandatory redesign review  
* what evidence proves the exception remains exceptional rather than normal operating mode

If the same control surface repeatedly requires exceptions, the package MUST trigger control redesign review, not merely further exception issuance.

## **22\. Final instruction to the spec-writing agent**

Produce a complete, non-duplicative, enforceable package.

Map every actor, entity, state, relationship, action, control point, approval path, failure path, invariant, incident trigger, review obligation, dissent branch, release condition, rollback path, contradiction risk, and enforcement point that matters to implementation, operation, review, release, or audit.

Do not stop at architecture.  
Do not stop at APIs.  
Do not stop at user flows.  
Do not stop at artifact enumeration.

The package must cover:

* semantic structure  
* execution behavior  
* operational behavior  
* governance behavior  
* evidence behavior  
* enforcement behavior  
* contradiction handling  
* control sufficiency

Everything authority-bearing must be controlled.  
Everything controlled must be reviewable.  
Everything reviewable must leave evidence.  
Everything evidenced must be queryable.  
Everything included must justify its existence.

Produce the minimum viable compliant package, not the largest possible package.

Do not create artifacts, models, diagrams, or governance structures that do not change implementation clarity, control sufficiency, operational execution, review quality, release control, or audit reconstruction.

If you claim a control is enforced, show where it is prevented, detected, gated, audited, and remediated, and why that placement is sufficient for the actual risk.

If you claim an artifact is binding evidence, make it queryable.

If you claim a boundary is authoritative, ensure real mutation paths and operating procedures match it.

