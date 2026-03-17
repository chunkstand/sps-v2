# SPS V2 Reliability Hardening

## What This Is

This project tightens reliability, security, and performance in the SPS V2 permit case system. It focuses on resolving documented concerns in release bundles, case workflows, API routes, and test coverage so existing clients can trust manifests and workflow state.

## Core Value

Permit case releases and manifests are accurate, verifiable, and secure end to end.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Release bundles fail fast on missing artifacts or identifiers
- [ ] Case manifest retrieval returns the persisted manifest, not a synthetic placeholder
- [ ] Document package workflows advance to `DOCUMENT_COMPLETE` with evidence registry readback verified
- [ ] Legacy reviewer API key access is removed or strictly constrained with mTLS enforcement
- [ ] Case and review list endpoints enforce pagination limits and ordering
- [ ] Permit case workflow transitions are modularized with focused tests for override/contradiction logic
- [ ] Case API routes and DTO mapping are split into smaller, domain-specific modules

### Out of Scope

- New product features outside the concerns audit — focus is stabilization
- UI redesigns or frontend feature work — backend reliability first
- Replatforming the service stack — existing architecture remains

## Context

The current SPS V2 codebase has a concerns audit highlighting missing manifest validation, placeholder manifest responses, workflow/evidence registry gaps, legacy auth bypasses, unbounded list queries, and fragile transition logic. These issues create release correctness risk, security exposure, and high regression potential in permit workflows.

## Constraints

- **Compatibility**: Preserve existing API contracts and release bundle formats — downstream systems depend on them
- **Security**: Changes must not weaken JWT/mTLS protections or expand legacy access

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Scope work to the concerns audit first | The current risks are correctness and security related | — Pending |

---
*Last updated: 2026-03-17 after initialization*
