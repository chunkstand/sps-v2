# Architecture Research

**Domain:** permit case workflow + release bundle management
**Researched:** 2026-03-17
**Confidence:** MEDIUM

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         API + Auth Layer                                 │
├──────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────────┐  ┌─────────────────────────────┐  │
│  │ Case API    │  │ Release Bundle   │  │ Admin/Verification API        │  │
│  │ (Intake/UI) │  │ API (manifests)  │  │ (policies, audits, paging)    │  │
│  └──────┬──────┘  └─────────┬────────┘  └──────────────┬──────────────┘  │
│         │                   │                          │                 │
├─────────┴───────────────────┴──────────────────────────┴────────────────┤
│                     Workflow + Orchestration Layer                        │
├──────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌───────────────────┐  ┌───────────────────────┐  │
│  │ Workflow Engine  │  │ Task/Activity     │  │ Evidence Registry      │  │
│  │ (BPMN/CMMN)      │  │ Workers           │  │ Adapter                │  │
│  └─────────┬────────┘  └──────────┬────────┘  └───────────┬───────────┘  │
│            │                      │                        │              │
├────────────┴──────────────────────┴────────────────────────┴────────────┤
│                     Release + Verification Layer                          │
├──────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │ Bundle Builder   │  │ Manifest/Registry │  │ Verification/Policy    │  │
│  │ (OCI artifact)   │  │ Client            │  │ Engine (attest/sig)    │  │
│  └─────────┬────────┘  └──────────┬────────┘  └───────────┬───────────┘  │
│            │                      │                        │              │
├────────────┴──────────────────────┴────────────────────────┴────────────┤
│                          Data + Audit Layer                               │
├──────────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌──────────────┐          │
│  │ Case DB  │  │ Evidence  │  │ Manifest   │  │ Audit/Event  │          │
│  │          │  │ Store     │  │ Store/OCI  │  │ Log          │          │
│  └──────────┘  └───────────┘  └────────────┘  └──────────────┘          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Case API | Intake, case state views, human actions, pagination | REST/GraphQL with RBAC + rate limits |
| Workflow Engine | Orchestrate case steps, timers, retries, compensation | BPMN/CMMN engine or durable workflow system |
| Task/Activity Workers | Execute external calls, validations, data fetches | Worker pool with idempotent activities |
| Evidence Registry Adapter | Write/read evidence records with integrity | Adapter to evidence registry, signed events |
| Bundle Builder | Build release bundle and manifest graph | OCI artifact packaging + metadata composition |
| Manifest/Registry Client | Fetch/verify manifests/blobs, pagination | OCI Distribution API client |
| Verification/Policy Engine | Verify signatures, attestations, policy rules | SLSA/in-toto/Sigstore verification pipeline |
| Audit/Event Log | Immutable trace of workflow + release actions | Append-only log + event bus |
| Case/Evidence/Manifest Stores | Durable storage for state + artifacts | RDBMS + object store + OCI registry |

## Recommended Project Structure

```
src/
├── api/                   # HTTP handlers, auth middleware, pagination
│   ├── cases/              # Case intake + retrieval
│   ├── bundles/            # Bundle and manifest endpoints
│   └── admin/              # Policy and audit endpoints
├── workflows/             # BPMN/CMMN or workflow definitions
│   ├── case/               # Permit case state machine
│   └── release/            # Release bundle workflows
├── workers/               # Activity implementations
│   ├── registry/           # Manifest and blob retrieval
│   ├── evidence/           # Evidence registry IO
│   └── verification/       # Signature/attestation checks
├── bundles/               # Bundle builder and manifest assembly
├── policy/                # Verification rules and policy evaluation
├── auth/                  # AuthN/AuthZ, service identities
├── storage/               # DB, object store, registry clients
├── events/                # Event bus + outbox logic
└── observability/         # Audit, metrics, tracing
```

### Structure Rationale

- **workflows/:** isolates long-running state transitions from API surface.
- **workers/ + bundles/:** separates orchestration from execution and artifact assembly.

## Architectural Patterns

### Pattern 1: Case-Oriented Workflow (BPMN/CMMN)

**What:** Model permit processing as a case with stages, tasks, and milestones.
**When to use:** Multi-step, human + automated tasks with evidence and approvals.
**Trade-offs:** Strong traceability and replayability, but requires careful versioning.

**Example:**
```typescript
// Pseudo-workflow: acquire evidence, validate bundle, approve
await workflow.stage("intake");
const evidenceId = await activities.recordEvidence(caseId, input);
const bundle = await activities.buildBundle(caseId, evidenceId);
await activities.verifyBundle(bundle.digest);
await workflow.stage("approval");
```

### Pattern 2: OCI Artifact Bundle + Referrers

**What:** Represent a release bundle as an OCI manifest with subject/referrers links.
**When to use:** Need verifiable, content-addressed bundles with attached attestations.
**Trade-offs:** Requires registry support for referrers API or fallback tag schema.

**Example:**
```typescript
// Bundle manifest points to bundle artifacts and references subject digest
const manifest = {
  mediaType: "application/vnd.oci.image.manifest.v1+json",
  artifactType: "application/vnd.sps.bundle.v1",
  subject: { digest: imageDigest, mediaType: "application/vnd.oci.image.manifest.v1+json" },
  layers: bundleLayers
};
```

### Pattern 3: Attestation-Driven Verification

**What:** Verify bundle integrity using attestations (SLSA/in-toto) and signatures.
**When to use:** Strong end-to-end provenance and tamper detection required.
**Trade-offs:** More moving parts (key management, policy updates, transparency logs).

## Data Flow

### Request Flow

```
Case Intake
    ↓
Case API → Workflow Engine → Activity Workers → Evidence Registry
    ↓                ↓                 ↓             ↓
Case Status ← State Store ← Bundle Builder ← Manifest/Registry Client
    ↓                                   ↓
Release Bundle API ← Verification/Policy Engine ← Signatures/Attestations
```

### State Management

```
Event Log/Outbox
    ↓ (publish)
Projections (Case View, Bundle View, Audit)
    ↓ (query)
APIs/UI
```

### Key Data Flows

1. **Permit case progression:** intake → workflow stage → activity execution → evidence registry write → case state update.
2. **Release bundle validation:** build bundle → fetch manifests/blobs → verify signatures/attestations → record verification evidence.
3. **Manifest retrieval:** API request → registry client (pagination + content negotiation) → verification engine → response with provenance.

## Build Order Implications

1. **Core workflow + case state model** must land first; all downstream components hang off case transitions.
2. **Manifest/registry client + bundle builder** next, so workflow can produce bundle outputs.
3. **Verification/policy engine + evidence registry adapter** next to make bundles verifiable and auditable.
4. **Release bundle API + pagination + admin/policy surfaces** last, once integrity guarantees exist.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k cases | Single workflow engine + shared DB is fine |
| 1k-100k cases | Split workers, add queueing, shard evidence store |
| 100k+ cases | Separate registry client tier, caching, dedicated audit log storage |

### Scaling Priorities

1. **First bottleneck:** registry/manifest fetches → add caching + pagination + retry budgets.
2. **Second bottleneck:** evidence writes → batch/async with outbox + backpressure.

## Anti-Patterns

### Anti-Pattern 1: In-place Manifest Mutation

**What people do:** Update manifests or bundle metadata after publication.
**Why it's wrong:** Breaks content-addressability and verification guarantees.
**Do this instead:** Treat bundles as immutable; publish a new bundle with new digest.

### Anti-Pattern 2: Verification Only at Publish

**What people do:** Validate once at publish time but skip on retrieval.
**Why it's wrong:** Allows tampering or drift in downstream consumers.
**Do this instead:** Verify on every retrieval and record evidence per request.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| OCI Registry | Distribution API (manifests, blobs, referrers) | Requires pagination + content negotiation |
| Evidence Registry | Signed evidence write/read | Ensure idempotent writes + hash linking |
| Signing/Transparency | Sigstore/Cosign + log | Bundle signatures and attestations |
| Identity Provider | OIDC/JWT | Service identity for workflow + workers |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| API ↔ Workflow Engine | Command + query APIs | Enforce auth and idempotency tokens |
| Workflow Engine ↔ Workers | Task queue | Use retries and deterministic inputs |
| Bundle Builder ↔ Verification | In-process API | Strict schema + digest checks |

## Sources

- https://www.omg.org/spec/BPMN/2.0/About-BPMN/
- https://www.omg.org/spec/CMMN/1.1/About-CMMN/
- https://github.com/opencontainers/image-spec/blob/main/manifest.md
- https://github.com/opencontainers/distribution-spec/blob/main/spec.md
- https://docs.sigstore.dev/about/overview/
- https://slsa.dev/spec/v1.2/
- https://in-toto.io/docs/specs/
- https://spdx.dev/use/specifications/

---
*Architecture research for: permit case workflow + release bundle management*
*Researched: 2026-03-17*
