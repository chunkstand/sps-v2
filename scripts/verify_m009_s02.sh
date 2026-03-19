#!/usr/bin/env bash
# shellcheck shell=bash
set -euo pipefail

if [[ "${1:-}" == "--failure-paths" ]]; then
  shift
fi

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
raise SystemExit(1)
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

_make_good_manifest() {
  "$PYTHON" - <<'PY'
import hashlib
import json
from pathlib import Path

root = Path(".").resolve()
artifact = root / "artifact.yaml"
artifact.write_text("""---\nartifact_metadata:\n  artifact_id: ART-RUNBOOK-001\n---\nname: runbook\n""", encoding="utf-8")
content = artifact.read_bytes()
sha = hashlib.sha256(content).hexdigest()
manifest = [
    {"path": artifact.name, "sha256": sha, "bytes": len(content)},
]
manifest_path = root / "PACKAGE-MANIFEST.json"
manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
PY
}

_make_bad_manifest() {
  "$PYTHON" - <<'PY'
import json
from pathlib import Path

root = Path(".").resolve()
artifact = root / "artifact.yaml"
artifact.write_text("""---\nartifact_metadata:\n  artifact_id: ART-RUNBOOK-001\n---\nname: runbook\n""", encoding="utf-8")
content = artifact.read_bytes()
manifest = [
    {"path": artifact.name, "sha256": "0" * 64, "bytes": len(content)},
]
manifest_path = root / "PACKAGE-MANIFEST.json"
manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
PY
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
# Phase 2: Migrations + cleanup
# ---------------------------------------------------------------------------

echo "runbook: applying_migrations" >&2
"$ALEMBIC" upgrade head >/dev/null

pg_exec "TRUNCATE TABLE release_artifacts, release_bundles, dissent_artifacts, review_decisions, contradiction_artifacts, permit_cases CASCADE" >/dev/null

# ---------------------------------------------------------------------------
# Phase 3: Start FastAPI server
# ---------------------------------------------------------------------------

mkdir -p "$ROOT_DIR/artifacts/runbook"
API_LOG="$ROOT_DIR/artifacts/runbook/m009_s02_api_${RUNBOOK_TS}_$$.log"

echo "runbook: starting_api log=$API_LOG port=$API_PORT" >&2
"$PYTHON" -m uvicorn sps.api.main:app --host 0.0.0.0 --port "$API_PORT" >"$API_LOG" 2>&1 &
API_PID=$!

_wait_for_api_ready 30

echo "runbook: api_ready pid=$API_PID" >&2

# ---------------------------------------------------------------------------
# Phase 4: CLI success path
# ---------------------------------------------------------------------------

echo "runbook: generating_release_bundle" >&2

GOOD_MANIFEST_DIR="$(mktemp -d /tmp/m009_s02_manifest_ok_XXXXXX)"
mkdir -p "$GOOD_MANIFEST_DIR/sps_full_spec_package"
pushd "$GOOD_MANIFEST_DIR/sps_full_spec_package" >/dev/null
_make_good_manifest

"$PYTHON" "$ROOT_DIR/scripts/generate_release_bundle.py" \
  --manifest "$GOOD_MANIFEST_DIR/sps_full_spec_package/PACKAGE-MANIFEST.json" \
  --root "$GOOD_MANIFEST_DIR/sps_full_spec_package" \
  --release-id "RUNBOOK-REL-001" \
  --api-base "$API_BASE" \
  --reviewer-api-key "$REVIEWER_API_KEY" >/dev/null

popd >/dev/null

pg_assert_int_eq \
  "select count(*) from release_bundles where release_id=$(pg_sql_quote "RUNBOOK-REL-001")" \
  "1" \
  "release_bundles.created"

# ---------------------------------------------------------------------------
# Phase 5: Manifest mismatch failure path
# ---------------------------------------------------------------------------

echo "runbook: manifest_mismatch_failure" >&2

MANIFEST_TMP_DIR="$(mktemp -d /tmp/m009_s02_manifest_XXXXXX)"
mkdir -p "$MANIFEST_TMP_DIR/sps_full_spec_package"
pushd "$MANIFEST_TMP_DIR/sps_full_spec_package" >/dev/null
_make_bad_manifest

if "$PYTHON" "$ROOT_DIR/scripts/generate_release_bundle.py" \
  --manifest "$MANIFEST_TMP_DIR/sps_full_spec_package/PACKAGE-MANIFEST.json" \
  --root "$MANIFEST_TMP_DIR/sps_full_spec_package" \
  --release-id "RUNBOOK-REL-BAD" \
  --api-base "$API_BASE" \
  --reviewer-api-key "$REVIEWER_API_KEY" >/dev/null 2>"$MANIFEST_TMP_DIR/error.log"; then
  echo "runbook.fail: expected_manifest_mismatch" >&2
  cat "$MANIFEST_TMP_DIR/error.log" >&2 || true
  exit 1
fi
popd >/dev/null

# ---------------------------------------------------------------------------
# Phase 6: Blocker failure path
# ---------------------------------------------------------------------------

echo "runbook: blocker_failure" >&2

CASE_ID="RUNBOOK-BLOCK-001"
DECISION_ID="RUNBOOK-DEC-001"

pg_exec "insert into permit_cases (case_id, tenant_id, project_id, case_state, review_state, submission_mode, portal_support_level, current_release_profile, legal_hold) values ($(pg_sql_quote "$CASE_ID"), 'tenant-runbook', $(pg_sql_quote "project-${CASE_ID}"), 'REVIEW_PENDING', 'PENDING', 'DIGITAL', 'FULL', 'default', false) on conflict (case_id) do nothing" >/dev/null
pg_exec "insert into review_decisions (decision_id, schema_version, case_id, object_type, object_id, decision_outcome, reviewer_id, subject_author_id, reviewer_independence_status, evidence_ids, contradiction_resolution, dissent_flag, notes, decision_at, idempotency_key) values ($(pg_sql_quote "$DECISION_ID"), '1.0', $(pg_sql_quote "$CASE_ID"), 'permit_case', $(pg_sql_quote "$CASE_ID"), 'ACCEPT_WITH_DISSENT', 'reviewer-block', 'author-block', 'INDEPENDENT', '{}', null, true, null, (now() - interval '1 day'), 'runbook/${DECISION_ID}') on conflict (decision_id) do nothing" >/dev/null
pg_exec "insert into dissent_artifacts (dissent_id, linked_review_id, case_id, scope, rationale, required_followup, resolution_state, created_at) values ('DISSENT-RUNBOOK-001', $(pg_sql_quote "$DECISION_ID"), $(pg_sql_quote "$CASE_ID"), 'PERMIT/HIGH_RISK', 'rationale', null, 'OPEN', now()) on conflict (dissent_id) do nothing" >/dev/null
pg_exec "insert into contradiction_artifacts (contradiction_id, case_id, scope, source_a, source_b, ranking_relation, blocking_effect, resolution_status, created_at) values ('CONTRA-RUNBOOK-001', $(pg_sql_quote "$CASE_ID"), 'RELEASE', 'source-a', 'source-b', 'SAME_RANK', true, 'OPEN', now()) on conflict (contradiction_id) do nothing" >/dev/null

if "$PYTHON" "$ROOT_DIR/scripts/generate_release_bundle.py" \
  --manifest "$GOOD_MANIFEST_DIR/sps_full_spec_package/PACKAGE-MANIFEST.json" \
  --root "$GOOD_MANIFEST_DIR/sps_full_spec_package" \
  --release-id "RUNBOOK-REL-BLOCK" \
  --api-base "$API_BASE" \
  --reviewer-api-key "$REVIEWER_API_KEY" >/dev/null 2>"/tmp/m009_s02_blocker_error_$$.log"; then
  echo "runbook.fail: expected_blocker_failure" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Phase 7: Summary
# ---------------------------------------------------------------------------

echo "runbook: release_bundle_summary" >&2
pg_print "select release_id, created_at from release_bundles order by created_at desc" >&2

echo "runbook: ok" >&2
