#!/usr/bin/env bash
# Start local Temporal + Postgres development environment with readiness checks and migrations.
# Provisions docker-compose services, waits for Temporal + Postgres readiness, runs alembic migrations.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==> Starting docker-compose services..."
docker compose up -d

echo "==> Waiting for Postgres readiness..."
max_attempts=30
attempt=0
while ! docker compose exec -T postgres pg_isready -U postgres -q; do
  attempt=$((attempt + 1))
  if [ $attempt -ge $max_attempts ]; then
    echo "ERROR: Postgres not ready after $max_attempts attempts"
    docker compose logs postgres
    exit 1
  fi
  sleep 1
done
echo "Postgres is ready (attempt $attempt)"

echo "==> Waiting for Temporal readiness..."
max_attempts=30
attempt=0
while ! nc -z localhost 7233; do
  attempt=$((attempt + 1))
  if [ $attempt -ge $max_attempts ]; then
    echo "ERROR: Temporal not ready after $max_attempts attempts"
    docker compose logs temporal
    exit 1
  fi
  sleep 1
done
echo "Temporal is ready (attempt $attempt)"

echo "==> Running alembic migrations..."
export SPS_DB_DSN="postgresql+psycopg://sps:sps@localhost:5432/sps"

# Use .venv if available, otherwise assume alembic is in PATH
if [ -f "$PROJECT_ROOT/.venv/bin/alembic" ]; then
  "$PROJECT_ROOT/.venv/bin/alembic" upgrade head
else
  alembic upgrade head
fi

echo "==> Docker-compose environment ready"
echo "    Postgres: localhost:5432 (sps/sps)"
echo "    Temporal: localhost:7233"
echo "    Temporal UI: http://localhost:8080"
echo "    MinIO: localhost:9000 (console: localhost:9001)"

exit 0
