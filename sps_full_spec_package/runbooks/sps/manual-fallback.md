---
artifact_id: ART-SPS-RUNBOOK-001
authoritative_or_informative: authoritative
authored_or_generated: authored
consumer_list: [operators, reviewers, audit]
owner: Operations Lead
freshness_expectation: update when fallback policy changes
failure_if_missing: operator_execution_degraded
---

# Unsupported portal manual fallback

## Trigger
- adapter returns `UNSUPPORTED_WORKFLOW`
- portal support metadata is `UNSUPPORTED`
- operator confirms configured portal family does not support required submission path
- automated submission enters ambiguous state and fallback is explicitly approved

## Required diagnostics
- case_id
- active package_id
- active package_version
- manifest_id
- package digest verification result
- portal support metadata version
- adapter logs
- current review decision id
- current contradiction state
- current release profile

## Exact operator actions
1. Verify active package hash, manifest digest, and review decision still match the current package version.
2. Generate `ManualFallbackPackage`.
3. Determine channel type:
   - authoritative portal upload-only remainder
   - official authority email channel
   - official mailed or in-person submission path
   - utility-specific manual intake path
4. Execute only documented channel-specific fallback instructions for that authority.
5. Capture channel-appropriate proof artifacts.
6. Bind proof to the approved package hash.
7. Submit proof bundle for reviewer validation.
8. Transition case only after reviewer validates proof sufficiency.

## Forbidden actions
- manually marking `SUBMITTED` without validated proof bundle
- modifying package contents after reviewer approval without new review
- mixing proof from different package versions
- treating operator notes alone as sufficient proof
- treating a generic sent-email screenshot without authority correlation as sufficient proof

## Escalation owner
- Operations Lead
- Reviewer on duty for proof validation
- Escalation Owner when authority channel ambiguity persists

## Success criteria
- proof bundle corresponds to current approved package version
- reviewer validation exists
- audit event exists for state change

## Closure evidence
- ManualFallbackPackage
- proof bundle
- reviewer validation decision
- state change audit event
- contradiction artifact if proof ambiguity occurred
