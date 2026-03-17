# Pitfalls Research

**Domain:** Permit case workflow and release bundle management (SPS V2)
**Researched:** 2026-03-17
**Confidence:** MEDIUM

## Critical Pitfalls

### Pitfall 1: Trusting tags over digests in bundle validation

**What goes wrong:**
Release bundles resolve tags to manifests without verifying digests or `mediaType`, so a tag move or registry mismatch yields the wrong artifact.

**Why it happens:**
Teams treat tags as stable identifiers and skip digest checks or content-type negotiation in the manifest retrieval path.

**How to avoid:**
Always retrieve by digest when possible; verify `Docker-Content-Digest` or manifest digest matches the requested digest; enforce `mediaType` and `Content-Type` match; record digests in release manifests and verify on every fetch.

**Warning signs:**
Manifest responses missing digest verification, acceptance of `latest`, or a bundle validates even when a tag is repointed.

**Phase to address:**
Phase 1: Release bundle validation and manifest retrieval.

---

### Pitfall 2: Incomplete pagination for tags/referrers

**What goes wrong:**
Bundle discovery misses SBOMs, attestations, or associated artifacts because pagination (Link headers or `last` cursor) is ignored.

**Why it happens:**
Registries vary in pagination behavior; implementations assume a single page or only use `n` without following `Link`.

**How to avoid:**
Implement RFC5988 `Link` header pagination for tags and referrers; add cursor-based fallback (`last`) where supported; test with large tag and referrer sets.

**Warning signs:**
Missing artifacts in larger repositories, inconsistent counts between environments, or tests only passing on small datasets.

**Phase to address:**
Phase 3: Pagination and content discovery hardening.

---

### Pitfall 3: Evidence not cryptographically bound to workflow steps

**What goes wrong:**
Workflow evidence exists, but it is not signed or bound to a step identity, allowing replay or substitution across permit cases.

**Why it happens:**
Evidence is stored as generic logs rather than signed attestations that encode who did what and in which order.

**How to avoid:**
Use signed attestations per step with explicit identities and expected step ordering; store evidence in a tamper-evident log; validate materials/products linkage for each step.

**Warning signs:**
Evidence records lack signature/identity metadata, or the same evidence can be reused across cases without detection.

**Phase to address:**
Phase 2: Workflow evidence registry integration.

---

### Pitfall 4: Collecting provenance without enforcing verification gates

**What goes wrong:**
Provenance and attestations are collected but not enforced as release gates, leading to approvals without verified supply chain evidence.

**Why it happens:**
Verification policies are deferred or considered optional, especially under schedule pressure.

**How to avoid:**
Define mandatory verification checks for release bundle approval (provenance presence, signer identity, and attestation validity); fail closed when checks are missing.

**Warning signs:**
Manual overrides become common, or bundles pass validation with missing provenance.

**Phase to address:**
Phase 1: Release bundle validation and policy enforcement.

---

### Pitfall 5: Auth scoping too broad for bundle and evidence actions

**What goes wrong:**
Single credentials or overly broad roles can read/write bundles and evidence, enabling unauthorized edits or approvals.

**Why it happens:**
Early implementations favor convenience over least privilege; signing and verification paths share identities.

**How to avoid:**
Separate signer, verifier, and approver identities; scope tokens to repository and operation; require strong identity binding for signatures; log and audit all privileged actions.

**Warning signs:**
Shared tokens across services, manual edits to evidence or bundle metadata, or missing audit trails.

**Phase to address:**
Phase 3: Auth hardening and auditability.

---

### Pitfall 6: Media type ambiguity in manifest handling

**What goes wrong:**
System assumes a single manifest type and mis-parses OCI image indexes or non-image artifacts, causing mismatched bundle contents.

**Why it happens:**
Content negotiation and `mediaType` verification are skipped or treated as best-effort.

**How to avoid:**
Use `Accept` headers for supported manifest types, verify `mediaType` matches `Content-Type`, and handle index vs manifest properly.

**Warning signs:**
Validation works for some artifacts but fails on multi-arch or non-image artifacts; inconsistent behavior across registries.

**Phase to address:**
Phase 1: Manifest retrieval correctness.

---

### Pitfall 7: Evidence replay due to missing expiry or layout trust roots

**What goes wrong:**
Old or replayed evidence is accepted for new permit cases, undermining integrity of the workflow.

**Why it happens:**
Evidence does not carry expiry, nonce, or trusted layout roots, and verification ignores freshness.

**How to avoid:**
Require evidence timestamps and expirations, verify against trusted layout keys, and reject stale evidence; use immutable logs to detect replays.

**Warning signs:**
Evidence can be attached without new signing events; audits show repeated evidence IDs across cases.

**Phase to address:**
Phase 2: Evidence registry integration and verification.

---

### Pitfall 8: SBOMs not aligned with released artifacts

**What goes wrong:**
SBOMs are attached but do not reflect the exact artifacts in the release bundle, leading to false compliance and vulnerability gaps.

**Why it happens:**
SBOMs are generated separately and not tied to bundle digests or manifest contents.

**How to avoid:**
Bind SBOMs to bundle digests and verify component lists against the actual manifest; enforce SBOM format and version expectations.

**Warning signs:**
SBOMs list components that are not in the bundle, or bundles pass validation without an SBOM attached.

**Phase to address:**
Phase 1: Release bundle validation.

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip digest verification and trust tags | Faster integration | Bundle integrity can be subverted | Never |
| Store evidence without signatures | Simple logging | Evidence replay and weak audit trails | Never |
| Only validate first page of tags/referrers | Quick implementation | Missing attestations at scale | Never |
| Allow manual approval without verification gates | Operational flexibility | Compliance drift and security gaps | Only with documented break-glass controls |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| OCI registry | Ignore `Link` header pagination for tags/referrers | Implement `Link` pagination and `last` cursor fallback |
| OCI manifest retrieval | Accept any `Content-Type` without `mediaType` check | Require `mediaType` and `Content-Type` match |
| Sigstore verification | Verify signature but skip transparency log inclusion | Verify identity, signature, and transparency log inclusion |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| N+1 registry fetches per bundle | Slow validation, timeouts | Batch manifest retrieval, cache digests | Hundreds of artifacts per bundle |
| Evidence registry without indexed queries | Slow case review | Index by case ID, artifact digest, and step | Thousands of cases |
| Full re-validation on every read | Excess CPU | Cache verification summaries with expiry | High read volumes |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Accept unsigned or unverifiable attestations | Forged evidence | Require signed attestations and verify identity |
| Reuse long-lived signing keys across services | Key compromise blast radius | Separate identities, prefer ephemeral or short-lived keys |
| Skip transparency log verification | Undetected tampering | Verify inclusion proofs and log consistency |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Hide which evidence is missing | Approvals with blind spots | Show required evidence checklist per case |
| Fail to explain verification errors | Workarounds and overrides | Provide actionable error details and remediation steps |
| No traceability view from permit case to bundle | Hard to audit | Provide end-to-end trace from case to manifest digest |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Release bundle validation:** Missing digest verification — verify `Docker-Content-Digest` and `mediaType`.
- [ ] **Manifest retrieval:** No pagination follow-through — verify `Link` header handling for tags/referrers.
- [ ] **Evidence registry integration:** Evidence stored but unsigned — verify attestation signatures and identities.
- [ ] **Auth hardening:** Same credentials for sign and verify — verify separated roles and scoped tokens.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Tag-based bundle validation | MEDIUM | Recompute bundle digests, invalidate approvals, re-verify by digest |
| Missing pagination | LOW | Re-run discovery with pagination, backfill missing attestations |
| Unsigned evidence accepted | HIGH | Quarantine affected releases, re-collect signed evidence, audit approvals |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Trusting tags over digests | Phase 1 | Integration tests that fail when tags repoint |
| Media type ambiguity | Phase 1 | Tests for index vs manifest parsing and `mediaType` checks |
| Collecting provenance without gating | Phase 1 | Policy tests that block release without required attestations |
| Evidence not bound to steps | Phase 2 | Evidence verification includes signer identity and step linkage |
| Evidence replay | Phase 2 | Tests that reject stale or duplicate evidence |
| Auth scoping too broad | Phase 3 | Role-based access tests and audit log assertions |
| Incomplete pagination | Phase 3 | Pagination tests with multi-page tag/referrer sets |
| SBOM mismatch | Phase 1 | SBOM-to-manifest consistency checks |

## Sources

- https://slsa.dev/spec/v1.2/
- https://docs.sigstore.dev/about/overview/
- https://raw.githubusercontent.com/in-toto/docs/master/in-toto-spec.md
- https://github.com/opencontainers/distribution-spec/blob/main/spec.md
- https://cyclonedx.org/specification/overview/

---
*Pitfalls research for: permit case workflow and release bundle management*
*Researched: 2026-03-17*
