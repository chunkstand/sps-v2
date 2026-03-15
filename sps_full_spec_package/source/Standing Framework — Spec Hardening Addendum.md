# **Standing Framework — Spec Hardening Addendum**

Version: 2.0  
Status: Secondary instruction set  
Purpose: Define the mandatory post-draft hardening pass that converts a completed canonical spec package into an implementation-safe execution contract without silent scope expansion, fabricated closure, or non-traceable reinterpretation.

## **1\. Non-negotiable purpose**

This addendum applies only after an initial canonical spec package has been assembled.

Its purpose is not to restate the package, admire it, summarize it, or cosmetically improve it. Its purpose is to identify, classify, and close every residual defect that would otherwise cause builders to guess, reviewers to improvise, operators to rely on tribal knowledge, release managers to apply judgment instead of artifacts, or auditors to encounter non-reconstructible behavior.

A package is not hardened merely because it is thorough, well-written, or directionally correct.

A package is hardened only when authority-bearing behavior, runtime-critical behavior, release-bearing behavior, rollback-bearing behavior, evidence-bearing behavior, and operator-critical behavior are explicit enough that implementation, review, operation, release, and audit can proceed without informal invention.

## **2\. Scope of authority**

The hardening pass may:

* clarify  
* formalize  
* complete  
* normalize terminology  
* split overloaded concepts  
* convert narrative into contract form  
* convert implied behavior into bounded explicit behavior when the package already supports that interpretation

The hardening pass must not:

* silently change product intent  
* silently expand system scope  
* silently add new subsystems, actors, governance layers, services, workflows, or artifacts that are not required by an existing binding defect  
* invent authority boundaries not already supported by the package  
* resolve stakeholder policy choices as if already decided  
* fabricate missing facts  
* fabricate external requirements  
* fabricate implementation certainty where the package does not support it

If a defect cannot be closed honestly from package evidence or a clearly bounded assumption, it must be escalated, not invented away.

## **3\. Core hardening stance**

Treat all residual ambiguity on authority-bearing, release-bearing, rollback-bearing, evidence-bearing, audit-bearing, security-bearing, compliance-bearing, and runtime-critical surfaces as a defect.

Treat all placeholder language on binding surfaces as defective unless bounded and governed.

This includes, but is not limited to:

* to be defined  
* handled elsewhere  
* implementation-specific  
* for brevity  
* system-determined  
* configurable  
* policy-defined  
* dynamic  
* as appropriate  
* may be skipped  
* typically  
* expected to  
* future work

These phrases are not acceptable substitutes for binding behavior unless all of the following are explicitly defined:

* owner  
* allowed values or range  
* decision rule  
* enforcement point  
* change-control path  
* audit consequence

Do not preserve a gap merely because the likely implementation seems obvious.

Do not preserve prose elegance at the expense of executable clarity.

Do not confuse confidence with closure.

## **4\. Hardening objective**

The hardening pass must force the package from strong draft to buildable contract.

After hardening, the package must make the following directly answerable without inference:

* exact allowed state transitions  
* exact mutation paths for authoritative state  
* exact preconditions and postconditions for critical actions  
* exact contracts across interfaces and boundaries  
* exact evidence required for approval, release, rollback, and audit  
* exact handling of contradictions, stale data, unsupported dependencies, and degraded modes  
* exact operator actions in failure, rollback, manual fallback, and emergency paths  
* exact reasons a build may proceed, be conditionally approved, or be blocked

If the answer to any of these still depends on local interpretation, the package is not hardened.

## **5\. Closure decision rule**

For every defect, the hardening pass must choose exactly one closure posture:

1. **Closed from package evidence**  
   The package already contains enough material to close the defect without adding new assumptions.  
2. **Closed with explicit bounded assumption**  
   The defect can be closed only by adding a stated assumption that is narrow, visible, and non-silent.  
3. **Escalated for policy or product decision**  
   The defect depends on unresolved stakeholder intent, scope, or governance choice.  
4. **Escalated for external factual validation**  
   The defect depends on facts, regulations, interfaces, dependencies, or external constraints not established in the package.  
5. **Escalated for implementation experiment**  
   The defect depends on runtime feasibility, performance, integration behavior, or technical unknowns that require testing rather than prose.  
6. **Left open as blocker**  
   The defect materially prevents build-safe implementation and cannot be honestly closed yet.

No defect may be “softly noted.” Every defect must be closed or explicitly escalated under one of these postures.

## **6\. Defect severity**

Every defect must be assigned one severity:

* **Blocker**  
  The package cannot safely proceed to build or release planning while this defect remains unresolved.  
* **Major**  
  The package can be read and decomposed, but meaningful implementation, review, or operations would still require risky interpretation.  
* **Moderate**  
  The package remains directionally buildable, but the defect weakens consistency, operability, or auditability.  
* **Minor**  
  The defect does not materially change build safety but should be corrected for clarity, precision, or maintainability.

A defect is automatically a **Blocker** if any of the following are true:

* an authoritative mutation path is undefined or ambiguous  
* a critical state transition is missing, conflicting, or narrative-only  
* a reviewer gate lacks explicit input/output contract  
* a release gate lacks measurable pass/fail criteria  
* a rollback trigger exists without rollback mechanics  
* a core runtime object materially affecting authority or workflow is only partially modeled  
* a binding evidence obligation is not queryable or reconstructible  
* a critical operator path lacks executable runbook structure  
* a normal external dependency failure can occur without safe-stop, fallback, or bounded unsupported-case behavior  
* advisory and authoritative behavior remain materially conflated

## **7\. Mandatory hardening passes**

### **7.1 Contradiction and normalization pass**

Before attempting closure, identify and reconcile:

* conflicting terminology  
* duplicated concepts with different names  
* conflicting state definitions  
* conflicting control definitions  
* conflicting authority claims  
* conflicting exception semantics  
* narrative sections that disagree with schemas, tables, or workflows  
* release logic that disagrees with rollback logic  
* runbook language that disagrees with lifecycle or controls

The hardening pass must normalize the package into one coherent authority-bearing vocabulary before further completion.

### **7.2 Contract completion pass**

For every promised, referenced, or implied interface, define the contract fully.

This includes:

* APIs  
* RPCs  
* commands  
* internal messages  
* event envelopes  
* queue payloads  
* persisted artifacts  
* reviewer decision payloads  
* operator action payloads  
* external connector interactions  
* release and rollback artifacts

For every contract, define:

* canonical name  
* purpose  
* producer  
* consumer  
* trigger  
* schema  
* required fields  
* optional fields  
* defaults  
* validation rules  
* invalid cases  
* error classes  
* retry behavior  
* idempotency behavior  
* correlation fields  
* authority effect  
* emitted evidence and audit fields  
* compatibility/versioning rules

A contract is incomplete if its existence is asserted but its payload semantics are not fully defined.

### **7.3 Authority and state completion pass**

For every stateful object, workflow, approval path, submission path, rollback path, and rejection/reopen path, define the complete state model.

This includes:

* initial states  
* active states  
* review-pending states  
* blocked states  
* rejected states  
* reopened states  
* degraded states  
* rollback states  
* terminal states  
* timeout states  
* emergency states where applicable

For every transition, define:

* source state  
* target state  
* initiator  
* required evidence  
* preconditions  
* forbidden conditions  
* side effects  
* emitted events  
* success postconditions  
* failure postconditions  
* timeout behavior  
* escalation path  
* rollback or reopen path

No state model may contain ellipses, implied transitions, or narrative shortcuts.

### **7.4 Domain completeness pass**

Every core domain object named in the package must be fully specified if it affects workflow, validation, review, release, rollback, evidence, audit, security, billing, policy, or authority.

For each core object, define:

* canonical name  
* purpose  
* source of truth  
* identity and keys  
* fields and field meanings  
* required vs optional fields  
* authoritative vs derived vs advisory classification  
* mutability rules  
* permitted writers  
* lifecycle participation  
* validation rules  
* relationships to other objects  
* evidence and provenance links  
* retention expectations  
* redaction constraints  
* versioning behavior

Summarized treatment of a core object is non-compliant if the object materially affects governed behavior.

### **7.5 Control sufficiency pass**

Every critical requirement, invariant, and guardrail must be checked for actual enforcement sufficiency.

Identify and correct:

* controls claimed but not placed  
* controls placed but not tied to a defect or threat  
* review-only controls used for runtime-reachable failures  
* CI-only controls used for driftable runtime behavior  
* detection without ownership  
* rollback triggers without execution mechanisms  
* release gates without verifiable evidence  
* emergency exceptions without anti-normalization boundaries  
* audit logging presented as a substitute for prevention where prevention is required

If a control exists only as intent language, it does not count as a control.

### **7.6 Evidence and provenance pass**

Every binding evidence obligation must become explicit, queryable, and reconstructible.

For every evidence class, define:

* evidence producer  
* evidence consumer  
* storage or retrieval path  
* stable identifier  
* correlation keys  
* authoritative or informative status  
* retention rule  
* redaction rule  
* access restrictions  
* missing-evidence failure class

For every source-dependent workflow, define:

* what counts as authoritative source  
* source ranking rules  
* freshness requirements  
* capture requirements  
* citation or source-link requirements  
* contradiction handling  
* stale-source invalidation  
* provenance attachment rules  
* behavior when authoritative sources disagree or become unavailable

Evidence that cannot be predictably retrieved does not satisfy a binding obligation.

### **7.7 Operability and runbook pass**

Every operator-relevant path must have executable operational guidance.

This includes:

* degraded mode  
* dependency outage  
* partial failure  
* stalled review  
* stale data  
* unsupported-case detection  
* failed submission  
* rollback initiation  
* rollback verification  
* emergency declaration  
* emergency cleanup  
* manual fallback  
* safe-stop  
* re-entry after pause, rejection, rollback, or failure

For every critical runbook, define:

* trigger  
* symptoms  
* required diagnostic inputs  
* prerequisites  
* exact operator actions  
* forbidden actions  
* escalation owner  
* success criteria  
* closure evidence  
* incident linkage

A package is not hardened if safe operations still rely on operator folklore.

### **7.8 External dependency and unsupported-case pass**

Every external dependency must be classified by support level and failure mode.

For each dependency, define:

* dependency class  
* supported interaction modes  
* unsupported interaction modes  
* availability assumptions  
* latency or timeout assumptions  
* freshness assumptions  
* retry behavior  
* contradiction behavior when external truth changes  
* human handoff path  
* manual fallback path  
* safe-stop behavior when authoritative interaction cannot proceed  
* recovery and re-entry conditions

Unsupported cases must not be relegated to vague future work if they can occur during normal operation.

### **7.9 Release, rollback, and emergency boundary pass**

Release, rollback, and emergency rules must be explicit and mechanically bounded.

Define:

* measurable release criteria  
* required evidence for release decision  
* disqualifying conditions  
* rollback triggers  
* rollback executor and authority  
* rollback verification evidence  
* reopen or replay rules after rollback  
* emergency declaration criteria  
* controls that may never be bypassed  
* controls that may be conditionally bypassed  
* exact duration, documentation, approval, and cleanup requirements for any emergency exception

Emergency language must not create a reusable loophole.

### **7.10 Build-readiness verdict pass**

After hardening, the package must receive exactly one verdict:

* **BUILD\_APPROVED**  
* **BUILD\_APPROVED\_WITH\_BLOCKERS**  
* **NOT\_BUILDABLE**

This verdict must be artifact-backed.

It must include:

* blocker list  
* major unresolved risks  
* remaining assumptions  
* sections rewritten  
* sections still incomplete  
* contracts still missing  
* state models still incomplete  
* control defects still open  
* evidence obligations still non-queryable  
* operator paths still undefined

## **8\. No silent scope expansion rule**

The hardening pass must not add new systems, services, actor classes, approval layers, workflows, or artifacts unless all of the following are true:

* the addition closes an already-existing binding defect  
* the need is directly traceable to the original package  
* the addition is narrower than the defect it closes  
* the addition is explicitly marked as introduced by hardening  
* the package would remain unsafe or incoherent without it

“Improvement” is not enough. The addition must be necessary.

## **9\. Anti-fabrication rule**

The hardening pass must not simulate certainty.

It must not:

* invent source material absent from the package  
* invent external interface behavior  
* invent legal, regulatory, or dependency facts  
* invent stakeholder decisions  
* invent operator capabilities  
* invent support coverage  
* invent evidence that the package does not define

Where closure would require invention, the hardening pass must escalate rather than fabricate.

Fake precision is a defect, not an improvement.

## **10\. Traceability requirement**

Every hardening action must be traceable.

For each defect or closure item, record:

* defect ID  
* severity  
* defect class  
* source section or artifact  
* problem summary  
* closure posture  
* closure action  
* closure basis  
* whether the result is inferred, assumed, escalated, or blocked  
* residual risk

No rewritten or newly added authoritative section may appear without traceable reason.

## **11\. Hardening defect classes**

At minimum, classify defects as:

* Contract gap  
* State gap  
* Domain model gap  
* Authority ambiguity  
* Terminology/normalization conflict  
* Control insufficiency  
* Evidence gap  
* Operability gap  
* External dependency gap  
* Unsupported-case gap  
* Release gap  
* Rollback gap  
* Emergency-boundary gap  
* Advisory/authoritative confusion  
* Placeholder normative content  
* Spec-authority mismatch  
* Scope-drift risk  
* Fabrication risk

## **12\. Required output shape**

The hardening pass must produce output in the following order:

1. **Executive verdict**  
   A concise statement of whether the package is hardened, conditionally hardened, or not hardenable without blockers.  
2. **Defect register**  
   All identified defects with severity, class, source section, closure posture, and closure action.  
3. **Contradiction and normalization register**  
   All reconciled terminology conflicts, concept collisions, and cross-section inconsistencies.  
4. **Assumptions register**  
   Every assumption introduced during hardening, with justification and bounded effect.  
5. **Rewritten or added sections**  
   Full authoritative replacement text for sections requiring closure.  
6. **Completed contracts**  
   Fully specified contracts for previously incomplete or narrative interfaces.  
7. **Completed state models**  
   Full lifecycle/state definitions for previously incomplete or ambiguous flows.  
8. **Completed core object definitions**  
   Full domain models for authority-bearing or runtime-critical objects.  
9. **Runbook completions**  
   Executable operational structures for critical failure and intervention paths.  
10. **Open blockers and escalations**  
    Every issue that could not be honestly closed, with reason and required next action.  
11. **Final build-readiness verdict**  
    One of BUILD\_APPROVED, BUILD\_APPROVED\_WITH\_BLOCKERS, or NOT\_BUILDABLE.

## **13\. Final instruction to the hardening agent**

Do not praise the package. Interrogate it.

Do not preserve ambiguity because it sounds sophisticated.

Do not convert missing facts into invented answers.

Do not convert unresolved policy into fake certainty.

Do not expand scope in the name of completeness.

Do not leave critical behavior in prose when contract form is required.

Do not leave authority-bearing behavior dependent on inference.

Do not leave operators to improvise.

Do not leave reviewers to guess what blocks.

Do not leave release managers to rely on judgment instead of artifacts.

Close every defect that can be honestly closed.  
Escalate every defect that cannot.  
Mark every blocker that must stop build approval.  
Prefer explicit incompleteness over fabricated completion.

