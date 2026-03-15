---
artifact_id: ART-SPS-RUNBOOK-002
authoritative_or_informative: authoritative
authored_or_generated: authored
consumer_list: [operators, release_managers, audit]
owner: Operations Lead
freshness_expectation: update when adapter failure policy changes
failure_if_missing: operator_execution_degraded
---

# Submission failure

## Trigger
- submission adapter returns retryable or ambiguous failure

## Required diagnostics
- adapter response classification
- idempotency key
- correlation id
- receipt lookup result
- external portal state if queryable
- current package digest verification result
- current contradiction state
- recent retry history for the same submission attempt

## Exact operator actions
1. Classify failure.
2. Retry only if the class is transient and policy permits.
3. If external state is ambiguous, stop automatic retries.
4. Create incident if ambiguity persists.
5. Require operator investigation before any manual action.
6. Route to manual fallback only through the approved fallback path when support-level and proof policy allow it.

## Forbidden actions
- blind retry after ambiguous external state
- second submission without idempotency review
- marking submitted without verified proof
- reusing receipts or proof artifacts from a different package version

## Escalation owner
- Operations Lead or on-call manager
- Release Manager if release or rollout artifact integrity is implicated

## Success criteria
- case remains in bounded pending, blocked, or manual state
- no ambiguous duplicate submission is created
- incident linkage exists where ambiguity persists

## Closure evidence
- updated SubmissionAttempt classification
- incident artifact when ambiguity persists
- retry history or manual fallback linkage
- state change audit event when final disposition is reached
