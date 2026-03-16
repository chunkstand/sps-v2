# S01: Reviewer console MVP (queue + evidence + decision capture) — UAT

**Milestone:** M008-z1k9mp
**Written:** 2026-03-16

## UAT Type
- UAT mode: mixed
- Why this mode is sufficient: This slice combines API contract proof (queue/evidence endpoints) with a human-facing reviewer console; both API calls and UI interactions must be exercised.

## Preconditions
- API running locally (e.g., `uvicorn sps.api.main:app --reload`).
- Postgres seeded with at least one `PermitCase` in `REVIEW_PENDING` state, a related `Project`, and evidence artifacts tied to the case-linked domain tables.
- `SPS_REVIEWER_API_KEY` configured in the API process.
- Reviewer API key available to the tester for UI input.

## Smoke Test
- Open `http://127.0.0.1:8000/reviewer`, enter the reviewer API key, click **Load Queue**, and confirm at least one queue row renders.

## Test Cases
### 1. Queue fetch renders reviewer cases
1. Open `http://127.0.0.1:8000/reviewer`.
2. Enter the reviewer API key and click **Load Queue**.
3. Click the first queue row.
4. **Expected:** Queue list shows REVIEW_PENDING cases with project summary fields and a selected case is highlighted.

### 2. Evidence summary renders aggregated artifacts
1. With a case selected, click **Load Evidence Summary**.
2. **Expected:** Evidence table populates with artifact IDs, types, and metadata for the selected case; decision summaries (if any) are visible.

### 3. Decision submission posts to reviewer API
1. Select a case, choose outcome `ACCEPT` (or `BLOCK`), and enter reviewer/subject IDs plus a decision note.
2. Click **Submit Decision**.
3. **Expected:** Success banner appears with HTTP 201 and response payload; a ReviewDecision row is persisted (verify via API or DB).

## Edge Cases
### Missing API key
1. Leave the reviewer API key blank and click **Load Queue**.
2. **Expected:** Error banner shows HTTP 401 with `missing_api_key` detail.

### Independence guard denial
1. Enter the same value for reviewer ID and subject author ID.
2. Submit a decision.
3. **Expected:** Error banner shows HTTP 403 with guard assertion `INV-SPS-REV-001` and no ReviewDecision persisted.

## Failure Signals
- `/reviewer` does not render queue/evidence/decision panels.
- Queue or evidence requests return 500s or empty data when seeded cases exist.
- Decision submission returns 200/201 without a corresponding ReviewDecision row.
- Error banner fails to show HTTP status + payload on API failures.

## Requirements Proved By This UAT
- R020 — Reviewer UI queue/evidence view/decision capture via the reviewer API.

## Not Proven By This UAT
- R021 — Rolling-quarter independence thresholds and enforcement signals.
- Live docker-compose runbook proof of reviewer UI + API + Postgres flow (S02).

## Notes for Tester
- The console is intentionally minimal; no pagination or bulk actions are implemented.
- Evidence payloads are summarized only; raw evidence contents are not displayed in this UI.
