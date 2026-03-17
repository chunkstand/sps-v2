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
export SPS_AUTH_JWT_ISSUER="${SPS_AUTH_JWT_ISSUER:-sps.local}"
export SPS_AUTH_JWT_AUDIENCE="${SPS_AUTH_JWT_AUDIENCE:-sps.api}"
export SPS_AUTH_JWT_SECRET="${SPS_AUTH_JWT_SECRET:-dev-secret}"
export SPS_AUTH_JWT_ALGORITHM="${SPS_AUTH_JWT_ALGORITHM:-HS256}"

WORKER_PID=""
API_PID=""

# shellcheck source=./scripts/lib/assert_postgres.sh
source "$ROOT_DIR/scripts/lib/assert_postgres.sh"

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

ADMIN_TOKEN="$($PYTHON - <<'PY'
from tests.helpers.auth_tokens import build_jwt
print(build_jwt(subject="admin-runbook", roles=["admin"]))
PY
)"
REVIEWER_TOKEN="$($PYTHON - <<'PY'
from tests.helpers.auth_tokens import build_jwt
print(build_jwt(subject="reviewer-runbook", roles=["reviewer"]))
PY
)"

if [[ -z "$ADMIN_TOKEN" || -z "$REVIEWER_TOKEN" ]]; then
  runbook_fail "token_generation" "non_empty_tokens" "missing"
  exit 1
fi

PORTAL_INTENT_ID="INTENT-PSM-RUNBOOK"
PORTAL_REVIEW_ID="REVIEW-PSM-RUNBOOK"
PORTAL_FAMILY="PACIFIC_GAS"
PORTAL_SUPPORT_LEVEL="FULL"

SOURCE_RULE_INTENT_ID="INTENT-SR-RUNBOOK"
SOURCE_RULE_REVIEW_ID="REVIEW-SR-RUNBOOK"
SOURCE_RULE_SCOPE="REQUIREMENTS_RANKING"

INCENTIVE_INTENT_ID="INTENT-IP-RUNBOOK"
INCENTIVE_REVIEW_ID="REVIEW-IP-RUNBOOK"
INCENTIVE_PROGRAM_KEY="FEDERAL_SOLAR_CREDIT"

runbook_step 3 "Resetting prior runbook rows"
pg_exec "DELETE FROM admin_portal_support_reviews WHERE review_id IN ($(pg_sql_quote "$PORTAL_REVIEW_ID"));" >/dev/null
pg_exec "DELETE FROM admin_portal_support_intents WHERE intent_id IN ($(pg_sql_quote "$PORTAL_INTENT_ID"));" >/dev/null
pg_exec "DELETE FROM portal_support_metadata WHERE portal_family IN ($(pg_sql_quote "$PORTAL_FAMILY"));" >/dev/null

pg_exec "DELETE FROM admin_source_rule_reviews WHERE review_id IN ($(pg_sql_quote "$SOURCE_RULE_REVIEW_ID"));" >/dev/null
pg_exec "DELETE FROM admin_source_rule_intents WHERE intent_id IN ($(pg_sql_quote "$SOURCE_RULE_INTENT_ID"));" >/dev/null
pg_exec "DELETE FROM source_rules WHERE rule_scope IN ($(pg_sql_quote "$SOURCE_RULE_SCOPE"));" >/dev/null

pg_exec "DELETE FROM admin_incentive_program_reviews WHERE review_id IN ($(pg_sql_quote "$INCENTIVE_REVIEW_ID"));" >/dev/null
pg_exec "DELETE FROM admin_incentive_program_intents WHERE intent_id IN ($(pg_sql_quote "$INCENTIVE_INTENT_ID"));" >/dev/null
pg_exec "DELETE FROM incentive_programs WHERE program_key IN ($(pg_sql_quote "$INCENTIVE_PROGRAM_KEY"));" >/dev/null

pg_exec "DELETE FROM audit_events WHERE correlation_id IN ($(pg_sql_quote "$PORTAL_INTENT_ID"), $(pg_sql_quote "$SOURCE_RULE_INTENT_ID"), $(pg_sql_quote "$INCENTIVE_INTENT_ID"));" >/dev/null
runbook_pass "cleanup_complete"

runbook_step 4 "Portal support intent → review → apply"
PORTAL_INTENT_RESPONSE_FILE="$(mktemp /tmp/m013_s02_portal_intent_XXXXXX)"
PORTAL_INTENT_STATUS=$(curl -sS -o "$PORTAL_INTENT_RESPONSE_FILE" -w "%{http_code}" \
  -X POST "${API_BASE}/api/v1/admin/portal-support/intents" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\
    \"intent_id\": \"${PORTAL_INTENT_ID}\",\
    \"portal_family\": \"${PORTAL_FAMILY}\",\
    \"requested_support_level\": \"${PORTAL_SUPPORT_LEVEL}\",\
    \"intent_payload\": {\"support_tier\": \"full\", \"notes\": \"runbook\"},\
    \"requested_by\": \"admin-runbook\"\
  }")
if [[ "$PORTAL_INTENT_STATUS" != "201" ]]; then
  runbook_fail "portal_support_intent" "201" "$PORTAL_INTENT_STATUS"
  cat "$PORTAL_INTENT_RESPONSE_FILE" >&2
  exit 1
fi
runbook_pass "portal_support_intent_created"

PORTAL_REVIEW_RESPONSE_FILE="$(mktemp /tmp/m013_s02_portal_review_XXXXXX)"
PORTAL_REVIEW_STATUS=$(curl -sS -o "$PORTAL_REVIEW_RESPONSE_FILE" -w "%{http_code}" \
  -X POST "${API_BASE}/api/v1/admin/portal-support/reviews" \
  -H "Authorization: Bearer ${REVIEWER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\
    \"review_id\": \"${PORTAL_REVIEW_ID}\",\
    \"intent_id\": \"${PORTAL_INTENT_ID}\",\
    \"reviewer_id\": \"reviewer-runbook\",\
    \"decision_outcome\": \"APPROVED\",\
    \"review_payload\": {\"notes\": \"approved\"},\
    \"idempotency_key\": \"IDEMPOTENCY-PSM-RUNBOOK\"\
  }")
if [[ "$PORTAL_REVIEW_STATUS" != "201" ]]; then
  runbook_fail "portal_support_review" "201" "$PORTAL_REVIEW_STATUS"
  cat "$PORTAL_REVIEW_RESPONSE_FILE" >&2
  exit 1
fi
runbook_pass "portal_support_review_recorded"

PORTAL_APPLY_RESPONSE_FILE="$(mktemp /tmp/m013_s02_portal_apply_XXXXXX)"
PORTAL_APPLY_STATUS=$(curl -sS -o "$PORTAL_APPLY_RESPONSE_FILE" -w "%{http_code}" \
  -X POST "${API_BASE}/api/v1/admin/portal-support/apply/${PORTAL_INTENT_ID}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}")
if [[ "$PORTAL_APPLY_STATUS" != "200" ]]; then
  runbook_fail "portal_support_apply" "200" "$PORTAL_APPLY_STATUS"
  cat "$PORTAL_APPLY_RESPONSE_FILE" >&2
  exit 1
fi
PORTAL_METADATA_ID="$($PYTHON - <<PY
import json
with open("$PORTAL_APPLY_RESPONSE_FILE") as fp:
    payload = json.load(fp)
print(payload.get("portal_support_metadata_id", ""))
PY
)"
if [[ -z "$PORTAL_METADATA_ID" ]]; then
  runbook_fail "portal_support_apply_response" "portal_support_metadata_id" "missing"
  exit 1
fi
runbook_pass "portal_support_applied"

pg_assert_int_eq "SELECT COUNT(*) FROM portal_support_metadata WHERE portal_family=$(pg_sql_quote "$PORTAL_FAMILY") AND support_level=$(pg_sql_quote "$PORTAL_SUPPORT_LEVEL");" "1" "portal_support_metadata_present"
pg_assert_int_eq "SELECT COUNT(*) FROM audit_events WHERE correlation_id=$(pg_sql_quote "$PORTAL_INTENT_ID") AND action='ADMIN_PORTAL_SUPPORT_INTENT_CREATED';" "1" "portal_support_audit_intent"
pg_assert_int_eq "SELECT COUNT(*) FROM audit_events WHERE correlation_id=$(pg_sql_quote "$PORTAL_INTENT_ID") AND action='ADMIN_PORTAL_SUPPORT_REVIEW_RECORDED';" "1" "portal_support_audit_review"
pg_assert_int_eq "SELECT COUNT(*) FROM audit_events WHERE correlation_id=$(pg_sql_quote "$PORTAL_INTENT_ID") AND action='ADMIN_PORTAL_SUPPORT_APPLIED';" "1" "portal_support_audit_applied"
runbook_pass "portal_support_audit_verified"

runbook_step 5 "Source rule intent → review → apply"
SOURCE_INTENT_RESPONSE_FILE="$(mktemp /tmp/m013_s02_source_intent_XXXXXX)"
SOURCE_INTENT_STATUS=$(curl -sS -o "$SOURCE_INTENT_RESPONSE_FILE" -w "%{http_code}" \
  -X POST "${API_BASE}/api/v1/admin/source-rules/intents" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\
    \"intent_id\": \"${SOURCE_RULE_INTENT_ID}\",\
    \"rule_scope\": \"${SOURCE_RULE_SCOPE}\",\
    \"rule_payload\": {\"priority\": [\"utility\", \"state\", \"county\"]},\
    \"requested_by\": \"admin-runbook\"\
  }")
if [[ "$SOURCE_INTENT_STATUS" != "201" ]]; then
  runbook_fail "source_rule_intent" "201" "$SOURCE_INTENT_STATUS"
  cat "$SOURCE_INTENT_RESPONSE_FILE" >&2
  exit 1
fi
runbook_pass "source_rule_intent_created"

SOURCE_REVIEW_RESPONSE_FILE="$(mktemp /tmp/m013_s02_source_review_XXXXXX)"
SOURCE_REVIEW_STATUS=$(curl -sS -o "$SOURCE_REVIEW_RESPONSE_FILE" -w "%{http_code}" \
  -X POST "${API_BASE}/api/v1/admin/source-rules/reviews" \
  -H "Authorization: Bearer ${REVIEWER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\
    \"review_id\": \"${SOURCE_RULE_REVIEW_ID}\",\
    \"intent_id\": \"${SOURCE_RULE_INTENT_ID}\",\
    \"reviewer_id\": \"reviewer-runbook\",\
    \"decision_outcome\": \"APPROVED\",\
    \"review_payload\": {\"notes\": \"approved\"},\
    \"idempotency_key\": \"IDEMPOTENCY-SR-RUNBOOK\"\
  }")
if [[ "$SOURCE_REVIEW_STATUS" != "201" ]]; then
  runbook_fail "source_rule_review" "201" "$SOURCE_REVIEW_STATUS"
  cat "$SOURCE_REVIEW_RESPONSE_FILE" >&2
  exit 1
fi
runbook_pass "source_rule_review_recorded"

SOURCE_APPLY_RESPONSE_FILE="$(mktemp /tmp/m013_s02_source_apply_XXXXXX)"
SOURCE_APPLY_STATUS=$(curl -sS -o "$SOURCE_APPLY_RESPONSE_FILE" -w "%{http_code}" \
  -X POST "${API_BASE}/api/v1/admin/source-rules/apply/${SOURCE_RULE_INTENT_ID}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}")
if [[ "$SOURCE_APPLY_STATUS" != "200" ]]; then
  runbook_fail "source_rule_apply" "200" "$SOURCE_APPLY_STATUS"
  cat "$SOURCE_APPLY_RESPONSE_FILE" >&2
  exit 1
fi
SOURCE_RULE_ID="$($PYTHON - <<PY
import json
with open("$SOURCE_APPLY_RESPONSE_FILE") as fp:
    payload = json.load(fp)
print(payload.get("source_rule_id", ""))
PY
)"
if [[ -z "$SOURCE_RULE_ID" ]]; then
  runbook_fail "source_rule_apply_response" "source_rule_id" "missing"
  exit 1
fi
runbook_pass "source_rule_applied"

pg_assert_int_eq "SELECT COUNT(*) FROM source_rules WHERE rule_scope=$(pg_sql_quote "$SOURCE_RULE_SCOPE");" "1" "source_rule_row_present"
pg_assert_int_eq "SELECT COUNT(*) FROM audit_events WHERE correlation_id=$(pg_sql_quote "$SOURCE_RULE_INTENT_ID") AND action='ADMIN_SOURCE_RULE_INTENT_CREATED';" "1" "source_rule_audit_intent"
pg_assert_int_eq "SELECT COUNT(*) FROM audit_events WHERE correlation_id=$(pg_sql_quote "$SOURCE_RULE_INTENT_ID") AND action='ADMIN_SOURCE_RULE_REVIEW_RECORDED';" "1" "source_rule_audit_review"
pg_assert_int_eq "SELECT COUNT(*) FROM audit_events WHERE correlation_id=$(pg_sql_quote "$SOURCE_RULE_INTENT_ID") AND action='ADMIN_SOURCE_RULE_APPLIED';" "1" "source_rule_audit_applied"
runbook_pass "source_rule_audit_verified"

runbook_step 6 "Incentive program intent → review → apply"
INCENTIVE_INTENT_RESPONSE_FILE="$(mktemp /tmp/m013_s02_incentive_intent_XXXXXX)"
INCENTIVE_INTENT_STATUS=$(curl -sS -o "$INCENTIVE_INTENT_RESPONSE_FILE" -w "%{http_code}" \
  -X POST "${API_BASE}/api/v1/admin/incentive-programs/intents" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\
    \"intent_id\": \"${INCENTIVE_INTENT_ID}\",\
    \"program_key\": \"${INCENTIVE_PROGRAM_KEY}\",\
    \"program_payload\": {\"eligibility\": \"residential\", \"value_usd\": 7500},\
    \"requested_by\": \"admin-runbook\"\
  }")
if [[ "$INCENTIVE_INTENT_STATUS" != "201" ]]; then
  runbook_fail "incentive_program_intent" "201" "$INCENTIVE_INTENT_STATUS"
  cat "$INCENTIVE_INTENT_RESPONSE_FILE" >&2
  exit 1
fi
runbook_pass "incentive_program_intent_created"

INCENTIVE_REVIEW_RESPONSE_FILE="$(mktemp /tmp/m013_s02_incentive_review_XXXXXX)"
INCENTIVE_REVIEW_STATUS=$(curl -sS -o "$INCENTIVE_REVIEW_RESPONSE_FILE" -w "%{http_code}" \
  -X POST "${API_BASE}/api/v1/admin/incentive-programs/reviews" \
  -H "Authorization: Bearer ${REVIEWER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\
    \"review_id\": \"${INCENTIVE_REVIEW_ID}\",\
    \"intent_id\": \"${INCENTIVE_INTENT_ID}\",\
    \"reviewer_id\": \"reviewer-runbook\",\
    \"decision_outcome\": \"APPROVED\",\
    \"review_payload\": {\"notes\": \"approved\"},\
    \"idempotency_key\": \"IDEMPOTENCY-IP-RUNBOOK\"\
  }")
if [[ "$INCENTIVE_REVIEW_STATUS" != "201" ]]; then
  runbook_fail "incentive_program_review" "201" "$INCENTIVE_REVIEW_STATUS"
  cat "$INCENTIVE_REVIEW_RESPONSE_FILE" >&2
  exit 1
fi
runbook_pass "incentive_program_review_recorded"

INCENTIVE_APPLY_RESPONSE_FILE="$(mktemp /tmp/m013_s02_incentive_apply_XXXXXX)"
INCENTIVE_APPLY_STATUS=$(curl -sS -o "$INCENTIVE_APPLY_RESPONSE_FILE" -w "%{http_code}" \
  -X POST "${API_BASE}/api/v1/admin/incentive-programs/apply/${INCENTIVE_INTENT_ID}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}")
if [[ "$INCENTIVE_APPLY_STATUS" != "200" ]]; then
  runbook_fail "incentive_program_apply" "200" "$INCENTIVE_APPLY_STATUS"
  cat "$INCENTIVE_APPLY_RESPONSE_FILE" >&2
  exit 1
fi
INCENTIVE_PROGRAM_ID="$($PYTHON - <<PY
import json
with open("$INCENTIVE_APPLY_RESPONSE_FILE") as fp:
    payload = json.load(fp)
print(payload.get("incentive_program_id", ""))
PY
)"
if [[ -z "$INCENTIVE_PROGRAM_ID" ]]; then
  runbook_fail "incentive_program_apply_response" "incentive_program_id" "missing"
  exit 1
fi
runbook_pass "incentive_program_applied"

pg_assert_int_eq "SELECT COUNT(*) FROM incentive_programs WHERE program_key=$(pg_sql_quote "$INCENTIVE_PROGRAM_KEY");" "1" "incentive_program_row_present"
pg_assert_int_eq "SELECT COUNT(*) FROM audit_events WHERE correlation_id=$(pg_sql_quote "$INCENTIVE_INTENT_ID") AND action='ADMIN_INCENTIVE_PROGRAM_INTENT_CREATED';" "1" "incentive_program_audit_intent"
pg_assert_int_eq "SELECT COUNT(*) FROM audit_events WHERE correlation_id=$(pg_sql_quote "$INCENTIVE_INTENT_ID") AND action='ADMIN_INCENTIVE_PROGRAM_REVIEW_RECORDED';" "1" "incentive_program_audit_review"
pg_assert_int_eq "SELECT COUNT(*) FROM audit_events WHERE correlation_id=$(pg_sql_quote "$INCENTIVE_INTENT_ID") AND action='ADMIN_INCENTIVE_PROGRAM_APPLIED';" "1" "incentive_program_audit_applied"
runbook_pass "incentive_program_audit_verified"

echo "" >&2
echo "======================================" >&2
echo "runbook.success: All assertions passed" >&2
echo "======================================" >&2
exit 0
