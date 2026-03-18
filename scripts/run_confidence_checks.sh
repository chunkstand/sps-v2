#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Missing .venv. Run scripts/bootstrap_dev.sh first." >&2
  exit 1
fi

export SPS_RUN_TEMPORAL_INTEGRATION="${SPS_RUN_TEMPORAL_INTEGRATION:-1}"
export SPS_RELEASE_BUNDLE_HTTP_MODE="${SPS_RELEASE_BUNDLE_HTTP_MODE:-asgi}"
export API_BASE="${API_BASE:-http://test}"

.venv/bin/python tools/verify_package_manifest.py --manifest PACKAGE-MANIFEST.json --root sps_full_spec_package

.venv/bin/pytest \
  tests/m006_s01_document_package_test.py \
  tests/m010_s04_readiness_test.py \
  tests/m012_s01_runtime_adapters_test.py \
  tests/s02_storage_adapter_test.py \
  tests/s02_evidence_roundtrip_test.py \
  tests/m009_s02_release_bundle_test.py

echo "Confidence checks complete."
