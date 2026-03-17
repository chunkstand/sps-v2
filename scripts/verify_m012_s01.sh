#!/usr/bin/env bash
# shellcheck shell=bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-$ROOT_DIR/.venv/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  echo "runbook.fail: assertion_description=python_not_found expected=.venv/bin/python actual=$PYTHON" >&2
  exit 2
fi

API_HOST="${API_HOST:-localhost}"
API_PORT="${API_PORT:-8000}"
API_BASE="http://${API_HOST}:${API_PORT}"

export SPS_TEMPORAL_ADDRESS="${SPS_TEMPORAL_ADDRESS:-localhost:7233}"
export SPS_DB_DSN="${SPS_DB_DSN:-postgresql+psycopg://sps:sps@localhost:5432/sps}"
export SPS_LOG_LEVEL="${SPS_LOG_LEVEL:-info}"

WORKER_PID=""
API_PID=""

runbook_step() {
  echo "runbook.step: step_num=$1 step_description=$2" >&2
}

runbook_pass() {
  echo "runbook.pass: assertion_description=$1" >&2
}

runbook_fail() {
  echo "runbook.fail: assertion_description=$1 expected=$2 actual=$3" >&2
}

cleanup() {
  if [[ -n "${WORKER_PID}" ]]; then
    kill "$WORKER_PID" 2>/dev/null || true
  fi
  if [[ -n "${API_PID}" ]]; then
    kill "$API_PID" 2>/dev/null || true
  fi
  docker compose down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

runbook_step 1 "Provisioning docker-compose stack"
bash scripts/start_temporal_dev.sh

# Ensure Temporal namespace exists for workflow signals
TEMPORAL_INTERNAL_HOST=$(docker compose exec -T temporal sh -c "hostname -i | awk '{print \$1}'")
if [[ -z "$TEMPORAL_INTERNAL_HOST" ]]; then
  runbook_fail "temporal_namespace" "default" "host_lookup_failed"
  exit 1
fi
namespace_attempt=0
until docker compose exec -T temporal sh -c "TEMPORAL_CLI_ADDRESS=${TEMPORAL_INTERNAL_HOST}:7233 tctl namespace describe default" >/dev/null 2>&1; do
  namespace_attempt=$((namespace_attempt + 1))
  if [[ $namespace_attempt -gt 15 ]]; then
    runbook_fail "temporal_namespace" "default" "missing"
    exit 1
  fi
  docker compose exec -T temporal sh -c "TEMPORAL_CLI_ADDRESS=${TEMPORAL_INTERNAL_HOST}:7233 tctl namespace register --retention 1 default" >/dev/null 2>&1 || true
  sleep 2
done
runbook_pass "temporal_namespace_ready"

runbook_step 2 "Starting API server"
"$PYTHON" -m uvicorn sps.api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "runbook: api_started pid=$API_PID" >&2

max_attempts=30
attempt=0
while ! curl -sf "${API_BASE}/healthz" > /dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ $attempt -ge $max_attempts ]; then
    runbook_fail "api_readiness" "ready" "timeout"
    exit 1
  fi
  sleep 1
done
runbook_pass "api_ready"

ESCALATION_TOKEN="$($PYTHON - <<'PY'
from tests.helpers.auth_tokens import build_jwt
print(build_jwt(subject="escalation-owner-runbook", roles=["escalation-owner"]))
PY
)"
REVIEWER_TOKEN="$($PYTHON - <<'PY'
from tests.helpers.auth_tokens import build_jwt
print(build_jwt(subject="reviewer-runbook", roles=["reviewer"]))
PY
)"
INTAKE_TOKEN="$($PYTHON - <<'PY'
from tests.helpers.auth_tokens import build_jwt
print(build_jwt(subject="intake-runbook", roles=["intake"]))
PY
)"

if [[ -z "$ESCALATION_TOKEN" || -z "$REVIEWER_TOKEN" || -z "$INTAKE_TOKEN" ]]; then
  runbook_fail "token_generation" "non_empty_tokens" "missing"
  exit 1
fi

runbook_step 3 "Create emergency case + override cases"
CASE_EMERGENCY_RESPONSE_FILE="$(mktemp /tmp/m012_s01_case_emergency_XXXXXX)"
CASE_EMERGENCY_STATUS=$(curl -sS -o "$CASE_EMERGENCY_RESPONSE_FILE" -w "%{http_code}" \
  -X POST "${API_BASE}/api/v1/cases" \
  -H "Authorization: Bearer ${INTAKE_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\
    \"tenant_id\": \"tenant-runbook\",\
    \"intake_mode\": \"PORTAL\",\
    \"project_description\": \"Runbook emergency case\",\
    \"site_address\": {\"line1\": \"123 Runbook Way\", \"city\": \"Testville\", \"state\": \"CA\", \"postal_code\": \"90210\"},\
    \"requester\": {\"name\": \"Runbook Requester\", \"email\": \"runbook@example.com\"},\
    \"project_type\": \"SOLAR_PV\",\
    \"system_size_kw\": 5.0,\
    \"battery_flag\": false,\
    \"service_upgrade_flag\": false,\
    \"trenching_flag\": false,\
    \"structural_modification_flag\": false\
  }")

if [[ "$CASE_EMERGENCY_STATUS" != "201" ]]; then
  runbook_fail "create_case_emergency" "201" "$CASE_EMERGENCY_STATUS"
  cat "$CASE_EMERGENCY_RESPONSE_FILE" >&2
  exit 1
fi

CASE_EMERGENCY_ID="$($PYTHON - <<PY
import json
with open("$CASE_EMERGENCY_RESPONSE_FILE") as fp:
    payload = json.load(fp)
print(payload["case_id"])
PY
)"

if [[ -z "$CASE_EMERGENCY_ID" ]]; then
  runbook_fail "parse_case_emergency" "case_id" "empty"
  exit 1
fi

runbook_pass "case_emergency_created"

CASE_OVERRIDE_VALID="CASE-OVERRIDE-VALID-$(date +%s)"
CASE_OVERRIDE_EXPIRED="CASE-OVERRIDE-EXPIRED-$(date +%s)"

for CASE_ID in "$CASE_OVERRIDE_VALID" "$CASE_OVERRIDE_EXPIRED"; do
  docker compose exec -T postgres psql -U sps -d sps <<EOF
INSERT INTO permit_cases (
  case_id, tenant_id, project_id, case_state, review_state,
  submission_mode, portal_support_level, current_release_profile,
  legal_hold, closure_reason
) VALUES (
  '${CASE_ID}', 'tenant-runbook', 'project-${CASE_ID}', 'REVIEW_PENDING', 'PENDING',
  'AUTOMATED', 'FULLY_SUPPORTED', 'default',
  false, NULL
) ON CONFLICT (case_id) DO NOTHING;
EOF
  if [ $? -ne 0 ]; then
    runbook_fail "seed_override_case" "insert_ok" "psql_error"
    exit 1
  fi
  runbook_pass "override_case_seeded_${CASE_ID}"
done

# Ensure emergency case is in REVIEW_PENDING before workflow runs
docker compose exec -T postgres psql -U sps -d sps -c \
  "UPDATE permit_cases SET case_state='REVIEW_PENDING' WHERE case_id='${CASE_EMERGENCY_ID}';" >/dev/null
UPDATE_STATE_COUNT=$(docker compose exec -T postgres psql -U sps -d sps -t -A -c \
  "SELECT COUNT(*) FROM permit_cases WHERE case_id='${CASE_EMERGENCY_ID}' AND case_state='REVIEW_PENDING';")
UPDATE_STATE_COUNT=$(echo "$UPDATE_STATE_COUNT" | tr -d '[:space:]')
if [[ "$UPDATE_STATE_COUNT" != "1" ]]; then
  runbook_fail "case_emergency_state_update" "1" "$UPDATE_STATE_COUNT"
  exit 1
fi
runbook_pass "case_emergency_review_pending"

runbook_step 4 "Create emergency + overrides"
EMERGENCY_RESPONSE_FILE="$(mktemp /tmp/m012_s01_emergency_XXXXXX)"
EMERGENCY_STATUS=$(curl -sS -o "$EMERGENCY_RESPONSE_FILE" -w "%{http_code}" \
  -X POST "${API_BASE}/api/v1/emergencies/" \
  -H "Authorization: Bearer ${ESCALATION_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\
    \"incident_id\": \"INC-${CASE_EMERGENCY_ID}\",\
    \"case_id\": \"${CASE_EMERGENCY_ID}\",\
    \"scope\": \"full_case\",\
    \"allowed_bypasses\": [\"WORKFLOW_GUARD_SKIP\"],\
    \"forbidden_bypasses\": []\
  }")

if [[ "$EMERGENCY_STATUS" != "201" ]]; then
  runbook_fail "create_emergency" "201" "$EMERGENCY_STATUS"
  cat "$EMERGENCY_RESPONSE_FILE" >&2
  exit 1
fi

EMERGENCY_ID="$($PYTHON - <<PY
import json
with open("$EMERGENCY_RESPONSE_FILE") as fp:
    payload = json.load(fp)
print(payload["emergency_id"])
PY
)"

if [[ -z "$EMERGENCY_ID" ]]; then
  runbook_fail "parse_emergency_id" "emergency_id" "empty"
  exit 1
fi

EMERGENCY_ROW=$(docker compose exec -T postgres psql -U sps -d sps -t -c \
  "SELECT emergency_id FROM emergency_records WHERE emergency_id='${EMERGENCY_ID}'")
EMERGENCY_ROW=$(echo "$EMERGENCY_ROW" | tr -d '[:space:]')
if [[ "$EMERGENCY_ROW" != "$EMERGENCY_ID" ]]; then
  runbook_fail "emergency_record_present" "$EMERGENCY_ID" "${EMERGENCY_ROW:-missing}"
  exit 1
fi
runbook_pass "emergency_record_verified"

create_override() {
  local case_id="$1"
  local response_file
  response_file="$(mktemp /tmp/m012_s01_override_XXXXXX)"
  local status
  status=$(curl -sS -o "$response_file" -w "%{http_code}" \
    -X POST "${API_BASE}/api/v1/overrides/" \
    -H "Authorization: Bearer ${ESCALATION_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\
      \"case_id\": \"${case_id}\",\
      \"scope\": \"review_transition\",\
      \"justification\": \"Runbook override\",\
      \"duration_hours\": 12,\
      \"affected_surfaces\": [\"REVIEW_PENDING->APPROVED_FOR_SUBMISSION\"]\
    }")
  if [[ "$status" != "201" ]]; then
    runbook_fail "create_override_${case_id}" "201" "$status"
    cat "$response_file" >&2
    exit 1
  fi
  local override_id
  override_id="$($PYTHON - <<PY
import json
with open("$response_file") as fp:
    payload = json.load(fp)
print(payload["override_id"])
PY
)"
  if [[ -z "$override_id" ]]; then
    runbook_fail "parse_override_${case_id}" "override_id" "empty"
    exit 1
  fi
  local row
  row=$(docker compose exec -T postgres psql -U sps -d sps -t -c \
    "SELECT override_id FROM override_artifacts WHERE override_id='${override_id}'")
  row=$(echo "$row" | tr -d '[:space:]')
  if [[ "$row" != "$override_id" ]]; then
    runbook_fail "override_record_present_${case_id}" "$override_id" "${row:-missing}"
    exit 1
  fi
  runbook_pass "override_record_verified_${case_id}"
  echo "$override_id"
}

OVERRIDE_VALID_ID=$(create_override "$CASE_OVERRIDE_VALID")
OVERRIDE_EXPIRED_ID=$(create_override "$CASE_OVERRIDE_EXPIRED")

runbook_step 5 "Seed contradictions + review decisions"
seed_contradiction() {
  local case_id="$1"
  local contradiction_id="CONTRA-${case_id}"
  local response_file
  response_file="$(mktemp /tmp/m012_s01_contradiction_XXXXXX)"
  local status
  status=$(curl -sS -o "$response_file" -w "%{http_code}" \
    -X POST "${API_BASE}/api/v1/contradictions/" \
    -H "Authorization: Bearer ${REVIEWER_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\
      \"contradiction_id\": \"${contradiction_id}\",\
      \"case_id\": \"${case_id}\",\
      \"scope\": \"plan_review\",\
      \"source_a\": \"Doc A\",\
      \"source_b\": \"Doc B\",\
      \"ranking_relation\": \"conflict\",\
      \"blocking_effect\": true\
    }")
  if [[ "$status" != "201" ]]; then
    runbook_fail "seed_contradiction_${case_id}" "201" "$status"
    cat "$response_file" >&2
    exit 1
  fi
  runbook_pass "contradiction_seeded_${case_id}"
}

seed_contradiction "$CASE_OVERRIDE_VALID"
seed_contradiction "$CASE_OVERRIDE_EXPIRED"

create_review_decision() {
  local case_id="$1"
  local decision_id="DEC-${case_id}"
  local response_file
  response_file="$(mktemp /tmp/m012_s01_review_decision_XXXXXX)"
  local status
  status=$(curl -sS -o "$response_file" -w "%{http_code}" \
    -X POST "${API_BASE}/api/v1/reviews/decisions" \
    -H "Authorization: Bearer ${REVIEWER_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\
      \"decision_id\": \"${decision_id}\",\
      \"idempotency_key\": \"idem-${decision_id}\",\
      \"case_id\": \"${case_id}\",\
      \"reviewer_id\": \"reviewer-runbook\",\
      \"subject_author_id\": \"author-runbook\",\
      \"outcome\": \"ACCEPT\"\
    }")
  if [[ "$status" != "201" ]]; then
    runbook_fail "create_review_decision_${case_id}" "201" "$status"
    cat "$response_file" >&2
    exit 1
  fi
  runbook_pass "review_decision_created_${case_id}"
  echo "$decision_id"
}

DECISION_VALID_ID=$(create_review_decision "$CASE_OVERRIDE_VALID")
DECISION_EXPIRED_ID=$(create_review_decision "$CASE_OVERRIDE_EXPIRED")

runbook_step 6 "Apply override-protected transition"
apply_transition() {
  local case_id="$1"
  local decision_id="$2"
  local override_id="$3"
  local request_id="$4"
  local expected_event="$5"

  local result_json
  result_json="$($PYTHON - <<PY
import json
import datetime as dt
from sps.workflows.permit_case.activities import apply_state_transition
from sps.workflows.permit_case.contracts import StateTransitionRequest, CaseState, ActorType

request = StateTransitionRequest(
    request_id="${request_id}",
    case_id="${case_id}",
    from_state=CaseState.REVIEW_PENDING,
    to_state=CaseState.APPROVED_FOR_SUBMISSION,
    actor_type=ActorType.system_guard,
    actor_id="system-guard",
    correlation_id="runbook-${case_id}",
    causation_id="runbook-${request_id}",
    required_review_id="${decision_id}",
    required_evidence_ids=[],
    override_id="${override_id}",
    requested_at=dt.datetime.now(dt.UTC),
    notes="runbook override transition",
)
result = apply_state_transition(request)
if hasattr(result, "model_dump"):
    payload = result.model_dump(mode="json")
elif hasattr(result, "dict"):
    payload = result.dict()
else:
    payload = result
print(json.dumps(payload, default=str))
PY
)"

  local actual_event
  actual_event="$($PYTHON - <<PY
import json
payload = json.loads('''${result_json}''')
print(payload.get("event_type", ""))
PY
)"

  if [[ "$actual_event" != "$expected_event" ]]; then
    runbook_fail "apply_transition_${case_id}" "$expected_event" "$actual_event"
    echo "$result_json" >&2
    exit 1
  fi
  runbook_pass "transition_result_${case_id}_${actual_event}"

  local ledger_event
  ledger_event=$(docker compose exec -T postgres psql -U sps -d sps -t -c \
    "SELECT event_type FROM case_transition_ledger WHERE transition_id='${request_id}'")
  ledger_event=$(echo "$ledger_event" | tr -d '[:space:]')
  if [[ "$ledger_event" != "$expected_event" ]]; then
    runbook_fail "ledger_event_${case_id}" "$expected_event" "${ledger_event:-missing}"
    exit 1
  fi
  runbook_pass "ledger_event_verified_${case_id}"
}

REQUEST_VALID_ID="transition-valid-${CASE_OVERRIDE_VALID}"
apply_transition "$CASE_OVERRIDE_VALID" "$DECISION_VALID_ID" "$OVERRIDE_VALID_ID" "$REQUEST_VALID_ID" "CASE_STATE_CHANGED"

# Expire override before attempting transition
runbook_step 7 "Expire override + verify OVERRIDE_DENIED"
docker compose exec -T postgres psql -U sps -d sps -c \
  "UPDATE override_artifacts SET expires_at = NOW() - '1 hour'::interval WHERE override_id='${OVERRIDE_EXPIRED_ID}';" >/dev/null
EXPIRE_RESULT=$(docker compose exec -T postgres psql -U sps -d sps -t -A -c \
  "SELECT COUNT(*) FROM override_artifacts WHERE override_id='${OVERRIDE_EXPIRED_ID}' AND expires_at < NOW();")
EXPIRE_RESULT=$(echo "$EXPIRE_RESULT" | tr -d '[:space:]')
if [[ "$EXPIRE_RESULT" != "1" ]]; then
  runbook_fail "override_expire" "1" "${EXPIRE_RESULT:-missing}"
  exit 1
fi
runbook_pass "override_expired"

REQUEST_EXPIRED_ID="transition-expired-${CASE_OVERRIDE_EXPIRED}"
apply_transition "$CASE_OVERRIDE_EXPIRED" "$DECISION_EXPIRED_ID" "$OVERRIDE_EXPIRED_ID" "$REQUEST_EXPIRED_ID" "OVERRIDE_DENIED"

GUARD_ASSERTION=$(docker compose exec -T postgres psql -U sps -d sps -t -c \
  "SELECT payload->>'guard_assertion_id' FROM case_transition_ledger WHERE transition_id='${REQUEST_EXPIRED_ID}'")
GUARD_ASSERTION=$(echo "$GUARD_ASSERTION" | tr -d '[:space:]')
if [[ "$GUARD_ASSERTION" != "INV-SPS-EMERG-001" ]]; then
  runbook_fail "override_guard_assertion" "INV-SPS-EMERG-001" "${GUARD_ASSERTION:-missing}"
  exit 1
fi
runbook_pass "override_guard_assertion_verified"

runbook_step 8 "Start worker + emergency hold exit"
"$PYTHON" -m sps.workflows.worker &
WORKER_PID=$!
echo "runbook: worker_started pid=$WORKER_PID" >&2
sleep 5

# Send EmergencyHoldEntry signal via Temporal client
EMERGENCY_ENTRY_RESULT="$($PYTHON - <<PY
import asyncio
from sps.workflows.temporal import connect_client
from sps.workflows.permit_case.contracts import EmergencyHoldRequest
from sps.workflows.permit_case.ids import permit_case_workflow_id

async def main():
    client = await connect_client()
    workflow_id = permit_case_workflow_id("${CASE_EMERGENCY_ID}")
    handle = client.get_workflow_handle(workflow_id)
    await handle.signal("EmergencyHoldEntry", EmergencyHoldRequest(emergency_id="${EMERGENCY_ID}"))
    return "ok"

print(asyncio.run(main()))
PY
)"

if [[ "$EMERGENCY_ENTRY_RESULT" != "ok" ]]; then
  runbook_fail "emergency_hold_entry_signal" "ok" "$EMERGENCY_ENTRY_RESULT"
  exit 1
fi

entry_attempt=0
ENTRY_FOUND="0"
while [[ $entry_attempt -lt 10 ]]; do
  ENTRY_FOUND=$(docker compose exec -T postgres psql -U sps -d sps -t -A -c \
    "SELECT COUNT(*) FROM case_transition_ledger WHERE case_id='${CASE_EMERGENCY_ID}' AND to_state='EMERGENCY_HOLD' AND event_type='CASE_STATE_CHANGED'")
  ENTRY_FOUND=$(echo "$ENTRY_FOUND" | tr -d '[:space:]')
  if [[ "$ENTRY_FOUND" == "1" ]]; then
    break
  fi
  entry_attempt=$((entry_attempt + 1))
  sleep 1
done

if [[ "$ENTRY_FOUND" != "1" ]]; then
  runbook_fail "emergency_hold_entry_ledger" "1" "${ENTRY_FOUND:-0}"
  exit 1
fi
runbook_pass "emergency_hold_entry_verified"

# Send EmergencyHoldExit signal after entry confirmed
EMERGENCY_EXIT_RESULT="$($PYTHON - <<PY
import asyncio
from sps.workflows.temporal import connect_client
from sps.workflows.permit_case.contracts import EmergencyHoldExitRequest, CaseState
from sps.workflows.permit_case.ids import permit_case_workflow_id

async def main():
    client = await connect_client()
    workflow_id = permit_case_workflow_id("${CASE_EMERGENCY_ID}")
    handle = client.get_workflow_handle(workflow_id)
    await handle.signal(
        "EmergencyHoldExit",
        EmergencyHoldExitRequest(target_state=CaseState.REVIEW_PENDING, reviewer_confirmation_id="${DECISION_VALID_ID}"),
    )
    return "ok"

print(asyncio.run(main()))
PY
)"

if [[ "$EMERGENCY_EXIT_RESULT" != "ok" ]]; then
  runbook_fail "emergency_hold_exit_signal" "ok" "$EMERGENCY_EXIT_RESULT"
  exit 1
fi

exit_attempt=0
LEDGER_EXIT_EVENT=""
while [[ $exit_attempt -lt 10 ]]; do
  LEDGER_EXIT_EVENT=$(docker compose exec -T postgres psql -U sps -d sps -t -A -c \
    "SELECT event_type FROM case_transition_ledger WHERE case_id='${CASE_EMERGENCY_ID}' AND to_state='REVIEW_PENDING' AND event_type='CASE_STATE_CHANGED' ORDER BY occurred_at DESC LIMIT 1")
  LEDGER_EXIT_EVENT=$(echo "$LEDGER_EXIT_EVENT" | tr -d '[:space:]')
  if [[ "$LEDGER_EXIT_EVENT" == "CASE_STATE_CHANGED" ]]; then
    break
  fi
  exit_attempt=$((exit_attempt + 1))
  sleep 1
done

if [[ "$LEDGER_EXIT_EVENT" != "CASE_STATE_CHANGED" ]]; then
  runbook_fail "emergency_hold_exit_ledger" "CASE_STATE_CHANGED" "${LEDGER_EXIT_EVENT:-missing}"
  exit 1
fi
runbook_pass "emergency_hold_exit_verified"

echo "" >&2
echo "======================================" >&2
echo "runbook.success: All assertions passed" >&2
echo "======================================" >&2
exit 0
