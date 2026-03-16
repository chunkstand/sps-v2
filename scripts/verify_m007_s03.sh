#!/usr/bin/env bash
# shellcheck shell=bash
set -euo pipefail

# M007 / S03 runbook verification: intake → reviewer decision → submission attempt → status ingest.
#
# What this does:
#   1) Ensures docker compose services are up (Postgres + Temporal + Temporal UI + MinIO)
#   2) Applies Alembic migrations
#   3) Starts the FastAPI server + worker against a unique task queue
#   4) Clears Phase 6/7 fixture rows to keep deterministic reruns
#   5) POSTs /api/v1/cases intake, posts reviewer decision, and runs workflow to submission
#   6) Fetches submission attempts + receipt evidence metadata + download URL
#   7) Ingests an external status event and asserts Postgres persistence
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
#   SPS_REVIEWER_API_KEY (default: dev-reviewer-key)
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

REVIEWER_API_KEY="${SPS_REVIEWER_API_KEY:-dev-reviewer-key}"
API_HOST="${API_HOST:-localhost}"
API_PORT="${API_PORT:-8000}"
API_BASE="http://${API_HOST}:${API_PORT}"

RUNBOOK_TS="$(date +%Y%m%d_%H%M%S)"
: "${SPS_TEMPORAL_TASK_QUEUE:=sps-permit-case-runbook-${RUNBOOK_TS}-$$}"
export SPS_TEMPORAL_TASK_QUEUE

CASE_ID=""
PROJECT_ID=""
DECISION_ID=""
SUBMISSION_ATTEMPT_ID=""
RECEIPT_ARTIFACT_ID=""
RAW_STATUS=""
EXTERNAL_EVENT_ID=""
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
  local out_file="${HTTP_RESPONSE_FILE:-/tmp/m007_s03_response_$$.json}"

  curl -s -o "$out_file" -w "%{http_code}" \
    -X POST "$url" \
    -H "Content-Type: application/json" \
    -d "$body"
}

_http_post_json_with_key() {
  local url="$1"
  local body="$2"
  local api_key="$3"
  local out_file="${HTTP_RESPONSE_FILE:-/tmp/m007_s03_response_$$.json}"

  curl -s -o "$out_file" -w "%{http_code}" \
    -X POST "$url" \
    -H "Content-Type: application/json" \
    -H "X-Reviewer-Api-Key: ${api_key}" \
    -d "$body"
}

_http_get_json() {
  local url="$1"
  local out_file="${HTTP_RESPONSE_FILE:-/tmp/m007_s03_response_$$.json}"

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

_poll_ledger_for_submission_state() {
  local case_id_quoted="$1"
  local timeout_seconds="$2"

  local deadline=$((SECONDS + timeout_seconds))
  while (( SECONDS < deadline )); do
    local count
    count="$(pg_exec "select count(*) from case_transition_ledger where case_id=${case_id_quoted} and event_type='CASE_STATE_CHANGED' and to_state in ('SUBMITTED','MANUAL_SUBMISSION_REQUIRED')" 2>/dev/null || echo 0)"
    count="${count%$'\n'}"
    if [[ "$count" =~ ^[0-9]+$ ]] && [[ "$count" != "0" ]]; then
      return 0
    fi
    sleep 0.5
  done

  echo "runbook.fail: workflow_not_submitted case_id=${case_id_quoted} timeout=${timeout_seconds}s" >&2
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

_parse_submission_attempt() {
  "$PYTHON" - <<'PY'
import json
import os
import sys

path = os.environ.get("HTTP_RESPONSE_FILE")
if not path or not os.path.isfile(path):
    sys.exit(1)
with open(path, "r", encoding="utf-8") as fh:
    payload = json.load(fh)

attempts = payload.get("submission_attempts") or []
if not attempts:
    sys.exit(1)

attempt = attempts[0]
values = [
    attempt.get("submission_attempt_id") or "",
    attempt.get("status") or "",
    attempt.get("outcome") or "",
    attempt.get("receipt_artifact_id") or "",
]
print("\t".join(values))
PY
}

# ---------------------------------------------------------------------------
# Phase 0: Load fixture IDs + set overrides
# ---------------------------------------------------------------------------

FIXTURE_PHASE6_CASE_ID="$($PYTHON - <<'PY'
import json
from pathlib import Path
path = Path("specs/sps/build-approved/fixtures/phase6/documents.json")
with path.open("r", encoding="utf-8") as handle:
    payload = json.load(handle)
print(payload["document_sets"][0]["case_id"])
PY
)"

FIXTURE_PHASE7_CASE_ID="$($PYTHON - <<'PY'
import json
from pathlib import Path
path = Path("specs/sps/build-approved/fixtures/phase7/submission_adapter.json")
with path.open("r", encoding="utf-8") as handle:
    payload = json.load(handle)

for fixture in payload.get("adapter_inputs", []):
    if fixture.get("portal_support_level") == "FULLY_SUPPORTED":
        print(fixture.get("case_id"))
        raise SystemExit(0)

raise SystemExit(1)
PY
)"

RAW_STATUS="$($PYTHON - <<'PY'
import json
from pathlib import Path
path = Path("specs/sps/build-approved/fixtures/phase7/status-maps.json")
with path.open("r", encoding="utf-8") as handle:
    payload = json.load(handle)

status_map = payload.get("status_maps", [])[0]
mapping = status_map.get("mappings", [])[0]
print(mapping.get("raw_status"))
PY
)"

FIXTURE_DOC_IDS=()
while IFS= read -r line; do
  [[ -n "$line" ]] && FIXTURE_DOC_IDS+=("$line")
done < <("$PYTHON" - <<'PY'
import json
from pathlib import Path
path = Path("specs/sps/build-approved/fixtures/phase6/documents.json")
with path.open("r", encoding="utf-8") as handle:
    payload = json.load(handle)

docs = payload.get("document_sets", [])[0].get("documents", [])
for doc in docs:
    doc_id = doc.get("document_id")
    if doc_id:
        print(doc_id)
PY
)

FIXTURE_CASE_ID_PHASE4="$($PYTHON - <<'PY'
import json
from pathlib import Path

path = Path("specs/sps/build-approved/fixtures/phase4/jurisdiction.json")
with path.open("r", encoding="utf-8") as handle:
    payload = json.load(handle)
print(payload["jurisdictions"][0]["case_id"])
PY
)"

FIXTURE_CASE_ID_PHASE5="$($PYTHON - <<'PY'
import json
from pathlib import Path

path = Path("specs/sps/build-approved/fixtures/phase5/compliance.json")
with path.open("r", encoding="utf-8") as handle:
    payload = json.load(handle)
print(payload["evaluations"][0]["case_id"])
PY
)"

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

FIXTURE_COMPLIANCE_IDS=()
while IFS= read -r line; do
  [[ -n "$line" ]] && FIXTURE_COMPLIANCE_IDS+=("$line")
done < <("$PYTHON" - <<'PY'
import json
from pathlib import Path

path = Path("specs/sps/build-approved/fixtures/phase5/compliance.json")
with path.open("r", encoding="utf-8") as handle:
    payload = json.load(handle)
case_id = payload["evaluations"][0]["case_id"]
ids = [item["compliance_evaluation_id"] for item in payload["evaluations"] if item.get("case_id") == case_id]
for item in ids:
    print(item)
PY
)

FIXTURE_INCENTIVE_IDS=()
while IFS= read -r line; do
  [[ -n "$line" ]] && FIXTURE_INCENTIVE_IDS+=("$line")
done < <("$PYTHON" - <<'PY'
import json
from pathlib import Path

path = Path("specs/sps/build-approved/fixtures/phase5/incentives.json")
with path.open("r", encoding="utf-8") as handle:
    payload = json.load(handle)
case_id = payload["assessments"][0]["case_id"]
ids = [item["incentive_assessment_id"] for item in payload["assessments"] if item.get("case_id") == case_id]
for item in ids:
    print(item)
PY
)

if [[ -z "$FIXTURE_PHASE6_CASE_ID" || -z "$FIXTURE_PHASE7_CASE_ID" || -z "$RAW_STATUS" || -z "$FIXTURE_CASE_ID_PHASE4" || -z "$FIXTURE_CASE_ID_PHASE5" ]]; then
  echo "runbook.fail: missing_fixture_ids" >&2
  exit 1
fi

if [[ ${#FIXTURE_JUR_IDS[@]} -eq 0 || ${#FIXTURE_REQ_IDS[@]} -eq 0 || ${#FIXTURE_COMPLIANCE_IDS[@]} -eq 0 || ${#FIXTURE_INCENTIVE_IDS[@]} -eq 0 ]]; then
  echo "runbook.fail: missing_phase4_phase5_fixture_ids" >&2
  exit 1
fi

export SPS_PHASE4_FIXTURE_CASE_ID_OVERRIDE="$FIXTURE_CASE_ID_PHASE4"
export SPS_PHASE5_FIXTURE_CASE_ID_OVERRIDE="$FIXTURE_CASE_ID_PHASE5"
export SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE="$FIXTURE_PHASE6_CASE_ID"
export SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE="$FIXTURE_PHASE7_CASE_ID"

echo "runbook: fixture_override_enabled phase4_case_id=$SPS_PHASE4_FIXTURE_CASE_ID_OVERRIDE phase5_case_id=$SPS_PHASE5_FIXTURE_CASE_ID_OVERRIDE phase6_case_id=$SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE phase7_case_id=$SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE" >&2

echo "runbook: fixture_raw_status raw_status=$RAW_STATUS" >&2

# ---------------------------------------------------------------------------
# Phase 1: Ensure infrastructure is up
# ---------------------------------------------------------------------------

echo "runbook: ensuring_docker_compose_stack" >&2
docker compose up -d postgres temporal temporal-ui minio minio-init >/dev/null

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
_wait_for_tcp "127.0.0.1" "9000" 30

# ---------------------------------------------------------------------------
# Phase 2: Migrations
# ---------------------------------------------------------------------------

echo "runbook: applying_migrations" >&2
"$ALEMBIC" upgrade head >/dev/null

# ---------------------------------------------------------------------------
# Phase 3: Clear deterministic fixture rows
# ---------------------------------------------------------------------------

pg_assert_no_single_quotes "$FIXTURE_PHASE6_CASE_ID"
pg_assert_no_single_quotes "$FIXTURE_PHASE7_CASE_ID"
pg_assert_no_single_quotes "$FIXTURE_CASE_ID_PHASE4"
pg_assert_no_single_quotes "$FIXTURE_CASE_ID_PHASE5"
PHASE6_CASE_QUOTED="$(pg_sql_quote "$FIXTURE_PHASE6_CASE_ID")"
PHASE7_CASE_QUOTED="$(pg_sql_quote "$FIXTURE_PHASE7_CASE_ID")"
PHASE4_CASE_QUOTED="$(pg_sql_quote "$FIXTURE_CASE_ID_PHASE4")"
PHASE5_CASE_QUOTED="$(pg_sql_quote "$FIXTURE_CASE_ID_PHASE5")"

pg_exec "delete from jurisdiction_resolutions where case_id=${PHASE4_CASE_QUOTED}" >/dev/null
pg_exec "delete from requirement_sets where case_id=${PHASE4_CASE_QUOTED}" >/dev/null
pg_exec "delete from compliance_evaluations where case_id=${PHASE5_CASE_QUOTED}" >/dev/null
pg_exec "delete from incentive_assessments where case_id=${PHASE5_CASE_QUOTED}" >/dev/null

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

for comp_id in "${FIXTURE_COMPLIANCE_IDS[@]}"; do
  pg_assert_no_single_quotes "$comp_id"
  COMP_QUOTED="$(pg_sql_quote "$comp_id")"
  pg_exec "delete from compliance_evaluations where compliance_evaluation_id=${COMP_QUOTED}" >/dev/null
done

for inc_id in "${FIXTURE_INCENTIVE_IDS[@]}"; do
  pg_assert_no_single_quotes "$inc_id"
  INC_QUOTED="$(pg_sql_quote "$inc_id")"
  pg_exec "delete from incentive_assessments where incentive_assessment_id=${INC_QUOTED}" >/dev/null
done

for doc_id in "${FIXTURE_DOC_IDS[@]}"; do
  pg_assert_no_single_quotes "$doc_id"
  DOC_QUOTED="$(pg_sql_quote "$doc_id")"
  pg_exec "delete from document_artifacts where document_id=${DOC_QUOTED}" >/dev/null
  pg_exec "delete from evidence_artifacts where linked_object_id=${DOC_QUOTED}" >/dev/null
  pg_exec "delete from evidence_artifacts where provenance->>'document_id'=${DOC_QUOTED}" >/dev/null
  echo "runbook: fixture_doc_cleanup document_id=$doc_id" >&2
done

pg_exec "delete from external_status_events where case_id=${PHASE6_CASE_QUOTED} or case_id=${PHASE7_CASE_QUOTED}" >/dev/null
pg_exec "delete from manual_fallback_packages where case_id=${PHASE6_CASE_QUOTED} or case_id=${PHASE7_CASE_QUOTED}" >/dev/null
pg_exec "delete from submission_attempts where case_id=${PHASE6_CASE_QUOTED} or case_id=${PHASE7_CASE_QUOTED}" >/dev/null
pg_exec "delete from submission_packages where case_id=${PHASE6_CASE_QUOTED} or case_id=${PHASE7_CASE_QUOTED}" >/dev/null
pg_exec "delete from permit_cases where case_id=${PHASE6_CASE_QUOTED} or case_id=${PHASE7_CASE_QUOTED}" >/dev/null
pg_exec "delete from projects where case_id=${PHASE6_CASE_QUOTED} or case_id=${PHASE7_CASE_QUOTED}" >/dev/null

echo "runbook: fixture_cleanup_ok" >&2

# ---------------------------------------------------------------------------
# Phase 4: Start FastAPI server + worker
# ---------------------------------------------------------------------------

mkdir -p "$ROOT_DIR/.gsd/runbook"
API_LOG="$ROOT_DIR/.gsd/runbook/m007_s03_api_${RUNBOOK_TS}_$$.log"
WORKER_LOG="$ROOT_DIR/.gsd/runbook/m007_s03_worker_${RUNBOOK_TS}_$$.log"

echo "runbook: starting_api log=$API_LOG port=$API_PORT" >&2
"$PYTHON" -m uvicorn sps.api.main:app --host 0.0.0.0 --port "$API_PORT" >"$API_LOG" 2>&1 &
API_PID=$!

_wait_for_api_ready 30
echo "runbook: api_ready pid=$API_PID" >&2

echo "runbook: starting_worker log=$WORKER_LOG" >&2
"$PYTHON" -m sps.workflows.worker >"$WORKER_LOG" 2>&1 &
WORKER_PID=$!

_wait_for_worker_ready 30
echo "runbook: worker_ready pid=$WORKER_PID" >&2

# ---------------------------------------------------------------------------
# Phase 5: Intake API
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
HTTP_RESPONSE_FILE="$(mktemp /tmp/m007_s03_resp_XXXXXX)"
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

pg_assert_no_single_quotes "$CASE_ID"
pg_assert_no_single_quotes "$PROJECT_ID"
CASE_QUOTED="$(pg_sql_quote "$CASE_ID")"
PROJECT_QUOTED="$(pg_sql_quote "$PROJECT_ID")"

# Wait for initial workflow to move to INTAKE_COMPLETE

echo "runbook: waiting_for_intake_complete" >&2
_poll_ledger_for_state "$CASE_QUOTED" "INTAKE_COMPLETE" 30

# ---------------------------------------------------------------------------
# Phase 6: Reviewer decision
# ---------------------------------------------------------------------------

DECISION_ID="DEC-$(date +%Y%m%d%H%M%S)-$$"
IDEMPOTENCY_KEY="runbook/${CASE_ID}"
REVIEWER_ID="reviewer-runbook"
SUBJECT_AUTHOR_ID="author-runbook"

DECISION_BODY="$(cat <<JSON
{
  "decision_id": "${DECISION_ID}",
  "idempotency_key": "${IDEMPOTENCY_KEY}",
  "case_id": "${CASE_ID}",
  "reviewer_id": "${REVIEWER_ID}",
  "subject_author_id": "${SUBJECT_AUTHOR_ID}",
  "outcome": "ACCEPT"
}
JSON
)"

echo "runbook: posting_review_decision decision_id=$DECISION_ID" >&2
HTTP_RESPONSE_FILE="$(mktemp /tmp/m007_s03_review_XXXXXX)"
export HTTP_RESPONSE_FILE

HTTP_STATUS="$(_http_post_json_with_key "${API_BASE}/api/v1/reviews/decisions" "$DECISION_BODY" "$REVIEWER_API_KEY")"
_assert_http_status "$HTTP_STATUS" "201" "post_review_decision"

echo "runbook: reviewer_api_201_ok decision_id=$DECISION_ID" >&2
if [[ -f "$HTTP_RESPONSE_FILE" ]]; then
  cat "$HTTP_RESPONSE_FILE"
  echo
fi

pg_assert_no_single_quotes "$DECISION_ID"
pg_assert_no_single_quotes "$IDEMPOTENCY_KEY"
DEC_QUOTED="$(pg_sql_quote "$DECISION_ID")"
IDEM_QUOTED="$(pg_sql_quote "$IDEMPOTENCY_KEY")"

pg_assert_int_eq \
  "select count(*) from review_decisions where decision_id=${DEC_QUOTED}" \
  "1" \
  "review_decisions.count(decision_id)"

# ---------------------------------------------------------------------------
# Phase 7: Run workflow to submission
# ---------------------------------------------------------------------------

echo "runbook: starting_workflow_for_incentives" >&2
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
    await asyncio.wait_for(handle.result(), timeout=120.0)

asyncio.run(main())
PY

_echo_incentives="runbook: waiting_for_incentives_complete"
echo "$_echo_incentives" >&2
_poll_ledger_for_state "$CASE_QUOTED" "INCENTIVES_COMPLETE" 90

echo "runbook: starting_workflow_for_submission" >&2
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
    await asyncio.wait_for(handle.result(), timeout=120.0)

asyncio.run(main())
PY

echo "runbook: waiting_for_submission_state" >&2
_poll_ledger_for_submission_state "$CASE_QUOTED" 90

# ---------------------------------------------------------------------------
# Phase 8: Fetch submission attempts + receipt evidence
# ---------------------------------------------------------------------------

echo "runbook: fetching_submission_attempts" >&2
HTTP_RESPONSE_FILE="$(mktemp /tmp/m007_s03_attempts_XXXXXX)"
export HTTP_RESPONSE_FILE

HTTP_STATUS="$(_http_get_json "${API_BASE}/api/v1/cases/${CASE_ID}/submission-attempts")"
_assert_http_status "$HTTP_STATUS" "200" "get_submission_attempts"

ATTEMPT_LINE="$(_parse_submission_attempt)"
SUBMISSION_ATTEMPT_ID="$(printf "%s" "$ATTEMPT_LINE" | awk -F '\t' '{print $1}')"
ATTEMPT_STATUS="$(printf "%s" "$ATTEMPT_LINE" | awk -F '\t' '{print $2}')"
ATTEMPT_OUTCOME="$(printf "%s" "$ATTEMPT_LINE" | awk -F '\t' '{print $3}')"
RECEIPT_ARTIFACT_ID="$(printf "%s" "$ATTEMPT_LINE" | awk -F '\t' '{print $4}')"

if [[ -z "$SUBMISSION_ATTEMPT_ID" ]]; then
  echo "runbook.fail: missing_submission_attempt_id" >&2
  exit 1
fi

if [[ "$ATTEMPT_STATUS" != "SUBMITTED" ]]; then
  echo "runbook.fail: unexpected_submission_status status=$ATTEMPT_STATUS outcome=$ATTEMPT_OUTCOME" >&2
  exit 1
fi

if [[ -z "$RECEIPT_ARTIFACT_ID" ]]; then
  echo "runbook.fail: missing_receipt_artifact" >&2
  exit 1
fi

echo "runbook: submission_attempt_ok attempt_id=$SUBMISSION_ATTEMPT_ID status=$ATTEMPT_STATUS outcome=$ATTEMPT_OUTCOME" >&2

if [[ -f "$HTTP_RESPONSE_FILE" ]]; then
  cat "$HTTP_RESPONSE_FILE"
  echo
fi

pg_assert_no_single_quotes "$SUBMISSION_ATTEMPT_ID"
pg_assert_no_single_quotes "$RECEIPT_ARTIFACT_ID"
ATTEMPT_QUOTED="$(pg_sql_quote "$SUBMISSION_ATTEMPT_ID")"
RECEIPT_QUOTED="$(pg_sql_quote "$RECEIPT_ARTIFACT_ID")"

# Evidence metadata

echo "runbook: fetching_receipt_metadata" >&2
HTTP_RESPONSE_FILE="$(mktemp /tmp/m007_s03_receipt_meta_XXXXXX)"
export HTTP_RESPONSE_FILE
HTTP_STATUS="$(_http_get_json "${API_BASE}/api/v1/evidence/artifacts/${RECEIPT_ARTIFACT_ID}")"
_assert_http_status "$HTTP_STATUS" "200" "get_receipt_metadata"
cat "$HTTP_RESPONSE_FILE"
echo

# Evidence download URL

echo "runbook: fetching_receipt_download_url" >&2
HTTP_RESPONSE_FILE="$(mktemp /tmp/m007_s03_receipt_dl_XXXXXX)"
export HTTP_RESPONSE_FILE
HTTP_STATUS="$(_http_get_json "${API_BASE}/api/v1/evidence/artifacts/${RECEIPT_ARTIFACT_ID}/download")"
_assert_http_status "$HTTP_STATUS" "200" "get_receipt_download"
cat "$HTTP_RESPONSE_FILE"
echo

echo "runbook.pass: receipt_evidence_ok artifact_id=$RECEIPT_ARTIFACT_ID" >&2

# ---------------------------------------------------------------------------
# Phase 9: Ingest external status event
# ---------------------------------------------------------------------------

EXTERNAL_EVENT_ID="ESE-$(date +%Y%m%d%H%M%S)-$$"
pg_assert_no_single_quotes "$EXTERNAL_EVENT_ID"
EXTERNAL_BODY="$(cat <<JSON
{
  "event_id": "${EXTERNAL_EVENT_ID}",
  "submission_attempt_id": "${SUBMISSION_ATTEMPT_ID}",
  "raw_status": "${RAW_STATUS}",
  "evidence_ids": ["${RECEIPT_ARTIFACT_ID}"]
}
JSON
)"

echo "runbook: ingesting_external_status event_id=$EXTERNAL_EVENT_ID raw_status=$RAW_STATUS" >&2
HTTP_RESPONSE_FILE="$(mktemp /tmp/m007_s03_status_XXXXXX)"
export HTTP_RESPONSE_FILE
HTTP_STATUS="$(_http_post_json "${API_BASE}/api/v1/cases/${CASE_ID}/external-status-events" "$EXTERNAL_BODY")"
_assert_http_status "$HTTP_STATUS" "201" "post_external_status"
cat "$HTTP_RESPONSE_FILE"
echo

echo "runbook.pass: external_status_ingest_ok event_id=$EXTERNAL_EVENT_ID" >&2

# ---------------------------------------------------------------------------
# Phase 10: Postgres assertions
# ---------------------------------------------------------------------------

pg_assert_int_eq \
  "select count(*) from submission_attempts where submission_attempt_id=${ATTEMPT_QUOTED}" \
  "1" \
  "submission_attempts.count(submission_attempt_id)"

pg_assert_int_eq \
  "select count(*) from evidence_artifacts where artifact_id=${RECEIPT_QUOTED}" \
  "1" \
  "evidence_artifacts.count(receipt_artifact_id)"

pg_assert_int_eq \
  "select count(*) from external_status_events where event_id=$(pg_sql_quote "$EXTERNAL_EVENT_ID")" \
  "1" \
  "external_status_events.count(event_id)"

echo "runbook.pass: postgres_assertions_ok" >&2

# ---------------------------------------------------------------------------
# Phase 11: Postgres summary
# ---------------------------------------------------------------------------

echo "runbook: postgres_summary" >&2
pg_print "select event_type, to_state, count(*) from case_transition_ledger where case_id=${CASE_QUOTED} group by event_type, to_state order by event_type" >&2
pg_print "select submission_attempt_id, status, outcome from submission_attempts where submission_attempt_id=${ATTEMPT_QUOTED}" >&2
pg_print "select event_id, raw_status, normalized_status from external_status_events where event_id=$(pg_sql_quote "$EXTERNAL_EVENT_ID")" >&2

echo "runbook: structured_log_hint hint='docker compose logs worker | grep submission_attempt'" >&2

echo "runbook: ok" >&2
