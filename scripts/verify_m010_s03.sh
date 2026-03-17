#!/usr/bin/env bash
# shellcheck shell=bash
set -euo pipefail

# M010 / S03 verification: read-only observability + redacted logs.
#
# What this does:
#   1) Generates a service-principal JWT + mTLS header
#   2) GET /api/v1/ops/dashboard/metrics → assert 200
#   3) GET /api/v1/ops/release-blockers → assert 200
#   4) POST /api/v1/ops/dashboard/metrics → assert 405 (read-only)
#   5) Emit redacted log output (Authorization + reviewer_api_key masked)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-$ROOT_DIR/.venv/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  echo "runbook.fail: python_not_found path=$PYTHON" >&2
  exit 2
fi

API_HOST="${API_HOST:-localhost}"
API_PORT="${API_PORT:-8000}"
API_BASE="http://${API_HOST}:${API_PORT}"
MTLS_HEADER="${SPS_AUTH_MTLS_SIGNAL_HEADER:-X-Forwarded-Client-Cert}"

TOKEN="$($PYTHON - <<PY
from tests.helpers.auth_tokens import build_service_principal_jwt

print(build_service_principal_jwt(subject="svc-ops", roles=["ops"]))
PY
)"

if [[ -z "$TOKEN" ]]; then
  echo "runbook.fail: token_generation_failed" >&2
  exit 1
fi

echo "runbook: service_principal_ready mtls_header=$MTLS_HEADER" >&2

HTTP_RESPONSE_FILE="$(mktemp /tmp/m010_s03_ops_metrics_XXXXXX)"
export HTTP_RESPONSE_FILE
if ! METRICS_STATUS="$(curl -sS -o "$HTTP_RESPONSE_FILE" -w "%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "${MTLS_HEADER}: present" \
  "${API_BASE}/api/v1/ops/dashboard/metrics")"; then
  echo "runbook.fail: curl_error action=get_ops_metrics" >&2
  exit 1
fi

if [[ "$METRICS_STATUS" != "200" ]]; then
  echo "runbook.fail: get_ops_metrics expected=200 actual=$METRICS_STATUS" >&2
  if [[ -f "$HTTP_RESPONSE_FILE" ]]; then
    echo "runbook.diagnostics: response_body" >&2
    cat "$HTTP_RESPONSE_FILE" >&2 || true
  fi
  exit 1
fi

echo "runbook: ops_metrics_ok" >&2

HTTP_RESPONSE_FILE="$(mktemp /tmp/m010_s03_release_blockers_XXXXXX)"
export HTTP_RESPONSE_FILE
if ! BLOCKERS_STATUS="$(curl -sS -o "$HTTP_RESPONSE_FILE" -w "%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "${MTLS_HEADER}: present" \
  "${API_BASE}/api/v1/ops/release-blockers")"; then
  echo "runbook.fail: curl_error action=get_release_blockers" >&2
  exit 1
fi

if [[ "$BLOCKERS_STATUS" != "200" ]]; then
  echo "runbook.fail: get_release_blockers expected=200 actual=$BLOCKERS_STATUS" >&2
  if [[ -f "$HTTP_RESPONSE_FILE" ]]; then
    echo "runbook.diagnostics: response_body" >&2
    cat "$HTTP_RESPONSE_FILE" >&2 || true
  fi
  exit 1
fi

echo "runbook: release_blockers_ok" >&2

HTTP_RESPONSE_FILE="$(mktemp /tmp/m010_s03_ops_mutation_XXXXXX)"
export HTTP_RESPONSE_FILE
if ! MUTATION_STATUS="$(curl -sS -o "$HTTP_RESPONSE_FILE" -w "%{http_code}" \
  -X POST "${API_BASE}/api/v1/ops/dashboard/metrics" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "${MTLS_HEADER}: present")"; then
  echo "runbook.fail: curl_error action=ops_mutation_attempt" >&2
  exit 1
fi

if [[ "$MUTATION_STATUS" != "405" ]]; then
  echo "runbook.fail: ops_mutation_expected=405 actual=$MUTATION_STATUS" >&2
  if [[ -f "$HTTP_RESPONSE_FILE" ]]; then
    echo "runbook.diagnostics: response_body" >&2
    cat "$HTTP_RESPONSE_FILE" >&2 || true
  fi
  exit 1
fi

echo "runbook: ops_mutation_rejected status=$MUTATION_STATUS" >&2

REDACTION_LOG="$($PYTHON - <<PY
import logging
import sys

from sps.logging.redaction import attach_redaction_filter

logging.basicConfig(
    level="INFO",
    format="%(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
attach_redaction_filter()
logger = logging.getLogger("runbook.redaction")
logger.info(
    "runbook.redaction_check authorization=Bearer %s reviewer_api_key=%s",
    "${TOKEN}",
    "legacy-reviewer-key",
)
PY
)"

if echo "$REDACTION_LOG" | grep -Fq "$TOKEN"; then
  echo "runbook.fail: redaction_missing token_visible" >&2
  exit 1
fi

if ! echo "$REDACTION_LOG" | grep -Fq "[REDACTED]"; then
  echo "runbook.fail: redaction_missing redacted_marker_absent" >&2
  exit 1
fi

echo "$REDACTION_LOG" >&2
echo "runbook.pass: redaction_confirmed" >&2
