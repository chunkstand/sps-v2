#!/usr/bin/env bash
# shellcheck shell=bash
set -euo pipefail

# M004 / S03 runbook verification: real intake API → fixture override worker
# → JURISDICTION_COMPLETE → RESEARCH_COMPLETE, with API read surfaces.
#
# What this does:
#   1) Ensures docker compose services are up (Postgres + Temporal + Temporal UI)
#   2) Applies Alembic migrations
#   3) Starts the FastAPI server (uvicorn sps.api.main:app)
#   4) POSTs /api/v1/cases and captures runtime case_id + project_id
#   5) Starts the worker with fixture override mapping
#   6) Asserts: INTAKE_COMPLETE → JURISDICTION_COMPLETE → RESEARCH_COMPLETE
#   7) Asserts: jurisdiction_resolutions + requirement_sets rows
#   8) GETs /api/v1/cases/{case_id}/jurisdiction + /requirements
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
FIXTURE_CASE_ID=""
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
  local out_file="${HTTP_RESPONSE_FILE:-/tmp/m004_s03_response_$$.json}"

  curl -s -o "$out_file" -w "%{http_code}" \
    -X POST "$url" \
    -H "Content-Type: application/json" \
    -d "$body"
}

_http_get_json() {
  local url="$1"
  local out_file="${HTTP_RESPONSE_FILE:-/tmp/m004_s03_response_$$.json}"

  curl -s -o "$out_file" -w "%{http_code}" \
    -X GET "$url" \
    -H "Content-Type: application/json"
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
  local case_id_quoted="$1"
  local to_state="$2"
  local timeout_seconds="$3"

  local deadline=$((SECONDS + timeout_seconds))
  while (( SECONDS < deadline )); do
    local count
    count="$(pg_exec "select count(*) from case_transition_ledger where case_id=${case_id_quoted} and event_type='CASE_STATE_CHANGED' and to_state='${to_state}'" 2>/dev/null || echo 0)"
    count="${count%$'\n'}"
    if [[ "$count" == "1" ]]; then
      return 0
    fi
    sleep 0.5
  done

  echo "runbook.fail: workflow_not_${to_state} case_id=${case_id_quoted} timeout=${timeout_seconds}s" >&2
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
# Phase 3: Start FastAPI server
# ---------------------------------------------------------------------------

mkdir -p "$ROOT_DIR/artifacts/runbook"
API_LOG="$ROOT_DIR/artifacts/runbook/m004_s03_api_${RUNBOOK_TS}_$$.log"

echo "runbook: starting_api log=$API_LOG port=$API_PORT" >&2
"$PYTHON" -m uvicorn sps.api.main:app --host 0.0.0.0 --port "$API_PORT" >"$API_LOG" 2>&1 &
API_PID=$!

_wait_for_api_ready 30
echo "runbook: api_ready pid=$API_PID" >&2

# ---------------------------------------------------------------------------
# Phase 4: Read fixture case_id + POST intake API
# ---------------------------------------------------------------------------

FIXTURE_CASE_ID="$($PYTHON - <<'PY'
import json
from pathlib import Path

path = Path("specs/sps/build-approved/fixtures/phase4/jurisdiction.json")
with path.open("r", encoding="utf-8") as handle:
    payload = json.load(handle)
print(payload["jurisdictions"][0]["case_id"])
PY
)"

if [[ -z "$FIXTURE_CASE_ID" ]]; then
  echo "runbook.fail: missing_fixture_case_id" >&2
  exit 1
fi

echo "runbook: fixture_case_id case_id=$FIXTURE_CASE_ID" >&2

pg_assert_no_single_quotes "$FIXTURE_CASE_ID"
FIXTURE_QUOTED="$(pg_sql_quote "$FIXTURE_CASE_ID")"

FIXTURE_JUR_IDS=()
while IFS= read -r line; do
  [[ -n "$line" ]] && FIXTURE_JUR_IDS+=("$line")
done < <("$PYTHON" - <<'PY'
import json
from pathlib import Path

path = Path("specs/sps/build-approved/fixtures/phase4/jurisdiction.json")
with path.open("r", encoding="utf-8") as handle:
    payload = json.load(handle)
case_id = payload["jurisdictions"][0]["case_id"]
ids = [item["jurisdiction_resolution_id"] for item in payload["jurisdictions"] if item.get("case_id") == case_id]
for item in ids:
    print(item)
PY
)

FIXTURE_REQ_IDS=()
while IFS= read -r line; do
  [[ -n "$line" ]] && FIXTURE_REQ_IDS+=("$line")
done < <("$PYTHON" - <<'PY'
import json
from pathlib import Path

path = Path("specs/sps/build-approved/fixtures/phase4/requirements.json")
with path.open("r", encoding="utf-8") as handle:
    payload = json.load(handle)
case_id = payload["requirement_sets"][0]["case_id"]
ids = [item["requirement_set_id"] for item in payload["requirement_sets"] if item.get("case_id") == case_id]
for item in ids:
    print(item)
PY
)

if [[ ${#FIXTURE_JUR_IDS[@]} -eq 0 || ${#FIXTURE_REQ_IDS[@]} -eq 0 ]]; then
  echo "runbook.fail: missing_fixture_ids" >&2
  exit 1
fi

echo "runbook: clearing_fixture_artifacts case_id=$FIXTURE_CASE_ID" >&2
pg_exec "delete from jurisdiction_resolutions where case_id=${FIXTURE_QUOTED}" >/dev/null
pg_exec "delete from requirement_sets where case_id=${FIXTURE_QUOTED}" >/dev/null

for jur_id in "${FIXTURE_JUR_IDS[@]}"; do
  pg_assert_no_single_quotes "$jur_id"
  JUR_QUOTED="$(pg_sql_quote "$jur_id")"
  pg_exec "delete from jurisdiction_resolutions where jurisdiction_resolution_id=${JUR_QUOTED}" >/dev/null
done

for req_id in "${FIXTURE_REQ_IDS[@]}"; do
  pg_assert_no_single_quotes "$req_id"
  REQ_QUOTED="$(pg_sql_quote "$req_id")"
  pg_exec "delete from requirement_sets where requirement_set_id=${REQ_QUOTED}" >/dev/null
done

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

HTTP_RESPONSE_FILE="$(mktemp /tmp/m004_s03_resp_XXXXXX)"
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

if [[ -f "$HTTP_RESPONSE_FILE" ]]; then
  cat "$HTTP_RESPONSE_FILE"
  echo
fi

export SPS_PHASE4_FIXTURE_CASE_ID_OVERRIDE="$FIXTURE_CASE_ID"
echo "runbook: fixture_override_enabled fixture_case_id=$SPS_PHASE4_FIXTURE_CASE_ID_OVERRIDE" >&2

# ---------------------------------------------------------------------------
# Phase 5: Start worker with fixture override
# ---------------------------------------------------------------------------

WORKER_LOG="$ROOT_DIR/artifacts/runbook/m004_s03_worker_${RUNBOOK_TS}_$$.log"

echo "runbook: starting_worker log=$WORKER_LOG" >&2
"$PYTHON" -m sps.workflows.worker >"$WORKER_LOG" 2>&1 &
WORKER_PID=$!

_wait_for_worker_ready 30
echo "runbook: worker_ready pid=$WORKER_PID" >&2

# ---------------------------------------------------------------------------
# Phase 6: Wait for workflow progression + persistence
# ---------------------------------------------------------------------------

pg_assert_no_single_quotes "$CASE_ID"
pg_assert_no_single_quotes "$PROJECT_ID"
CASE_QUOTED="$(pg_sql_quote "$CASE_ID")"
PROJECT_QUOTED="$(pg_sql_quote "$PROJECT_ID")"

echo "runbook: waiting_for_intake_complete" >&2
_poll_ledger_for_state "$CASE_QUOTED" "INTAKE_COMPLETE" 30

echo "runbook: starting_workflow_for_research case_id=$CASE_ID" >&2
RUNBOOK_CASE_ID="$CASE_ID" "$PYTHON" - <<'PY'
import asyncio
import os

from temporalio.common import WorkflowIDReusePolicy

from sps.workflows.permit_case.contracts import PermitCaseWorkflowInput
from sps.workflows.permit_case.ids import permit_case_workflow_id
from sps.workflows.permit_case.workflow import PermitCaseWorkflow
from sps.workflows.temporal import connect_client


async def main() -> None:
    client = await connect_client()
    case_id = os.environ["RUNBOOK_CASE_ID"]
    workflow_id = permit_case_workflow_id(case_id)
    handle = await client.start_workflow(
        PermitCaseWorkflow.run,
        PermitCaseWorkflowInput(case_id=case_id),
        id=workflow_id,
        task_queue=os.environ["SPS_TEMPORAL_TASK_QUEUE"],
        id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
    )
    await asyncio.wait_for(handle.result(), timeout=60.0)


asyncio.run(main())
PY

echo "runbook: waiting_for_jurisdiction_complete" >&2
_poll_ledger_for_state "$CASE_QUOTED" "JURISDICTION_COMPLETE" 60

echo "runbook: waiting_for_research_complete" >&2
_poll_ledger_for_state "$CASE_QUOTED" "RESEARCH_COMPLETE" 60

pg_assert_int_eq \
  "select count(*) from case_transition_ledger where case_id=${CASE_QUOTED} and event_type='CASE_STATE_CHANGED' and to_state='INTAKE_COMPLETE'" \
  "1" \
  "case_transition_ledger.CASE_STATE_CHANGED.INTAKE_COMPLETE"

pg_assert_int_eq \
  "select count(*) from case_transition_ledger where case_id=${CASE_QUOTED} and event_type='CASE_STATE_CHANGED' and to_state='JURISDICTION_COMPLETE'" \
  "1" \
  "case_transition_ledger.CASE_STATE_CHANGED.JURISDICTION_COMPLETE"

pg_assert_int_eq \
  "select count(*) from case_transition_ledger where case_id=${CASE_QUOTED} and event_type='CASE_STATE_CHANGED' and to_state='RESEARCH_COMPLETE'" \
  "1" \
  "case_transition_ledger.CASE_STATE_CHANGED.RESEARCH_COMPLETE"

pg_assert_int_eq \
  "select count(*) from jurisdiction_resolutions where case_id=${CASE_QUOTED}" \
  "1" \
  "jurisdiction_resolutions.count(case_id)"

pg_assert_int_eq \
  "select count(*) from requirement_sets where case_id=${CASE_QUOTED}" \
  "1" \
  "requirement_sets.count(case_id)"

# ---------------------------------------------------------------------------
# Phase 7: API read surfaces
# ---------------------------------------------------------------------------

echo "runbook: fetching_api_jurisdiction" >&2
HTTP_RESPONSE_FILE="$(mktemp /tmp/m004_s03_jurisdiction_XXXXXX)"
export HTTP_RESPONSE_FILE
HTTP_STATUS="$(_http_get_json "${API_BASE}/api/v1/cases/${CASE_ID}/jurisdiction")"
_assert_http_status "$HTTP_STATUS" "200" "get_jurisdiction"
cat "$HTTP_RESPONSE_FILE"
echo

echo "runbook: fetching_api_requirements" >&2
HTTP_RESPONSE_FILE="$(mktemp /tmp/m004_s03_requirements_XXXXXX)"
export HTTP_RESPONSE_FILE
HTTP_STATUS="$(_http_get_json "${API_BASE}/api/v1/cases/${CASE_ID}/requirements")"
_assert_http_status "$HTTP_STATUS" "200" "get_requirements"
cat "$HTTP_RESPONSE_FILE"
echo

# ---------------------------------------------------------------------------
# Phase 8: Postgres summary
# ---------------------------------------------------------------------------

echo "runbook: postgres_summary" >&2
pg_print "select event_type, to_state, count(*) from case_transition_ledger where case_id=${CASE_QUOTED} group by event_type, to_state order by event_type" >&2
pg_print "select case_id, project_id, case_state from permit_cases where case_id=${CASE_QUOTED}" >&2
pg_print "select jurisdiction_resolution_id, support_level from jurisdiction_resolutions where case_id=${CASE_QUOTED}" >&2
pg_print "select requirement_set_id, freshness_state from requirement_sets where case_id=${CASE_QUOTED}" >&2

# Signal inspection hint for operators.
echo "runbook: structured_log_hint hint='docker compose logs worker | grep fixture_case_id'" >&2

echo "runbook: ok" >&2
