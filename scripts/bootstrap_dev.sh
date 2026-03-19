#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

uv sync --extra dev --frozen

echo "Bootstrap complete. Activate with: source .venv/bin/activate"
