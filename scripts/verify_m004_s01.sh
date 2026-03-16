#!/usr/bin/env bash
# shellcheck shell=bash
set -euo pipefail

# M004 / S01 runbook verification: Intake API → Postgres → Temporal → INTAKE_COMPLETE.
#
# What this does:
#   1) Ensures docker compose services are up (Postgres + Temporal + Temporal UI)
#   2) Applies Alembic migrations
#   3) Starts the real worker entrypoint (python -m sps.workflows.worker)
#   4) Starts the FastAPI server (uvicorn sps.api.main:app)
#   5) POSTs /api/v1/cases (the HTTP authority boundary)
#   6) Asserts: HTTP 201, PermitCase + Project rows in Postgres
#   7) Waits for CASE_STATE_CHANGED → INTAKE_COMPLETE in case_transition_ledger
#
# Expected env vars (optional; defaults match src/sps/config.py and .env.example):
#   SPS_DB_HOST (default: localhost)
#   SPS_DB_PORT (default: 5432)
#   SPS_DB_NAME (default: sps)
#   SPS_DB_USER (default: sps)
#   SPS_DB_PASSWORD (default: sps)          # never printed
#
#   SPS_TEMPORAL_ADDRESS (default: localhost:7233)
#   SPS_TEMPORAL_NAMESPACE (default: default)
#   SPS_TEMPORAL_TASK_QUEUE (default: sps-permit-case)
#
#   API_HOST (default: localhost)
#   API_PORT (default: 8000)
#
# Optional overrides:
#   PYTHON (default: ./.venv/bin/python)
#   ALEMBIC (default: ./.venv/bin/alembic)
#   CASE_PAYLOAD_TENANT (default: TEN-RUNBOOK)

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

API_HOST="${API_HOST:-localhost}"
API_PORT="${API_PORT:-8000}"
API_BASE="http://${API_HOST}:${API_PORT}"

RUNBOOK_TS="$(date +%Y%m%d_%H%M%S)"
: "${SPS_TEMPORAL_TASK_QUEUE:=sps-permit-case-runbook-${RUNBOOK_TS}-$$}"
export SPS_TEMPORAL_TASK_QUEUE

CASE_ID=""
PROJECT_ID=""
WORKER_PID=""
WORKER_LOG=""
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

  if [[ -n "$WORKER_PID" ]]; then
    if kill -0 "$WORKER_PID" >/dev/null 2>&1; then
      echo "runbook.cleanup: stopping_worker pid=$WORKER_PID" >&2
      kill "$WORKER_PID" >/dev/null 2>&1 || true
      wait "$WORKER_PID" >/dev/null 2>&1 || true
    fi
  fi

  if [[ $exit_code -ne 0 ]]; then
    if [[ -n "$WORKER_LOG" && -f "$WORKER_LOG" ]]; then
      echo "runbook.diagnostics: worker_log_tail path=$WORKER_LOG" >&2
      tail -n 50 "$WORKER_LOG" >&2 || true
    fi
    if [[ -n "$API_LOG" && -f "$API_LOG" ]]; then
      echo "runbook.diagnostics: api_log_tail path=$API_LOG" >&2
      tail -n 50 "$API_LOG" >&2 || true
    fi
    if [[ -n "$CASE_ID" ]]; then
      pg_assert_no_single_quotes "$CASE_ID"
      CASE_QUOTED="$(pg_sql_quote "$CASE_ID")"
      echo "runbook.diagnostics: ledger_snapshot case_id=$CASE_ID" >&2
      pg_print "select event_type, to_state from case_transition_ledger where case_id=${CASE_QUOTED} order by occurred_at" >&2 || true
    fi
  fi

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
import os, socket, time, sys

host = os.environ["WAIT_HOST"]
port = int(os.environ["WAIT_PORT"])
timeout_seconds = float(os.environ["WAIT_TIMEOUT_SECONDS"])

deadline = time.time() + timeout_seconds
last_err = None
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            sys.exit(0)
    except OSError as e:
        last_err = e
        time.sleep(0.2)

print(
    f"runbook.fail: tcp_not_ready host={host} port={port} last_err={type(last_err).__name__ if last_err else None}",
    file=sys.stderr,
)
sys.exit(1)
PY
}

_wait_for_worker_ready() {
  local timeout_seconds="$1"

  local deadline=$((SECONDS + timeout_seconds))
  while (( SECONDS < deadline )); do
    if [[ -n "$WORKER_PID" ]] && ! kill -0 "$WORKER_PID" >/dev/null 2>&1; then
      echo "runbook.fail: worker_exited_early pid=$WORKER_PID" >&2
      return 1
    fi

    if [[ -f "$WORKER_LOG" ]] && grep -q "temporal.worker.polling" "$WORKER_LOG"; then
      return 0
    fi

    sleep 0.2
  done

  echo "runbook.fail: worker_not_ready timeout_seconds=$timeout_seconds" >&2
  return 1
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
import os, socket
try:
    with socket.create_connection(("localhost", int(os.environ.get("API_PORT", "8000"))), timeout=0.5):
        pass
    exit(0)
except OSError:
    exit(1)
PY
    then
      return 0
    fi

    sleep 0.2
  done

  echo "runbook.fail: api_not_ready timeout_seconds=$timeout_seconds" >&2
  return 1
}

_http_post_json() {
  # POST a JSON body and return the HTTP status code on stdout.
  # The response body goes to the file referenced by HTTP_RESPONSE_FILE.
  local url="$1"
  local body="$2"
  local out_file="${HTTP_RESPONSE_FILE:-/tmp/m004_s01_response_$$.json}"

  curl -s -o "$out_file" -w "%{http_code}" \
    -X POST "$url" \
    -H "Content-Type: application/json" \
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

_poll_ledger_for_state() {
  # Poll case_transition_ledger until CASE_STATE_CHANGED/INTAKE_COMPLETE appears.
  local case_id_quoted="$1"
  local timeout_seconds="$2"

  local deadline=$((SECONDS + timeout_seconds))
  while (( SECONDS < deadline )); do
    local count
    count="$(pg_exec "select count(*) from case_transition_ledger where case_id=${case_id_quoted} and event_type='CASE_STATE_CHANGED' and to_state='INTAKE_COMPLETE'" 2>/dev/null || echo 0)"
    count="${count%$'\n'}"
    if [[ "$count" == "1" ]]; then
      return 0
    fi
    sleep 0.5
  done

  echo "runbook.fail: workflow_not_intake_complete case_id=${case_id_quoted} timeout=${timeout_seconds}s" >&2
  return 1
}

_parse_response_field() {
  local field="$1"
  FIELD_NAME="$field" "$PYTHON" - <<'PY'
import json
import os
import sys

path = os.environ.get("HTTP_RESPONSE_FILE")
if not path or not os.path.isfile(path):
    sys.exit(1)
with open(path, "r", encoding="utf-8") as fh:
    data = json.load(fh)
value = data.get(os.environ.get("FIELD_NAME"))
if value is None:
    sys.exit(1)
print(value)
PY
}

# ---------------------------------------------------------------------------
# Phase 1: Ensure infrastructure is up
# ---------------------------------------------------------------------------

echo "runbook: ensuring_docker_compose_stack" >&2
docker compose up -d postgres temporal temporal-ui >/dev/null

DB_HOST="${SPS_DB_HOST:-127.0.0.1}"
DB_PORT="${SPS_DB_PORT:-5432}"
TEMPORAL_ADDRESS="${SPS_TEMPORAL_ADDRESS:-${TEMPORAL_ADDRESS:-localhost:7233}}"
TEMPORAL_HOST="${TEMPORAL_ADDRESS%:*}"
TEMPORAL_PORT="${TEMPORAL_ADDRESS##*:}"
if [[ "$TEMPORAL_HOST" == "$TEMPORAL_PORT" ]]; then
  TEMPORAL_HOST="$TEMPORAL_ADDRESS"
  TEMPORAL_PORT="7233"
fi

_wait_for_tcp "$DB_HOST" "$DB_PORT" 30
_wait_for_tcp "$TEMPORAL_HOST" "$TEMPORAL_PORT" 30

# ---------------------------------------------------------------------------
# Phase 2: Migrations
# ---------------------------------------------------------------------------

echo "runbook: applying_migrations" >&2
"$ALEMBIC" upgrade head >/dev/null

# ---------------------------------------------------------------------------
# Phase 3: Start worker
# ---------------------------------------------------------------------------

mkdir -p "$ROOT_DIR/.gsd/runbook"
WORKER_LOG="$ROOT_DIR/.gsd/runbook/m004_s01_worker_${RUNBOOK_TS}_$$.log"

echo "runbook: starting_worker log=$WORKER_LOG" >&2
"$PYTHON" -m sps.workflows.worker >"$WORKER_LOG" 2>&1 &
WORKER_PID=$!

_wait_for_worker_ready 30
echo "runbook: worker_ready pid=$WORKER_PID" >&2

# ---------------------------------------------------------------------------
# Phase 4: Start FastAPI server
# ---------------------------------------------------------------------------

API_LOG="$ROOT_DIR/.gsd/runbook/m004_s01_api_${RUNBOOK_TS}_$$.log"

echo "runbook: starting_api log=$API_LOG port=$API_PORT" >&2
"$PYTHON" -m uvicorn sps.api.main:app --host 0.0.0.0 --port "$API_PORT" >"$API_LOG" 2>&1 &
API_PID=$!

_wait_for_api_ready 30
echo "runbook: api_ready pid=$API_PID" >&2

# ---------------------------------------------------------------------------
# Phase 5: POST to intake API (the HTTP authority boundary)
# ---------------------------------------------------------------------------

TENANT_ID="${CASE_PAYLOAD_TENANT:-TEN-RUNBOOK}"

PAYLOAD_JSON="$(cat <<JSON
{
  "tenant_id": "${TENANT_ID}",
  "intake_mode": "interactive",
  "project_description": "Install 45 kW rooftop solar.",
  "site_address": {
    "line1": "900 Runbook Blvd",
    "city": "Helena",
    "state": "MT",
    "postal_code": "59601"
  },
  "requester": {
    "name": "Runbook Applicant",
    "email": "runbook-applicant@example.com"
  },
  "project_type": "commercial_solar",
  "system_size_kw": 45.0,
  "battery_flag": false,
  "service_upgrade_flag": false,
  "trenching_flag": false,
  "structural_modification_flag": false,
  "utility_name": "Example Utility"
}
JSON
)"

echo "runbook: posting_intake_case" >&2

HTTP_RESPONSE_FILE="$(mktemp /tmp/m004_s01_resp_XXXXXX)"
export HTTP_RESPONSE_FILE

HTTP_STATUS="$(_http_post_json "${API_BASE}/api/v1/cases" "$PAYLOAD_JSON")"

_assert_http_status "$HTTP_STATUS" "201" "post_intake_case"

CASE_ID="$(_parse_response_field case_id)"
PROJECT_ID="$(_parse_response_field project_id)"

if [[ -z "$CASE_ID" || -z "$PROJECT_ID" ]]; then
  echo "runbook.fail: missing_ids_from_response" >&2
  exit 1
fi

echo "runbook: intake_api_201_ok case_id=$CASE_ID project_id=$PROJECT_ID" >&2

# Print the 201 response to stdout (operator surface).
if [[ -f "$HTTP_RESPONSE_FILE" ]]; then
  cat "$HTTP_RESPONSE_FILE"
  echo
fi

# ---------------------------------------------------------------------------
# Phase 6: Assert PermitCase + Project rows
# ---------------------------------------------------------------------------

pg_assert_no_single_quotes "$CASE_ID"
pg_assert_no_single_quotes "$PROJECT_ID"
CASE_QUOTED="$(pg_sql_quote "$CASE_ID")"
PROJECT_QUOTED="$(pg_sql_quote "$PROJECT_ID")"

pg_assert_int_eq \
  "select count(*) from permit_cases where case_id=${CASE_QUOTED}" \
  "1" \
  "permit_cases.count(case_id)"

pg_assert_int_eq \
  "select count(*) from projects where project_id=${PROJECT_QUOTED}" \
  "1" \
  "projects.count(project_id)"

pg_assert_scalar_eq \
  "select case_id from projects where project_id=${PROJECT_QUOTED}" \
  "$CASE_ID" \
  "projects.case_id"

pg_assert_scalar_eq \
  "select project_id from permit_cases where case_id=${CASE_QUOTED}" \
  "$PROJECT_ID" \
  "permit_cases.project_id"

echo "runbook: permit_case_project_rows_ok" >&2

# ---------------------------------------------------------------------------
# Phase 7: Wait for workflow to reach INTAKE_COMPLETE
# ---------------------------------------------------------------------------

echo "runbook: waiting_for_intake_complete" >&2
_poll_ledger_for_state "$CASE_QUOTED" 30

echo "runbook: workflow_intake_complete" >&2

pg_assert_int_eq \
  "select count(*) from case_transition_ledger where case_id=${CASE_QUOTED} and event_type='CASE_STATE_CHANGED' and to_state='INTAKE_COMPLETE'" \
  "1" \
  "case_transition_ledger.CASE_STATE_CHANGED.INTAKE_COMPLETE"

# ---------------------------------------------------------------------------
# Phase 8: Postgres summary
# ---------------------------------------------------------------------------

echo "runbook: postgres_summary" >&2
pg_print "select event_type, to_state, count(*) from case_transition_ledger where case_id=${CASE_QUOTED} group by event_type, to_state order by event_type" >&2
pg_print "select case_id, project_id, case_state from permit_cases where case_id=${CASE_QUOTED}" >&2
pg_print "select project_id, project_type from projects where project_id=${PROJECT_QUOTED}" >&2

# Signal inspection hint for operators.
echo "runbook: structured_log_hint hint='docker compose logs api | grep intake_api'" >&2

echo "runbook: ok" >&2
