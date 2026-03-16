# S01: Reviewer console MVP (queue + evidence + decision capture)

**Goal:** Deliver a minimal reviewer console that lists REVIEW_PENDING cases, exposes aggregated evidence summaries per case, and submits review decisions through the existing reviewer API.
**Demo:** A reviewer opens `/reviewer`, sees pending cases, drills into a case to view aggregated evidence metadata, and submits a decision that lands in the real `POST /api/v1/reviews/decisions` path.

## Planning Notes
- Grouping is driven by risk: API contract + evidence aggregation is the highest-risk data surface and needs tests; UI wiring is a separate boundary that can be validated once the API surfaces are stable.
- Verification favors in-process integration tests against Postgres-backed models (no UI toolchain) plus a simple HTML contract check to keep the console stable while avoiding a full browser harness.

## Must-Haves
- Reviewer queue endpoint returns REVIEW_PENDING cases with project summaries and review metadata.
- Evidence summary endpoint aggregates evidence IDs + artifact metadata across case-linked domain tables without N+1 behavior.
- Reviewer console entrypoint renders a usable queue → evidence → decision flow with API key gating handled in the client.
- Decision submission uses the real reviewer API contract (including independence/self-approval guard) and surfaces response state (including guard denials) in the UI.

## Proof Level
- This slice proves: integration
- Real runtime required: no
- Human/UAT required: yes

## Verification
- `pytest tests/m008_s01_reviewer_queue_evidence_test.py -v -s`
- `pytest tests/m008_s01_reviewer_console_page_test.py -v -s`

## Observability / Diagnostics
- Runtime signals: reviewer queue/evidence fetch logs with case counts and case_id context; reviewer console surfaces API error payloads.
- Inspection surfaces: `/api/v1/reviews/queue`, `/api/v1/reviews/cases/{case_id}/evidence-summary`, `/reviewer`, DB tables `permit_cases`, `projects`, `evidence_artifacts`.
- Failure visibility: HTTP 401/404/500 details for API calls; UI error banner with status + response body.
- Redaction constraints: never log evidence payload contents or reviewer-provided notes; only IDs and counts.

## Integration Closure
- Upstream surfaces consumed: `PermitCase`, `Project`, `EvidenceArtifact`, `JurisdictionResolution`, `RequirementSet`, `ComplianceEvaluation`, `IncentiveAssessment`, `ReviewDecision` models.
- New wiring introduced in this slice: reviewer queue/evidence endpoints under `/api/v1/reviews/*` and FastAPI `/reviewer` entrypoint with Jinja template.
- What remains before the milestone is truly usable end-to-end: rolling-quarter independence threshold computation + enforcement, live docker-compose runbook (S02).

## Tasks
- [x] **T01: Add reviewer queue + evidence summary endpoints with tests** `est:4h`
  - Why: Reviewer UI needs authoritative queue/evidence data and contract coverage before UI wiring.
  - Files: `src/sps/api/routes/reviews.py`, `src/sps/api/contracts/reviews.py`, `src/sps/db/models.py`, `tests/m008_s01_reviewer_queue_evidence_test.py`
  - Do: Define queue/evidence response models, add `/api/v1/reviews/queue` and `/api/v1/reviews/cases/{case_id}/evidence-summary` endpoints gated by reviewer API key, aggregate evidence IDs across case-linked tables and join to `evidence_artifacts` for metadata, add structured logs with counts, and add integration tests covering empty queue, populated queue, and evidence aggregation behavior.
  - Verify: `pytest tests/m008_s01_reviewer_queue_evidence_test.py -v -s`
  - Done when: Tests pass and endpoints return stable JSON with expected counts/metadata for seeded cases.
- [x] **T02: Serve reviewer console MVP and wire decision submission** `est:3h`
  - Why: Provides the actual reviewer-facing console entrypoint that exercises the new API and decision submission flow.
  - Files: `src/sps/api/main.py`, `src/sps/api/routes/reviewer_console.py`, `src/sps/api/templates/reviewer_console.html`, `tests/m008_s01_reviewer_console_page_test.py`
  - Do: Add a `/reviewer` route using Jinja2 templates, render queue + evidence + decision panels, include minimal JS to fetch queue/evidence and POST decisions with API key + required fields, and show API errors inline (including independence guard denials) without logging sensitive inputs.
  - Verify: `pytest tests/m008_s01_reviewer_console_page_test.py -v -s`
  - Done when: `/reviewer` returns HTML with the expected UI anchors and manual smoke verifies queue → evidence → decision path.

## Files Likely Touched
- `src/sps/api/routes/reviews.py`
- `src/sps/api/contracts/reviews.py`
- `src/sps/api/routes/reviewer_console.py`
- `src/sps/api/main.py`
- `src/sps/api/templates/reviewer_console.html`
- `tests/m008_s01_reviewer_queue_evidence_test.py`
- `tests/m008_s01_reviewer_console_page_test.py`
