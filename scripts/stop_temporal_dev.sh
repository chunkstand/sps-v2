#!/usr/bin/env bash
# shellcheck shell=bash
set -euo pipefail

# Manual cleanup helper for stopping the docker-compose Temporal development environment.
# Removes all volumes for fresh state on next start.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==> Stopping docker-compose services and removing volumes..." >&2
docker compose down -v

echo "==> Docker-compose environment cleaned up" >&2
exit 0
