---
artifact_id: ART-SPS-INTENT-001
authoritative_or_informative: authoritative
authored_or_generated: authored
consumer_list:
- builders
- reviewers
- release_managers
owner: Product Manager
freshness_expectation: update only on intent or scope change
failure_if_missing: review_invalid
---


# SPS implementation intent

## Intent statement

Build the Solar Permitting System as a governed planner -> specialist -> reviewer -> submission workflow for commercial solar and adjacent commercial energy projects.

## Binding intent limits

The build MUST preserve these binding limits:

- commercial scope only
- US-only scope in this package version
- no payment processing in v1
- no residential permitting in this package version
- no autonomous authority-bearing mutation by agents or models
- reviewer approval remains the permission gate for protected transitions
- unsupported portal workflows remain bounded manual fallback paths, not silent operator bypasses

## Why this build exists now

The system is intended to replace fragmented manual permitting operations with deterministic orchestration, queryable evidence, controlled submission, contradiction handling, and audit reconstruction.

## What constitutes intent drift

Any of the following requires new intent approval and spec revision:

- adding residential scope
- adding fee payment or payment capture
- weakening reviewer gates
- allowing specialist workers to mutate authoritative state directly
- removing runtime guards on binding control surfaces
- treating aggregator sources as authoritative
- making a vendor-specific agent SDK the authoritative harness
