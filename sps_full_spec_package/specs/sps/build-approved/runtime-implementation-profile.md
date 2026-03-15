---
artifact_id: ART-SPS-RUNTIME-001
authoritative_or_informative: authoritative
authored_or_generated: authored_materialized
consumer_list:
- implementers
- runtime_owners
- reviewers
- release_managers
owner: Architecture Lead
freshness_expectation: must match runtime implementation profile used for release
failure_if_missing: release_block
---


# SPS runtime implementation profile

This document is the normalized markdown materialization of the provided `Implementation SPS v2.0.1.docx`.

It is normative for implementation and binds the logical SPS agent model to a concrete runtime harness.

## Runtime architecture and harness binding

Runtime Architecture and Harness Binding
1. Purpose
This section binds the SPS logical agent model to a concrete execution runtime. The purpose of this binding is to ensure that the system is implementable, reviewable, durable under failure, and operationally auditable without changing the normative workflow model defined elsewhere in this package.
This binding is authoritative for implementation unless superseded by a later approved revision.
2. Binding decision
SPS shall use the following runtime stack:
Workflow and orchestration harness: Temporal

Execution language: Python

Agent implementation model: typed worker activities and child workflows

Reviewer model: separate human-in-the-loop reviewer service and UI

Authoritative data store: Postgres

Artifact and evidence storage: S3-compatible object storage

Model access layer: internal provider-abstracted LLM adapter

Schema and contract enforcement: typed schemas using Pydantic or equivalent strongly validated schema system

No high-level autonomous agent SDK shall be treated as the authoritative system harness.
3. Architectural stance
SPS is not implemented as a free-form multi-agent conversation system. SPS is implemented as a governed workflow system containing agent-shaped execution units.
The authoritative control structure is:
State Machine
  -> Temporal Workflow
    -> Planner
      -> Typed Tasks
        -> Specialist Worker Activities / Child Workflows
          -> Evidence and Artifact Outputs
            -> Reviewer Decision
              -> State Transition Guard
                -> Next Case State
The planner, specialists, and reviewer are logical roles defined by the system architecture. Their runtime realization shall follow the binding in this section.
4. Harness definition
For purposes of this package, the term harness means the durable runtime responsible for:
workflow execution

task ordering

retries

timeouts

compensation and rollback coordination

human approval waiting states

replayability

audit reconstruction of execution history

The SPS harness shall be Temporal, and no other subsystem shall be treated as the authoritative source of workflow progression.
Temporal workflow history, together with SPS evidence and review artifacts, shall be sufficient to reconstruct why a case reached its present state.
5. Agent implementation model
5.1 General rule
Each SPS agent shall be implemented as one of the following runtime forms:
a Temporal workflow

a Temporal child workflow

a Temporal activity executed by a Python worker service

a human review task suspended in workflow until decision resolution

Agents are logical capability boundaries, not independent runtime authorities.
5.2 Planner
The Planner shall be implemented as workflow logic plus supporting planning activities. The Planner may:
inspect current case state

inspect missing prerequisites

determine the required task graph

schedule specialist execution

request clarification or safe-stop

assemble work for reviewer submission

The Planner shall not directly mutate authoritative case state outside the allowed workflow transition path.
5.3 Specialist agents
Specialist agents shall be implemented as typed activities or child workflows. Typical specialist agents include but are not limited to:
Intake

Jurisdiction Resolution

Zoning and Code Research

Incentive Research

Compliance Evaluation

Document Generation

Submission Preparation

Submission Tracking

Comment Resolution

Evidence Assembly

Each specialist execution unit shall produce structured outputs, evidence references, confidence or quality metadata where applicable, and explicit failure status.
5.4 Reviewer
The Reviewer shall not be implemented as an autonomous worker with final authority. Reviewer authority shall be exercised through a separate human review service and UI/API surface. The Temporal workflow may pause on a review gate and await a reviewer decision, but the review decision itself shall be authored through the dedicated reviewer path.
5.5 State transition guard
All authoritative case-state mutation shall pass through an explicit state transition guard. The guard shall validate:
prerequisite completion

review approval where required

invariant satisfaction

contradiction handling status

artifact completeness

policy compliance

release-gated checks where applicable

No specialist worker shall be permitted to advance case state by itself.
6. Runtime component model
6.1 Temporal cluster
Temporal is the authoritative workflow engine. It is responsible for:
durable workflow execution

timers and waiting states

retry policy execution

activity scheduling

child workflow coordination

execution history retention according to policy

recovery after worker or service failure

6.2 Python worker services
Python worker services shall execute activities and child workflow logic. Workers shall be separated by capability domain where practical, for example:
intake workers

research workers

compliance workers

document workers

submission workers

tracking workers

Workers shall remain stateless except for temporary processing state. Authoritative state shall be externalized to approved stores.
6.3 Postgres
Postgres shall serve as the authoritative relational system of record for structured SPS state, including:
permit case records

normalized project facts

jurisdiction assignments

review records

contradictions and resolutions

policy and rule version references

release applicability records

state transition records

audit index metadata

Temporal history is authoritative for execution sequence. Postgres is authoritative for persistent business state unless a narrower source of truth is explicitly declared for a field or artifact.
6.4 Object storage
S3-compatible object storage shall hold durable files and evidence artifacts, including:
generated forms

submission bundles

research evidence packages

manifests

exported traceability artifacts

reviewer attachments

portal receipts

machine-generated intermediate artifacts when retention is required

Stored artifacts shall be content-addressable or otherwise durably identifiable, and references shall be recorded in Postgres.
6.5 Reviewer service and UI
A dedicated reviewer service and UI shall provide:
work queue for pending reviews

access to evidence and generated artifacts

contradiction display

approval, reject, return-for-rework, and escalation actions

reviewer identity and timestamp capture

rationale recording where required

independence and policy checks where required by governance

6.6 LLM adapter layer
All model calls shall pass through an internal adapter layer. The adapter layer shall abstract provider-specific details and expose a controlled internal contract for:
prompt invocation

model selection

temperature or equivalent settings where allowed

response capture

token and cost telemetry

redaction and policy hooks

citation or evidence attachment handling where applicable

error normalization

No workflow or worker shall directly depend on a vendor-specific agent SDK as a normative control surface.
7. Workflow structure
7.1 Top-level workflow
Each permit case shall run under a top-level workflow, for example:
PermitCaseWorkflow

This workflow is the durable controller for the case lifecycle.
7.2 Child workflows and activity groups
The top-level workflow may invoke child workflows or grouped activities for major lifecycle segments, including:
intake and normalization

jurisdiction and authority resolution

research and evidence collection

compliance analysis

incentive analysis

application and document generation

reviewer gate processing

submission and receipt capture

submission tracking

AHJ comment handling

correction and resubmission

closure, withdrawal, or rollback handling

7.3 Human gating
Where human review is required, the workflow shall enter an explicit waiting state. The pending gate shall identify:
required reviewer role

review scope

deadline or SLA if applicable

required artifact set

case state at pause

acceptable resolution actions

8. Contracts and schemas
Every workflow input, activity input, activity output, review payload, state transition payload, and artifact manifest shall conform to a typed schema.
These schemas shall define at minimum:
required fields

optional fields

enum-constrained state values where applicable

evidence references

source identifiers where applicable

timestamps

version metadata

failure codes or structured error objects where applicable

Pydantic models or equivalent validated schemas shall be used in implementation. JSON serialization formats may be used for interchange, but runtime validation is mandatory at all trust boundaries.
9. Failure handling and retries
9.1 General principle
Failures shall be classified as:
transient

deterministic recoverable

deterministic unrecoverable

policy-blocked

dependency-unavailable

contradiction-requiring-review

Retry behavior shall be policy-driven and explicit.
9.2 Temporal retry use
Temporal retry policies shall be used for transient activity failures such as:
temporary network failures

portal timeouts

intermittent upstream service issues

short-lived provider errors

Retries shall not be used to hide deterministic schema failures, policy violations, or contradiction states.
9.3 Safe-stop behavior
When required inputs are missing, external systems are unsupported, policy constraints are triggered, or contradictions cannot be safely resolved, the workflow shall safe-stop or route to review according to the governing policy.
10. Idempotency and replay
All externally visible side effects shall be idempotent or guarded by idempotency keys where feasible. This includes:
portal submissions

document generation with authoritative artifact registration

notifications

external case updates

payment-related interactions if later introduced

Workflow and activity design shall preserve safe replay behavior consistent with Temporal execution semantics.
11. Observability and audit
The runtime shall produce sufficient telemetry and artifacts to support:
workflow execution trace reconstruction

activity start and completion history

retry history

review gate timing

artifact lineage

source evidence lineage

state transition causality

model invocation observability subject to confidentiality rules

operator incident analysis

Observability data shall not replace required authoritative artifacts. It is supporting evidence, not normative state.
12. Security and authority boundaries
The runtime architecture shall preserve the following authority boundaries:
workers may compute outputs but may not unilaterally authorize controlled state advancement

reviewer authority shall be separately authenticated and recorded

state transitions shall be guarded by explicit validation logic

provider-specific model access shall be encapsulated behind the adapter layer

secrets shall not be embedded in workflow definitions or artifacts

policy-sensitive prompts, outputs, and evidence shall follow package confidentiality and retention rules

13. Non-goals
The following are explicitly not the SPS harness:
ad hoc chat loops between agents

vendor-branded multi-agent orchestration frameworks as the source of truth

unmanaged queue consumers without durable workflow history

direct model-to-model autonomous authority for case-state mutation

reviewer approval inferred from agent consensus

Such mechanisms may be used only as internal implementation details beneath the approved harness and only where they do not weaken auditability, determinism of control flow, or authority boundaries.
14. Implementation constraints
Any implementation claiming conformance to this package shall satisfy the following:
the authoritative workflow engine is Temporal

workflow progression is durable and replayable

case-state mutation is explicitly guarded

review gates are durable and auditable

specialist execution units use typed contracts

business state is persisted outside ephemeral worker memory

artifacts and evidence are durably referenced

model providers are replaceable without rewriting workflow doctrine

no uncontrolled agent autonomy exists over authoritative mutation paths

15. Conformance statement
An SPS runtime implementation is conformant only if it realizes the logical agent model through the harness and constraints defined in this section. Substituting a different orchestration engine, allowing direct worker-controlled case advancement, or making a vendor-specific agent SDK the authoritative runtime control surface constitutes a material architectural deviation and requires formal spec revision approval.

## Implementation profile

Implementation Profile
1. Profile purpose
This profile converts the runtime binding into an implementation-concrete operating profile. It defines the minimum deployable shape of SPS, the required runtime responsibilities of each component, and the conformance expectations for production-grade operation.
This profile is normative unless a stricter environment-specific profile is approved.
2. Implementation profile identifier
3. Required runtime components
A conformant SPS deployment shall include the following minimum components:
3.1 Temporal service
Responsible for:
workflow durability

workflow timers

activity scheduling

child workflow coordination

replay

retry semantics

pause and resume at review gates

3.2 SPS workflow service
Responsible for:
top-level permit case workflows

task graph planning coordination

state transition requests

workflow-level compensation handling

child workflow invocation

review wait-state coordination

3.3 Specialist worker services
Responsible for domain-specific activity execution. Worker pools may be separated by capability and load profile, including:
intake and extraction workers

jurisdiction and authority workers

research workers

compliance workers

incentive workers

document generation workers

submission workers

tracking workers

evidence assembly workers

3.4 Reviewer service and UI
Responsible for:
review queue presentation

evidence and artifact access

contradiction review

reviewer action capture

rationale and dissent capture

approval/rejection/escalation actions

identity and timestamp recording

3.5 State transition guard service
Responsible for:
invariant validation

transition precondition checks

artifact completeness checks

required-review enforcement

contradiction resolution status checks

policy applicability checks

This service is the final mutation gate before case-state advancement.
3.6 Postgres
Responsible for authoritative structured data persistence, including:
case records

normalized facts

review records

contradiction records

policy references

transition ledger

evidence index metadata

release applicability references

3.7 Artifact and evidence store
Responsible for durable storage of:
generated forms

export bundles

reviewer attachments

research packets

manifests

portal receipts

traceability exports

3.8 LLM adapter service
Responsible for:
model invocation abstraction

provider routing

request/response normalization

telemetry capture

redaction hooks

policy hooks

error normalization

model capability configuration

3.9 Integration adapter services
Responsible for controlled interaction with external systems such as:
AHJ portals

parcel or zoning data sources

incentive data sources

notification systems

document rendering tools

retrieval sources

4. Minimum deployment topology
A minimum production deployment shall include:
one Temporal cluster or managed Temporal environment

one workflow service deployment

one or more Python worker deployments

one reviewer service deployment

one Postgres deployment with backup and recovery policy

one S3-compatible storage deployment or managed equivalent

one LLM adapter deployment

one observability stack covering logs, metrics, and traces

Single-node development deployment is permitted for non-production environments only.
5. Environment profiles
5.1 Local development
Permitted characteristics:
local Temporal instance

local Postgres

local object storage emulator

mock integrations

reduced retention

test-only credentials

Not sufficient for production claims.
5.2 Staging
Required characteristics:
workflow replay testing enabled

schema validation enabled

representative integration mocks or limited real endpoints

reviewer flow exercised

rollback and compensation tests executed

5.3 Production
Required characteristics:
durable backed-up Postgres

durable object storage

authenticated reviewer UI

full observability

release-gated workflow versioning

auditable identity on reviewer actions

policy-controlled secrets handling

retention and legal hold controls where applicable

6. Mandatory implementation controls
A conformant implementation shall enforce:
typed validation at every workflow/activity boundary

reviewer gating before protected transitions

explicit invariant checks before state mutation

durable correlation IDs across workflow, DB, and artifact references

idempotency protection on external side effects

provider abstraction for model access

explicit error classification

evidence linkage from conclusions to sources where required by task type

7. Prohibited implementation shortcuts
The following are non-conformant:
allowing worker code to directly advance authoritative case state without the state transition guard

storing authoritative case state only in Temporal workflow memory

allowing reviewer outcomes to be inferred rather than explicitly recorded

allowing model-provider SDK abstractions to become the workflow source of truth

using untyped free-form payloads across authoritative boundaries

treating logs alone as sufficient audit evidence

8. Versioning and evolution rules
Runtime component changes that do not alter authority boundaries may be treated as implementation revisions. The following changes require formal spec revision or approved architectural addendum:
replacing Temporal as authoritative harness

removing human review where currently mandatory

changing state transition authority model

allowing direct autonomous mutation by specialist workers

making a vendor agent SDK the normative orchestration layer

weakening typed contract enforcement


Component Diagram Text
1. Purpose
This section provides a canonical text representation of the runtime component model. It is intended for direct conversion into diagram form without changing the architecture.
2. Component diagram text
SPS Runtime Architecture

[User / Operator / Reviewer]
    |
    v
[Reviewer UI/API] <----------------------------------------------+
    |                                                           |
    | reviewer decisions                                        |
    v                                                           |
[Reviewer Service]                                               |
    |                                                           |
    | review outcomes / rationale / dissent                     |
    v                                                           |
[State Transition Guard] ----------------------------------+    |
    |                                                      |    |
    | validated transition requests                        |    |
    v                                                      |    |
[Postgres: Authoritative Case Store]                       |    |
                                                           |    |
                                                           |    |
[Workflow API / SPS Workflow Service] ---------------------+----+
    |
    | starts / signals / queries workflows
    v
[Temporal Harness]
    |
    +--> [PermitCaseWorkflow]
            |
            +--> planning logic
            |
            +--> [Child Workflow: Intake / Normalization]
            |
            +--> [Child Workflow: Jurisdiction / Authority]
            |
            +--> [Child Workflow: Research / Evidence]
            |
            +--> [Child Workflow: Compliance / Incentives]
            |
            +--> [Child Workflow: Document Generation]
            |
            +--> [Review Wait State]
            |
            +--> [Child Workflow: Submission / Tracking]
            |
            +--> [Child Workflow: Comment Resolution / Resubmission]
            |
            +--> [Closure / Withdrawal / Rollback Path]

[Temporal Harness]
    |
    +--> schedules activities to Python workers
            |
            +--> [Intake Workers]
            +--> [Research Workers]
            +--> [Compliance Workers]
            +--> [Incentive Workers]
            +--> [Document Workers]
            +--> [Submission Workers]
            +--> [Tracking Workers]
            +--> [Evidence Workers]

[Python Workers]
    |
    +--> read/write structured state refs ----------------------> [Postgres]
    |
    +--> read/write artifacts ---------------------------------> [Object Storage]
    |
    +--> model calls ------------------------------------------> [LLM Adapter]
    |
    +--> external data / portal calls -------------------------> [Integration Adapters]

[LLM Adapter]
    |
    +--> [OpenAI or other provider]
    +--> [Local / alternate model provider]

[Integration Adapters]
    |
    +--> [AHJ Portals]
    +--> [Zoning / Parcel Sources]
    +--> [Incentive Sources]
    +--> [Notification Services]
    +--> [Document Rendering Services]

[Observability Stack]
    ^
    |
    +--- logs / metrics / traces / audit-supporting telemetry from:
         [Workflow Service]
         [Temporal]
         [Python Workers]
         [Reviewer Service]
         [State Transition Guard]
         [LLM Adapter]
         [Integration Adapters]

Authority model:
- Workers compute.
- Reviewer approves or rejects.
- State Transition Guard validates.
- Temporal orchestrates.
- Postgres records authoritative structured state.
- Object storage holds durable artifacts.
3. Diagram interpretation rules
The following rules apply to any rendered version of this component diagram:
The reviewer path shall remain separate from specialist worker execution.

The state transition guard shall remain visually and logically distinct from workers.

Temporal shall appear as the authoritative orchestrator.

Postgres shall be shown as authoritative structured state, not just a cache.

Object storage shall be shown as the durable artifact store.

Model providers shall remain behind the LLM adapter abstraction.


Agent-to-Runtime Mapping Table
1. Purpose
This table binds each logical SPS agent or control role to its runtime realization. It eliminates ambiguity about what is a workflow role, what is a worker activity, and what is a human-controlled authority.
2. Mapping table
3. Interpretation notes
3.1 Planner is not a free-standing autonomous authority
The Planner decides what work should happen next, but it does not have unilateral authority to advance case state.
3.2 Reviewer is not replaced by agent consensus
No combination of specialist outputs substitutes for a required reviewer action where the policy or state machine requires review.
3.3 State Transition Guard is the mutation choke point
All protected state advancement must pass through the guard. This is the core authority boundary in the runtime.
3.4 Submission is externally consequential
Because submission affects outside systems, the submission path must be both idempotent and gated. It is not just another worker task.

Optional drop-in conformance clause
You can append this immediately after the mapping table if you want the section to close hard:
Runtime conformance clause
Any implementation that represents SPS as a free-form multi-agent conversation framework, permits specialist workers to advance authoritative state without the state transition guard, or collapses reviewer authority into automated consensus is non-conformant with this package.
Any implementation that substitutes a vendor-specific agent SDK for Temporal as the authoritative workflow harness is a material architectural deviation and requires formal approval.
