#!/usr/bin/env bash
# shellcheck shell=bash
set -euo pipefail

# Postgres assertion helpers for runbook-style scripts.
#
# Design goals:
# - No credential echo (never print DSNs/passwords)
# - Safe, operator-friendly error messages
# - Works with the repo's docker-compose Postgres service by default
#
# Expected env (matches src/sps/config.py defaults):
#   SPS_DB_HOST (default: localhost)         # host where Postgres listens for the app
#   SPS_DB_PORT (default: 5432)
#   SPS_DB_NAME (default: sps)
#   SPS_DB_USER (default: sps)
#   SPS_DB_PASSWORD (default: sps)
#
# Optional (only relevant because we run psql *inside* the container):
#   SPS_DB_PORT_CONTAINER (default: 5432)
#
# Docker compose integration:
#   SPS_DOCKER_COMPOSE_SERVICE_POSTGRES (default: postgres)

_pg_die() {
  # Hard-exit: these helpers are intended for runbook scripts where any assertion
  # failure should terminate the run immediately.
  echo "postgres.assert.fail: $*" >&2
  exit 1
}

_pg_require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || _pg_die "missing_required_command cmd=$cmd"
}

pg_compose_service_postgres() {
  echo "${SPS_DOCKER_COMPOSE_SERVICE_POSTGRES:-postgres}"
}

pg_assert_no_single_quotes() {
  local value="$1"
  if [[ "$value" == *"'"* ]]; then
    _pg_die "unsafe_value_contains_single_quote"
  fi
}

pg_sql_quote() {
  # Defensive: keep quoting simple and safe for our canonical runbook values.
  # (If we ever need full escaping, switch to a python helper.)
  local value="$1"
  pg_assert_no_single_quotes "$value"
  printf "'%s'" "$value"
}

pg_exec() {
  # Execute SQL against the app DB using psql inside the docker-compose Postgres container.
  # Outputs raw stdout from psql.
  local sql="$1"

  _pg_require_cmd docker

  local svc
  svc="$(pg_compose_service_postgres)"

  # Do not echo password.
  local db_user="${SPS_DB_USER:-sps}"
  local db_name="${SPS_DB_NAME:-sps}"
  # This connection runs *inside* the container, so it should generally use the
  # container's Postgres port (5432) regardless of any host port mapping.
  local db_port="${SPS_DB_PORT_CONTAINER:-5432}"

  docker compose exec -T \
    -e "PGPASSWORD=${SPS_DB_PASSWORD:-sps}" \
    "$svc" \
    psql \
      -h 127.0.0.1 \
      -p "$db_port" \
      -U "$db_user" \
      -d "$db_name" \
      -v ON_ERROR_STOP=1 \
      -X \
      -q \
      -A \
      -t \
      -c "$sql"
}

pg_scalar() {
  # Run SQL and require exactly one non-empty line of output.
  local sql="$1"
  local label="${2:-scalar}"

  local out
  if ! out="$(pg_exec "$sql")"; then
    _pg_die "query_failed label=$label"
  fi

  # Trim trailing newline(s) from psql for stable comparisons.
  out="${out%$'\n'}"

  local lines
  lines="$(printf "%s" "$out" | awk 'END { print NR }')"
  if [[ "$lines" != "1" ]]; then
    _pg_die "expected_single_line_output label=$label lines=$lines"
  fi

  if [[ -z "$out" ]]; then
    _pg_die "expected_non_empty_output label=$label"
  fi

  printf "%s" "$out"
}

pg_assert_scalar_eq() {
  local sql="$1"
  local expected="$2"
  local label="$3"

  local actual
  actual="$(pg_scalar "$sql" "$label")" || return 1

  if [[ "$actual" != "$expected" ]]; then
    _pg_die "scalar_mismatch label=$label expected=$expected actual=$actual"
  fi
}

pg_assert_int_eq() {
  local sql="$1"
  local expected="$2"
  local label="$3"

  local actual
  actual="$(pg_scalar "$sql" "$label")" || return 1

  if ! [[ "$actual" =~ ^[0-9]+$ ]]; then
    _pg_die "expected_integer label=$label actual=$actual"
  fi

  if [[ "$actual" != "$expected" ]]; then
    _pg_die "count_mismatch label=$label expected=$expected actual=$actual"
  fi
}

pg_print() {
  local sql="$1"
  pg_exec "$sql"
}
