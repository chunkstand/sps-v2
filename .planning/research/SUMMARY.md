# Project Research Summary

**Project:** SPS V2 Reliability Hardening
**Domain:** permit case workflow and release bundle management
**Researched:** 2026-03-17
**Confidence:** MEDIUM

## Executive Summary

This project hardens a permit case workflow system that also manages release bundle manifests, evidence, and verification. Experts build these systems with durable workflow orchestration, immutable artifact storage, and verifiable manifests/attestations so every decision and release can be audited end to end.

The recommended approach is to prioritize correctness and verification gates over new features: enforce digest- and mediaType-verified manifest retrieval, make bundles immutable and content-addressed, bind signed evidence to workflow steps, and use a policy gate that fails closed when provenance is missing. Architecturally, keep a clear separation between APIs, workflow orchestration, workers, bundle/manifest tooling, and audit/event logging, with OCI distribution patterns for artifacts.

The biggest risks are tag-based bundle validation, unsigned or replayable evidence, and incomplete pagination that silently misses attestations. Mitigate by always verifying digests and media types, requiring signed attestations with step identity and freshness checks, and implementing pagination for tags/referrers with robust tests. Keep auth scoped and auditable to prevent implicit overrides.

## Key Findings

### Recommended Stack

The stack centers on Python 3.13 with FastAPI for HTTP contracts, Temporal for durable workflows, PostgreSQL for authoritative case and audit state, Kafka for eventing, and S3-compatible object storage for immutable artifacts. Supporting libraries (SQLAlchemy, Alembic, Pydantic, asyncpg, boto3, PyJWT) cover transactional data, schema evolution, validation, and secure access. Versions are current and aligned with Python 3.10+ requirements for FastAPI and Temporal. See `.planning/research/STACK.md`.

**Core technologies:**
- Python 3.13.x: primary runtime — strong async and typing support
- FastAPI 0.135.1: API layer — OpenAPI-first validation and performance
- Temporal Server 1.30.1: workflow orchestration — durable, replayable workflows
- PostgreSQL 18.3: system of record — ACID + JSONB for manifests
- Apache Kafka 4.2.0: event log — ordered, durable audit streams
- Amazon S3 API (2006-03-01): object storage — immutable bundle storage

### Expected Features

Baseline expectations include structured case intake, workflow stages with approvals, evidence attachment, audit trails, manifest creation/retrieval, digest and signature verification, provenance/attestation capture, and strict access control. Differentiators center on end-to-end verifiable bundles, policy-as-code gating, and evidence registry integration. Defer transparency logs and analytics until core correctness is proven. See `.planning/research/FEATURES.md`.

**Must have (table stakes):**
- Case intake with workflow stages/approvals — regulatory workflows depend on this
- Evidence/document attachment + audit trail — traceability is required
- Manifest creation/retrieval — canonical bundle truth
- Digest + signature verification — baseline integrity
- Provenance/attestation capture — compliance expectations
- Access control — sensitive data protection

**Should have (competitive):**
- Policy-as-code gating — enforce provenance requirements
- Evidence registry integration across workflow and releases — single source of truth
- End-to-end verifiable bundles — integrity summary across manifest + attestations

**Defer (v2+):**
- Transparency-log publishing — high operational overhead
- Cross-case analytics/optimization — after core reliability is stable

### Architecture Approach

Use a layered system with APIs, workflow orchestration, workers, bundle/manifest tooling, verification/policy, and audit/event data stores. Apply case-oriented workflows for staged decisions, OCI artifact bundles with referrers for manifests/attestations, and attestation-driven verification. Build order should start with core workflow/state, then bundle/registry client, then verification/evidence integration, and finally admin/policy surfaces. See `.planning/research/ARCHITECTURE.md`.

**Major components:**
1. Case API + Admin/Verification API — intake, approvals, policy/audit endpoints
2. Workflow engine + workers — durable case transitions and idempotent activities
3. Bundle builder + registry client — deterministic manifests and retrieval
4. Verification/policy engine — signature/attestation checks and gating
5. Data + audit layer — case/evidence/manifest stores and append-only log

### Critical Pitfalls

Top pitfalls to avoid early:

1. **Trusting tags over digests** — always verify digest and mediaType on fetch
2. **Media type ambiguity** — enforce Accept/Content-Type and parse index vs manifest
3. **Unsigned or unbound evidence** — require signed attestations tied to step identity
4. **Provenance collected but not enforced** — fail closed on missing attestations
5. **Incomplete pagination for tags/referrers** — implement Link header and cursor support

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Manifest Correctness and Bundle Validation
**Rationale:** Core integrity guarantees must exist before any workflow approvals can be trusted.
**Delivers:** Digest-verified manifest retrieval, mediaType checks, bundle immutability, SBOM alignment checks, fail-fast validation.
**Addresses:** Manifest creation/retrieval, digest + signature verification, baseline provenance checks.
**Avoids:** Tag-based validation, mediaType ambiguity, SBOM mismatch, missing verification gates.

### Phase 2: Workflow Evidence Binding and Transition Hardening
**Rationale:** Evidence must be bound to workflow steps before approvals and audits are reliable.
**Delivers:** Signed evidence attestation per step, evidence readback verification, replay protection, modularized transitions with tests.
**Uses:** Workflow engine + evidence registry adapter, attestation verification.
**Avoids:** Unsigned evidence, evidence replay, weak audit linkage.

### Phase 3: Access Control, Pagination, and Audit Hardening
**Rationale:** Security and correctness regress at scale without scoped auth and pagination.
**Delivers:** Scoped identities for signer/verifier/approver, legacy API key restrictions with mTLS, strict pagination/ordering, audit assertions.
**Implements:** Auth layer, API pagination, audit/event log usage.
**Avoids:** Over-broad auth scopes, missing artifacts due to pagination gaps.

### Phase 4: Continuous Reconciliation and Traceability (Post-stabilization)
**Rationale:** Once integrity is stable, add ongoing drift detection and cross-case traceability.
**Delivers:** Periodic re-verification, cross-case-to-release trace links, operational alerts.
**Addresses:** Continuous reconciliation and traceability differentiators.

### Phase Ordering Rationale

- Verification correctness is a dependency for any downstream approvals and audits.
- Evidence binding must precede policy enforcement and auditability claims.
- Auth and pagination hardening reduce operational risk as usage grows.
- Reconciliation and traceability add value after core integrity is stable.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** Evidence registry attestation format, key management, and step-identity binding details.
- **Phase 3:** Legacy auth constraints and mTLS requirements with existing clients.
- **Phase 4:** Transparency log feasibility and operational overhead if promoted earlier.

Phases with standard patterns (skip research-phase):
- **Phase 1:** OCI manifest verification, digest/mediaType checks, SBOM alignment.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Based on official versioned docs and current releases. |
| Features | MEDIUM | Mix of domain expectations and inferred prioritization. |
| Architecture | MEDIUM | Standard patterns, but depends on existing SPS V2 constraints. |
| Pitfalls | MEDIUM | Well-known issues, but mitigation details need validation in codebase. |

**Overall confidence:** MEDIUM

### Gaps to Address

- Evidence registry schema and attestation format: confirm current data model and signing requirements before Phase 2.
- Registry capabilities (referrers, pagination behavior): validate against actual registries in use.
- Policy gating requirements: confirm which attestations are mandatory for release approval.
- Legacy auth boundary: clarify acceptable changes to reviewer API key flows and mTLS enforcement.

## Sources

### Primary (HIGH confidence)
- https://www.python.org/downloads/ — Python 3.13 status
- https://pypi.org/project/fastapi/ — FastAPI 0.135.1
- https://github.com/temporalio/temporal/releases/latest — Temporal Server 1.30.1
- https://www.postgresql.org/docs/current/ — PostgreSQL 18.3
- https://kafka.apache.org/community/downloads/ — Kafka 4.2.0
- https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html — S3 API
- https://github.com/opencontainers/image-spec/blob/main/manifest.md — OCI manifest
- https://github.com/opencontainers/distribution-spec/blob/main/spec.md — OCI distribution
- https://slsa.dev/spec/v1.2/ — SLSA provenance
- https://in-toto.io/docs/specs/ — in-toto attestations

### Secondary (MEDIUM confidence)
- https://docs.sigstore.dev/about/overview/ — Sigstore verification
- https://www.omg.org/spec/BPMN/2.0/About-BPMN/ — BPMN patterns
- https://www.omg.org/spec/CMMN/1.1/About-CMMN/ — CMMN patterns

---
*Research completed: 2026-03-17*
*Ready for roadmap: yes*
