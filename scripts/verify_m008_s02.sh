#!/usr/bin/env bash
# shellcheck shell=bash
set -euo pipefail

# M008 / S02 runbook verification: reviewer queue → evidence → decision flow
# plus rolling-quarter independence threshold enforcement.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# shellcheck source=scripts/lib/assert_postgres.sh
source "$ROOT_DIR/scripts/lib/assert_postgres.sh"

PYTHON="${PYTHON:-$ROOT_DIR/.venv/bin/python}"
ALEMBIC="${ALEMBIC:-$ROOT_DIR/.venv/bin/alembic}"

if [[ ! -x "$PYTHON" ]]; then
  echo "runbook.fail: python_not_found path=$PYTHON" >&2
  exit 2
fi

if [[ ! -x "$ALEMBIC" ]]; then
  echo "runbook.fail: alembic_not_found path=$ALEMBIC" >&2
  exit 2
fi

REVIEWER_API_KEY="${SPS_REVIEWER_API_KEY:-dev-reviewer-key}"
API_HOST="${API_HOST:-localhost}"
API_PORT="${API_PORT:-8000}"
API_BASE="http://${API_HOST}:${API_PORT}"

RUNBOOK_TS="$(date +%Y%m%d_%H%M%S)"
API_PID=""
API_LOG=""

_cleanup() {
  local exit_code=$?

  if [[ -n "$API_PID" ]]; then
    if kill -0 "$API_PID" >/dev/null 2>&1; then
      echo "runbook.cleanup: stopping_api pid=$API_PID" >&2
      kill "$API_PID" >/dev/null 2>&1 || true
      wait "$API_PID" >/dev/null 2>&1 || true
    fi
  fi

  if [[ $exit_code -ne 0 ]]; then
    if [[ -n "$API_LOG" && -f "$API_LOG" ]]; then
      echo "runbook.diagnostics: api_log_tail path=$API_LOG" >&2
      tail -n 80 "$API_LOG" >&2 || true
    fi
  fi

  docker compose down >/dev/null 2>&1 || true

  return $exit_code
}

trap _cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

_wait_for_tcp() {
  local host="$1"
  local port="$2"
  local timeout_seconds="$3"

  WAIT_HOST="$host" WAIT_PORT="$port" WAIT_TIMEOUT_SECONDS="$timeout_seconds" \
    "$PYTHON" - <<'PY'
import os
import socket
import time
import sys

host = os.environ["WAIT_HOST"]
port = int(os.environ["WAIT_PORT"])
timeout_seconds = float(os.environ["WAIT_TIMEOUT_SECONDS"])

last_err = None
deadline = time.time() + timeout_seconds
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            sys.exit(0)
    except OSError as exc:
        last_err = exc
        time.sleep(0.2)

print(
    f"runbook.fail: tcp_not_ready host={host} port={port} last_err={type(last_err).__name__ if last_err else None}",
    file=sys.stderr,
)
sys.exit(1)
PY
}

_wait_for_api_ready() {
  local timeout_seconds="$1"

  local deadline=$((SECONDS + timeout_seconds))
  while (( SECONDS < deadline )); do
    if [[ -n "$API_PID" ]] && ! kill -0 "$API_PID" >/dev/null 2>&1; then
      echo "runbook.fail: api_exited_early pid=$API_PID" >&2
      return 1
    fi

    if "$PYTHON" - <<'PY' 2>/dev/null
import os
import socket

try:
    with socket.create_connection(("localhost", int(os.environ.get("API_PORT", "8000"))), timeout=0.5):
        pass
    raise SystemExit(0)
except OSError:
    raise SystemExit(1)
PY
    then
      return 0
    fi

    sleep 0.2
  done

  echo "runbook.fail: api_not_ready timeout_seconds=$timeout_seconds" >&2
  return 1
}

_http_get_json_with_key() {
  local url="$1"
  local api_key="$2"
  local out_file="${HTTP_RESPONSE_FILE:-/tmp/m008_s02_response_$$.json}"

  curl -s -o "$out_file" -w "%{http_code}" \
    -X GET "$url" \
    -H "Content-Type: application/json" \
    -H "X-Reviewer-Api-Key: ${api_key}"
}

_http_post_json_with_key() {
  local url="$1"
  local body="$2"
  local api_key="$3"
  local out_file="${HTTP_RESPONSE_FILE:-/tmp/m008_s02_response_$$.json}"

  curl -s -o "$out_file" -w "%{http_code}" \
    -X POST "$url" \
    -H "Content-Type: application/json" \
    -H "X-Reviewer-Api-Key: ${api_key}" \
    -d "$body"
}

_assert_http_status() {
  local actual="$1"
  local expected="$2"
  local label="$3"

  if [[ "$actual" != "$expected" ]]; then
    echo "runbook.fail: http_status_mismatch label=$label expected=$expected actual=$actual" >&2
    if [[ -f "${HTTP_RESPONSE_FILE:-}" ]]; then
      echo "runbook.diagnostics: response_body" >&2
      cat "${HTTP_RESPONSE_FILE}" >&2 || true
    fi
    exit 1
  fi
}

_parse_first_queue_case_id() {
  "$PYTHON" - <<'PY'
import json
import os
import sys

path = os.environ.get("HTTP_RESPONSE_FILE")
if not path:
    raise SystemExit(1)

with open(path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)

cases = payload.get("cases") or []
if not cases:
    raise SystemExit(1)

case_id = cases[0].get("case_id")
if not case_id:
    raise SystemExit(1)

print(case_id)
PY
}

_assert_blocked_payload() {
  "$PYTHON" - <<'PY'
import json
import os
import sys

path = os.environ.get("HTTP_RESPONSE_FILE")
if not path:
    raise SystemExit(1)

with open(path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)

if isinstance(payload, dict) and "detail" in payload:
    detail = payload["detail"]
else:
    detail = payload

if detail.get("guard_assertion_id") != "INV-SPS-REV-001":
    raise SystemExit("guard_assertion_id mismatch")
if detail.get("blocked_reason") != "INDEPENDENCE_THRESHOLD_BLOCKED":
    raise SystemExit("blocked_reason mismatch")
PY
}

_seed_permit_case() {
  local case_id="$1"
  local project_id="$2"
  local case_state="${3:-REVIEW_PENDING}"
  local review_state="${4:-PENDING}"

  pg_assert_no_single_quotes "$case_id"
  pg_assert_no_single_quotes "$project_id"
  pg_assert_no_single_quotes "$case_state"
  pg_assert_no_single_quotes "$review_state"

  local case_quoted
  local project_quoted
  case_quoted="$(pg_sql_quote "$case_id")"
  project_quoted="$(pg_sql_quote "$project_id")"

  pg_exec "insert into permit_cases (case_id, tenant_id, project_id, case_state, review_state, submission_mode, portal_support_level, current_release_profile, legal_hold) values (${case_quoted}, 'tenant-runbook', ${project_quoted}, $(pg_sql_quote "$case_state"), $(pg_sql_quote "$review_state"), 'DIGITAL', 'FULL', 'default', false) on conflict (case_id) do nothing" >/dev/null
}

_seed_project() {
  local project_id="$1"
  local case_id="$2"

  pg_assert_no_single_quotes "$project_id"
  pg_assert_no_single_quotes "$case_id"

  local project_quoted
  local case_quoted
  project_quoted="$(pg_sql_quote "$project_id")"
  case_quoted="$(pg_sql_quote "$case_id")"

  pg_exec "insert into projects (project_id, case_id, address, project_type, system_size_kw, battery_flag, service_upgrade_flag, trenching_flag, structural_modification_flag, utility_name) values (${project_quoted}, ${case_quoted}, '100 Runbook Ave', 'residential_solar', 12.5, false, false, false, false, 'Runbook Utility') on conflict (project_id) do nothing" >/dev/null
}

_seed_review_decision() {
  local case_id="$1"
  local decision_id="$2"
  local reviewer_id="$3"
  local subject_author_id="$4"

  pg_assert_no_single_quotes "$case_id"
  pg_assert_no_single_quotes "$decision_id"
  pg_assert_no_single_quotes "$reviewer_id"
  pg_assert_no_single_quotes "$subject_author_id"

  local case_quoted
  local decision_quoted
  local reviewer_quoted
  local subject_quoted
  case_quoted="$(pg_sql_quote "$case_id")"
  decision_quoted="$(pg_sql_quote "$decision_id")"
  reviewer_quoted="$(pg_sql_quote "$reviewer_id")"
  subject_quoted="$(pg_sql_quote "$subject_author_id")"

  pg_exec "insert into review_decisions (decision_id, schema_version, case_id, object_type, object_id, decision_outcome, reviewer_id, subject_author_id, reviewer_independence_status, evidence_ids, contradiction_resolution, dissent_flag, notes, decision_at, idempotency_key) values (${decision_quoted}, '1.0', ${case_quoted}, 'permit_case', ${case_quoted}, 'ACCEPT', ${reviewer_quoted}, ${subject_quoted}, 'PASS', '{}', null, false, null, (now() - interval '1 day'), 'seed/${decision_id}') on conflict (decision_id) do nothing" >/dev/null
}

# ---------------------------------------------------------------------------
# Phase 1: Ensure infrastructure is up
# ---------------------------------------------------------------------------

echo "runbook: ensuring_docker_compose_stack" >&2
docker compose up -d postgres >/dev/null

DB_HOST="${SPS_DB_HOST:-127.0.0.1}"
DB_PORT="${SPS_DB_PORT:-5432}"
_wait_for_tcp "$DB_HOST" "$DB_PORT" 30

# ---------------------------------------------------------------------------
# Phase 2: Migrations
# ---------------------------------------------------------------------------

echo "runbook: applying_migrations" >&2
"$ALEMBIC" upgrade head >/dev/null

# ---------------------------------------------------------------------------
# Phase 3: Seed reviewer data
# ---------------------------------------------------------------------------

echo "runbook: seeding_reviewer_cases" >&2

pg_exec "delete from review_decisions where decision_id like 'RUNBOOK-%' or idempotency_key like 'runbook/%'" >/dev/null
pg_exec "delete from projects where project_id like 'RUNBOOK-%' or case_id like 'RUNBOOK-%'" >/dev/null
pg_exec "delete from permit_cases where case_id like 'RUNBOOK-%'" >/dev/null
pg_exec "truncate table review_decisions cascade" >/dev/null

QUEUE_CASE_ID="RUNBOOK-QUEUE-001"
QUEUE_PROJECT_ID="RUNBOOK-PROJ-QUEUE-001"

_seed_permit_case "$QUEUE_CASE_ID" "$QUEUE_PROJECT_ID"
_seed_project "$QUEUE_PROJECT_ID" "$QUEUE_CASE_ID"

PASS_CASE_ID="$QUEUE_CASE_ID"
PASS_DECISION_ID="RUNBOOK-PASS-001"
PASS_REVIEWER_ID="reviewer-pass"
PASS_AUTHOR_ID="author-pass"

WARN_CASE_ID="RUNBOOK-WARN-001"
WARN_PROJECT_ID="RUNBOOK-PROJ-WARN-001"
WARN_DECISION_ID="RUNBOOK-WARN-DEC-001"
WARN_REVIEWER_ID="reviewer-warning"
WARN_AUTHOR_ID="author-warning"

ESC_CASE_ID="RUNBOOK-ESC-001"
ESC_PROJECT_ID="RUNBOOK-PROJ-ESC-001"
ESC_DECISION_ID="RUNBOOK-ESC-DEC-001"
ESC_REVIEWER_ID="reviewer-escalation"
ESC_AUTHOR_ID="author-escalation"

BLOCK_CASE_ID="RUNBOOK-BLOCK-001"
BLOCK_PROJECT_ID="RUNBOOK-PROJ-BLOCK-001"
BLOCK_DECISION_ID="RUNBOOK-BLOCK-DEC-001"
BLOCK_REVIEWER_ID="reviewer-blocked"
BLOCK_AUTHOR_ID="author-blocked"

_seed_permit_case "$WARN_CASE_ID" "$WARN_PROJECT_ID" "INTAKE_COMPLETE"
_seed_permit_case "$ESC_CASE_ID" "$ESC_PROJECT_ID" "INTAKE_COMPLETE"
_seed_permit_case "$BLOCK_CASE_ID" "$BLOCK_PROJECT_ID" "INTAKE_COMPLETE"

_seed_project "$WARN_PROJECT_ID" "$WARN_CASE_ID"
_seed_project "$ESC_PROJECT_ID" "$ESC_CASE_ID"
_seed_project "$BLOCK_PROJECT_ID" "$BLOCK_CASE_ID"

echo "runbook: seeded_queue_case case_id=$QUEUE_CASE_ID" >&2

# ---------------------------------------------------------------------------
# Phase 4: Start FastAPI server
# ---------------------------------------------------------------------------

mkdir -p "$ROOT_DIR/artifacts/runbook"
API_LOG="$ROOT_DIR/artifacts/runbook/m008_s02_api_${RUNBOOK_TS}_$$.log"

echo "runbook: starting_api log=$API_LOG port=$API_PORT" >&2
"$PYTHON" -m uvicorn sps.api.main:app --host 0.0.0.0 --port "$API_PORT" >"$API_LOG" 2>&1 &
API_PID=$!

_wait_for_api_ready 30
echo "runbook: api_ready pid=$API_PID" >&2

# ---------------------------------------------------------------------------
# Phase 5: Reviewer queue + evidence summary
# ---------------------------------------------------------------------------

echo "runbook: fetching_reviewer_queue" >&2
HTTP_RESPONSE_FILE="$(mktemp /tmp/m008_s02_queue_XXXXXX)"
export HTTP_RESPONSE_FILE

HTTP_STATUS="$(_http_get_json_with_key "${API_BASE}/api/v1/reviews/queue" "$REVIEWER_API_KEY")"
_assert_http_status "$HTTP_STATUS" "200" "get_review_queue"

QUEUE_CASE_FROM_API="$(_parse_first_queue_case_id)"
if [[ "$QUEUE_CASE_FROM_API" != "$QUEUE_CASE_ID" ]]; then
  echo "runbook.fail: unexpected_queue_case expected=$QUEUE_CASE_ID actual=$QUEUE_CASE_FROM_API" >&2
  exit 1
fi

cat "$HTTP_RESPONSE_FILE"
echo

EVIDENCE_CASE_ID="$QUEUE_CASE_ID"

echo "runbook: fetching_evidence_summary case_id=$EVIDENCE_CASE_ID" >&2
HTTP_RESPONSE_FILE="$(mktemp /tmp/m008_s02_evidence_XXXXXX)"
export HTTP_RESPONSE_FILE

HTTP_STATUS="$(_http_get_json_with_key "${API_BASE}/api/v1/reviews/cases/${EVIDENCE_CASE_ID}/evidence-summary" "$REVIEWER_API_KEY")"
_assert_http_status "$HTTP_STATUS" "200" "get_evidence_summary"

cat "$HTTP_RESPONSE_FILE"
echo

# ---------------------------------------------------------------------------
# Phase 6: Review decisions (PASS / WARNING / ESCALATION / BLOCKED)
# ---------------------------------------------------------------------------

PASS_BODY="$(cat <<JSON
{
  "decision_id": "${PASS_DECISION_ID}",
  "idempotency_key": "runbook/${PASS_DECISION_ID}",
  "case_id": "${PASS_CASE_ID}",
  "reviewer_id": "${PASS_REVIEWER_ID}",
  "subject_author_id": "${PASS_AUTHOR_ID}",
  "outcome": "ACCEPT"
}
JSON
)"

echo "runbook: posting_pass_decision decision_id=$PASS_DECISION_ID" >&2
HTTP_RESPONSE_FILE="$(mktemp /tmp/m008_s02_pass_XXXXXX)"
export HTTP_RESPONSE_FILE

HTTP_STATUS="$(_http_post_json_with_key "${API_BASE}/api/v1/reviews/decisions" "$PASS_BODY" "$REVIEWER_API_KEY")"
_assert_http_status "$HTTP_STATUS" "201" "post_pass_decision"
cat "$HTTP_RESPONSE_FILE"
echo

pg_assert_scalar_eq \
  "select reviewer_independence_status from review_decisions where decision_id=$(pg_sql_quote "$PASS_DECISION_ID")" \
  "PASS" \
  "review_decisions.status.pass"

pg_assert_scalar_eq \
  "select subject_author_id from review_decisions where decision_id=$(pg_sql_quote "$PASS_DECISION_ID")" \
  "${PASS_AUTHOR_ID}" \
  "review_decisions.subject_author_id.pass"

echo "runbook: resetting_for_warning_threshold" >&2
pg_exec "truncate table review_decisions cascade" >/dev/null

for idx in 1 2; do
  case_id="RUNBOOK-WARN-PAIR-${idx}"
  _seed_permit_case "$case_id" "RUNBOOK-PROJ-${case_id}" "INTAKE_COMPLETE"
  _seed_review_decision "$case_id" "RUNBOOK-WARN-PAIR-DEC-${idx}" "$WARN_REVIEWER_ID" "$WARN_AUTHOR_ID"
done
for idx in 1 2 3; do
  case_id="RUNBOOK-WARN-OTHER-${idx}"
  _seed_permit_case "$case_id" "RUNBOOK-PROJ-${case_id}" "INTAKE_COMPLETE"
  _seed_review_decision "$case_id" "RUNBOOK-WARN-OTHER-DEC-${idx}" "reviewer-other-${idx}" "author-other-${idx}"
done

WARN_BODY="$(cat <<JSON
{
  "decision_id": "${WARN_DECISION_ID}",
  "idempotency_key": "runbook/${WARN_DECISION_ID}",
  "case_id": "${WARN_CASE_ID}",
  "reviewer_id": "${WARN_REVIEWER_ID}",
  "subject_author_id": "${WARN_AUTHOR_ID}",
  "outcome": "ACCEPT"
}
JSON
)"

echo "runbook: posting_warning_decision decision_id=$WARN_DECISION_ID" >&2
HTTP_RESPONSE_FILE="$(mktemp /tmp/m008_s02_warn_XXXXXX)"
export HTTP_RESPONSE_FILE

HTTP_STATUS="$(_http_post_json_with_key "${API_BASE}/api/v1/reviews/decisions" "$WARN_BODY" "$REVIEWER_API_KEY")"
_assert_http_status "$HTTP_STATUS" "201" "post_warning_decision"
cat "$HTTP_RESPONSE_FILE"
echo

pg_assert_scalar_eq \
  "select reviewer_independence_status from review_decisions where decision_id=$(pg_sql_quote "$WARN_DECISION_ID")" \
  "WARNING" \
  "review_decisions.status.warning"

pg_assert_scalar_eq \
  "select subject_author_id from review_decisions where decision_id=$(pg_sql_quote "$WARN_DECISION_ID")" \
  "${WARN_AUTHOR_ID}" \
  "review_decisions.subject_author_id.warning"

echo "runbook: resetting_for_escalation_threshold" >&2
pg_exec "truncate table review_decisions cascade" >/dev/null

for idx in 1 2 3; do
  case_id="RUNBOOK-ESC-PAIR-${idx}"
  _seed_permit_case "$case_id" "RUNBOOK-PROJ-${case_id}" "INTAKE_COMPLETE"
  _seed_review_decision "$case_id" "RUNBOOK-ESC-PAIR-DEC-${idx}" "$ESC_REVIEWER_ID" "$ESC_AUTHOR_ID"
done
for idx in 1 2; do
  case_id="RUNBOOK-ESC-OTHER-${idx}"
  _seed_permit_case "$case_id" "RUNBOOK-PROJ-${case_id}" "INTAKE_COMPLETE"
  _seed_review_decision "$case_id" "RUNBOOK-ESC-OTHER-DEC-${idx}" "reviewer-other-esc-${idx}" "author-other-esc-${idx}"
done

ESC_BODY="$(cat <<JSON
{
  "decision_id": "${ESC_DECISION_ID}",
  "idempotency_key": "runbook/${ESC_DECISION_ID}",
  "case_id": "${ESC_CASE_ID}",
  "reviewer_id": "${ESC_REVIEWER_ID}",
  "subject_author_id": "${ESC_AUTHOR_ID}",
  "outcome": "ACCEPT"
}
JSON
)"

echo "runbook: posting_escalation_decision decision_id=$ESC_DECISION_ID" >&2
HTTP_RESPONSE_FILE="$(mktemp /tmp/m008_s02_esc_XXXXXX)"
export HTTP_RESPONSE_FILE

HTTP_STATUS="$(_http_post_json_with_key "${API_BASE}/api/v1/reviews/decisions" "$ESC_BODY" "$REVIEWER_API_KEY")"
_assert_http_status "$HTTP_STATUS" "201" "post_escalation_decision"
cat "$HTTP_RESPONSE_FILE"
echo

pg_assert_scalar_eq \
  "select reviewer_independence_status from review_decisions where decision_id=$(pg_sql_quote "$ESC_DECISION_ID")" \
  "ESCALATION_REQUIRED" \
  "review_decisions.status.escalation"

pg_assert_scalar_eq \
  "select subject_author_id from review_decisions where decision_id=$(pg_sql_quote "$ESC_DECISION_ID")" \
  "${ESC_AUTHOR_ID}" \
  "review_decisions.subject_author_id.escalation"

echo "runbook: resetting_for_block_threshold" >&2
pg_exec "truncate table review_decisions cascade" >/dev/null

for idx in 1 2 3 4; do
  case_id="RUNBOOK-BLOCK-PAIR-${idx}"
  _seed_permit_case "$case_id" "RUNBOOK-PROJ-${case_id}" "INTAKE_COMPLETE"
  _seed_review_decision "$case_id" "RUNBOOK-BLOCK-PAIR-DEC-${idx}" "$BLOCK_REVIEWER_ID" "$BLOCK_AUTHOR_ID"
done
for idx in 1; do
  case_id="RUNBOOK-BLOCK-OTHER-${idx}"
  _seed_permit_case "$case_id" "RUNBOOK-PROJ-${case_id}" "INTAKE_COMPLETE"
  _seed_review_decision "$case_id" "RUNBOOK-BLOCK-OTHER-DEC-${idx}" "reviewer-other-block-${idx}" "author-other-block-${idx}"
done

BLOCK_BODY="$(cat <<JSON
{
  "decision_id": "${BLOCK_DECISION_ID}",
  "idempotency_key": "runbook/${BLOCK_DECISION_ID}",
  "case_id": "${BLOCK_CASE_ID}",
  "reviewer_id": "${BLOCK_REVIEWER_ID}",
  "subject_author_id": "${BLOCK_AUTHOR_ID}",
  "outcome": "ACCEPT"
}
JSON
)"

echo "runbook: posting_blocked_decision decision_id=$BLOCK_DECISION_ID" >&2
HTTP_RESPONSE_FILE="$(mktemp /tmp/m008_s02_block_XXXXXX)"
export HTTP_RESPONSE_FILE

HTTP_STATUS="$(_http_post_json_with_key "${API_BASE}/api/v1/reviews/decisions" "$BLOCK_BODY" "$REVIEWER_API_KEY")"
_assert_http_status "$HTTP_STATUS" "403" "post_blocked_decision"
_assert_blocked_payload
cat "$HTTP_RESPONSE_FILE"
echo

pg_assert_int_eq \
  "select count(*) from review_decisions where decision_id=$(pg_sql_quote "$BLOCK_DECISION_ID")" \
  "0" \
  "review_decisions.status.blocked"

# ---------------------------------------------------------------------------
# Phase 7: Summary
# ---------------------------------------------------------------------------

echo "runbook: postgres_summary" >&2
pg_print "select decision_id, reviewer_id, subject_author_id, reviewer_independence_status from review_decisions where decision_id like 'RUNBOOK-%' order by decision_id" >&2


echo "runbook: ok" >&2
