---
artifact_id: ART-SPS-RUNBOOK-006
authoritative_or_informative: authoritative
authored_or_generated: authored
consumer_list: [operators, compliance, audit, security]
owner: Compliance Lead
freshness_expectation: update when retention or legal-hold policy changes
failure_if_missing: operator_execution_degraded
---

# Legal hold activation and release

## Trigger
- legal hold request from Compliance Counsel or General Counsel
- incident or audit finding indicating purge risk on regulated evidence
- pending litigation, regulatory inquiry, or formal preservation demand

## Required diagnostics
- linked case ids or evidence artifact ids
- legal hold reason and requesting authority
- retention classes currently applied
- pending purge jobs or retention workflows
- access restrictions required during hold

## Exact operator actions
1. Record legal hold request and authorizing party.
2. Apply `legal_hold=true` or stronger retention class to affected case and evidence records.
3. Halt purge or destructive delete workflows touching held records.
4. Verify hold propagation to storage, metadata index, and release evidence where applicable.
5. Notify affected owners and audit stakeholders.
6. Release hold only on documented counsel authorization and record the release event.

## Forbidden actions
- deleting or purging held evidence or case records
- applying a narrower retention class while hold is active
- releasing legal hold on verbal-only instruction

## Escalation owner
- Compliance Counsel
- Compliance Lead
- Security Lead if purge risk is caused by system fault or incident

## Success criteria
- purge jobs cannot delete held evidence
- affected records show legal-hold status consistently across authoritative stores
- release of hold is authorized and audited

## Closure evidence
- legal hold record or waiver
- storage-policy validation result
- purge-denial audit events where applicable
- hold release authorization when the hold ends
