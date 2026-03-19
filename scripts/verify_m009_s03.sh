#!/usr/bin/env bash
# shellcheck shell=bash
set -euo pipefail

# M009 / S03 verification: rollback rehearsal evidence + post-release validation runbook.
#
# What this does:
#   1) Verifies the post-release validation runbook template exists
#   2) POST /api/v1/releases/rollbacks/rehearsals → assert 201
#   3) GET /api/v1/evidence/artifacts/{artifact_id} → assert 200

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUNBOOK_PATH="$ROOT_DIR/runbooks/sps/post-release-validation.md"
if [[ ! -f "$RUNBOOK_PATH" ]]; then
  echo "runbook.fail: missing_template path=$RUNBOOK_PATH" >&2
  exit 1
fi

echo "runbook: template_present path=$RUNBOOK_PATH" >&2

PYTHON="${PYTHON:-$ROOT_DIR/.venv/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  echo "runbook.fail: python_not_found path=$PYTHON" >&2
  exit 2
fi

API_HOST="${API_HOST:-localhost}"
API_PORT="${API_PORT:-8000}"
API_BASE="http://${API_HOST}:${API_PORT}"
SERVICE_PRINCIPAL_TOKEN="$($PYTHON - <<'PY'
from sps.auth.service_principal import mint_service_principal_jwt
print(mint_service_principal_jwt(subject="svc-m009-s03-runbook", roles=["release"]))
PY
)"
MTLS_HEADER_NAME="$($PYTHON - <<'PY'
from sps.config import get_settings
print(get_settings().auth_mtls_signal_header)
PY
)"
MTLS_HEADER_VALUE="${SPS_MTLS_HEADER_VALUE:-cert-present}"

RELEASE_ID="REL-M009-S03-$(date +%Y%m%d%H%M%S)-$$"
REHEARSAL_ID="REH-M009-S03-$(date +%Y%m%d%H%M%S)-$$"

REQUEST_BODY="$($PYTHON - <<PY
import json, hashlib
payload = {
    "status": "SUCCESS",
    "duration_seconds": 84,
    "rollback_version": "v2026.03.16",
    "validated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
}
canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
checksum = f"sha256:{hashlib.sha256(canonical).hexdigest()}"
body = {
    "release_id": "$RELEASE_ID",
    "rehearsal_id": "$REHEARSAL_ID",
    "environment": "staging",
    "operator_id": "ops-runbook",
    "authoritativeness": "INFORMATIONAL",
    "artifact_class": "ROLLBACK_REHEARSAL",
    "checksum": checksum,
    "evidence_payload": payload,
    "notes": "post-release verification",
}
print(json.dumps(body))
PY
)"

HTTP_RESPONSE_FILE="$(mktemp /tmp/m009_s03_rehearsal_XXXXXX)"
export HTTP_RESPONSE_FILE

if ! HTTP_STATUS="$(curl -sS -o "$HTTP_RESPONSE_FILE" -w "%{http_code}" \
  -X POST "${API_BASE}/api/v1/releases/rollbacks/rehearsals" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${SERVICE_PRINCIPAL_TOKEN}" \
  -H "${MTLS_HEADER_NAME}: ${MTLS_HEADER_VALUE}" \
  -d "$REQUEST_BODY")"; then
  echo "runbook.fail: curl_error action=create_rehearsal" >&2
  exit 1
fi

if [[ "$HTTP_STATUS" != "201" ]]; then
  echo "runbook.fail: create_rehearsal expected=201 actual=$HTTP_STATUS" >&2
  if [[ -f "$HTTP_RESPONSE_FILE" ]]; then
    echo "runbook.diagnostics: response_body" >&2
    cat "$HTTP_RESPONSE_FILE" >&2 || true
  fi
  exit 1
fi

echo "runbook: rehearsal_created" >&2

ARTIFACT_ID="$($PYTHON - <<PY
import json, sys
path = "${HTTP_RESPONSE_FILE}"
try:
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    print(payload.get("artifact_id", ""))
except Exception:
    print("")
PY
)"

if [[ -z "$ARTIFACT_ID" ]]; then
  echo "runbook.fail: missing_artifact_id" >&2
  if [[ -f "$HTTP_RESPONSE_FILE" ]]; then
    cat "$HTTP_RESPONSE_FILE" >&2 || true
  fi
  exit 1
fi

echo "runbook: artifact_id=$ARTIFACT_ID" >&2

HTTP_RESPONSE_FILE="$(mktemp /tmp/m009_s03_evidence_XXXXXX)"
export HTTP_RESPONSE_FILE

if ! GET_STATUS="$(curl -sS -o "$HTTP_RESPONSE_FILE" -w "%{http_code}" \
  "${API_BASE}/api/v1/evidence/artifacts/${ARTIFACT_ID}")"; then
  echo "runbook.fail: curl_error action=get_artifact" >&2
  exit 1
fi

if [[ "$GET_STATUS" != "200" ]]; then
  echo "runbook.fail: get_artifact expected=200 actual=$GET_STATUS" >&2
  if [[ -f "$HTTP_RESPONSE_FILE" ]]; then
    echo "runbook.diagnostics: response_body" >&2
    cat "$HTTP_RESPONSE_FILE" >&2 || true
  fi
  exit 1
fi

ARTIFACT_MATCH="$($PYTHON - <<PY
import json
path = "${HTTP_RESPONSE_FILE}"
with open(path, "r", encoding="utf-8") as fh:
    payload = json.load(fh)
print("ok" if payload.get("artifact_id") == "${ARTIFACT_ID}" else "mismatch")
PY
)"

if [[ "$ARTIFACT_MATCH" != "ok" ]]; then
  echo "runbook.fail: artifact_id_mismatch expected=${ARTIFACT_ID}" >&2
  cat "$HTTP_RESPONSE_FILE" >&2 || true
  exit 1
fi

echo "runbook.pass: evidence_artifact_ok artifact_id=$ARTIFACT_ID" >&2
