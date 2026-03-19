#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from sps.auth.service_principal import build_service_principal_headers
from sps.config import get_settings
from sps.services.release_bundle_manifest import (
    ReleaseBundleManifestError,
    build_release_bundle_components,
)


def _run_manifest_verifier(
    manifest_path: Path, root_dir: Path, *, repo_root: Path
) -> tuple[int, str]:
    cmd = [
        sys.executable,
        str(repo_root / "tools/verify_package_manifest.py"),
        "--manifest",
        str(manifest_path),
        "--root",
        str(root_dir),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output.strip()


def _parse_adapter_versions(values: list[str] | None, defaults: dict[str, str]) -> dict[str, str]:
    adapter_versions = dict(defaults)
    if not values:
        return adapter_versions
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid adapter version '{value}' (expected key=value)")
        key, version = value.split("=", 1)
        key = key.strip()
        version = version.strip()
        if not key or not version:
            raise ValueError(f"Invalid adapter version '{value}' (expected key=value)")
        adapter_versions[key] = version
    return adapter_versions


def _load_approvals(path: Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Approvals file must contain a JSON array")
    return payload


def _http_get_blockers(api_base: str, headers: dict[str, str], *, http_mode: str) -> dict[str, Any]:
    if http_mode == "asgi":
        import anyio
        import httpx
        from sps.api.main import app

        async def _fetch() -> dict[str, Any]:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url=api_base) as client:
                response = await client.get(
                    "/api/v1/ops/release-blockers",
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()

        return anyio.run(_fetch)

    from urllib import request

    req = request.Request(
        f"{api_base}/api/v1/ops/release-blockers",
        headers={"Content-Type": "application/json", **headers},
    )
    with request.urlopen(req, timeout=10) as response:  # nosec B310
        payload = json.loads(response.read().decode("utf-8"))
    return payload


def _http_post_bundle(
    api_base: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    *,
    http_mode: str,
) -> tuple[int, dict[str, Any] | None, str | None]:
    body = json.dumps(payload).encode("utf-8")

    if http_mode == "asgi":
        import anyio
        import httpx
        from sps.api.main import app

        async def _post() -> tuple[int, dict[str, Any] | None, str | None]:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url=api_base) as client:
                response = await client.post(
                    "/api/v1/releases/bundles",
                    headers=headers,
                    json=payload,
                )
                payload_json = None
                try:
                    payload_json = response.json()
                except ValueError:
                    payload_json = None
                return response.status_code, payload_json, response.text

        return anyio.run(_post)

    from urllib import request
    from urllib.error import HTTPError

    req = request.Request(
        f"{api_base}/api/v1/releases/bundles",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", **headers},
    )
    try:
        with request.urlopen(req, timeout=10) as response:  # nosec B310
            payload_json = json.loads(response.read().decode("utf-8"))
            return response.status, payload_json, None
    except HTTPError as exc:
        try:
            payload_json = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload_json = None
        return exc.code, payload_json, str(exc)


def _format_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for contradiction in payload.get("contradictions", []) or []:
        if isinstance(contradiction, dict):
            blockers.append(
                f"contradiction:{contradiction.get('contradiction_id')} scope={contradiction.get('scope')}"
            )
    for dissent in payload.get("dissents", []) or []:
        if isinstance(dissent, dict):
            blockers.append(f"dissent:{dissent.get('dissent_id')} scope={dissent.get('scope')}")
    return blockers


def _handle_failure(error_type: str, message: str, expect_failure: str | None) -> int:
    print(message, file=sys.stderr)
    if expect_failure:
        if expect_failure == error_type:
            print(f"release_bundle.expected_failure: {error_type}", file=sys.stderr)
            return 0
        print(
            f"release_bundle.unexpected_failure expected={expect_failure} actual={error_type}",
            file=sys.stderr,
        )
        return 2
    return 1


def run_release_bundle(args: argparse.Namespace) -> int:
    root_dir = Path(args.root).resolve()
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        resolved_from_cwd = manifest_path.resolve()
        if resolved_from_cwd.exists():
            manifest_path = resolved_from_cwd
        else:
            manifest_path = (root_dir / manifest_path).resolve()

    settings = get_settings()
    api_base = args.api_base
    repo_root = Path(__file__).resolve().parents[1]
    headers = build_service_principal_headers(
        roles=["ops", "release"],
        subject="svc-release-bundle-cli",
        bearer_token=args.bearer_token,
        mtls_header_name=args.mtls_header_name,
        mtls_header_value=args.mtls_header_value,
        settings=settings,
    )

    exit_code, verifier_output = _run_manifest_verifier(
        manifest_path, root_dir, repo_root=repo_root
    )
    if exit_code != 0:
        message = "release_bundle.manifest_invalid: PACKAGE-MANIFEST verification failed\n"
        if verifier_output:
            message += verifier_output
        return _handle_failure("manifest", message, args.expect_failure)

    try:
        approvals = _load_approvals(Path(args.approvals_file)) if args.approvals_file else []
        adapter_versions = _parse_adapter_versions(args.adapter_version, settings.adapter_versions)
        components = build_release_bundle_components(
            manifest_path=manifest_path,
            root_dir=root_dir,
            release_id=args.release_id,
            settings=settings,
            approvals=approvals,
            adapter_versions=adapter_versions,
            schema_path=repo_root / "model/sps/contracts/release-bundle-manifest.schema.json",
        )
    except (ReleaseBundleManifestError, ValueError) as exc:
        return _handle_failure(
            "manifest",
            f"release_bundle.manifest_invalid: {exc}",
            args.expect_failure,
        )

    if args.simulate_blockers:
        blockers_payload = {
            "blocker_count": 1,
            "contradictions": [{"contradiction_id": "SIMULATED-BLOCKER", "scope": "RELEASE"}],
            "dissents": [],
        }
    else:
        blockers_payload = _http_get_blockers(api_base, headers, http_mode=args.http_mode)
    if blockers_payload.get("blocker_count", 0) > 0:
        blocker_list = _format_blockers(blockers_payload)
        message_lines = [
            "release_bundle.blocked: open release blockers detected",
            f"blocker_count={blockers_payload.get('blocker_count')}",
        ]
        if blocker_list:
            message_lines.append("blockers=" + ", ".join(blocker_list))
        return _handle_failure("blockers", "\n".join(message_lines), args.expect_failure)

    if args.dry_run:
        print(json.dumps(components.manifest, indent=2, sort_keys=True))
        return 0

    payload = dict(components.manifest)
    payload.pop("created_at", None)
    payload["artifacts"] = components.artifacts

    status_code, response_payload, response_text = _http_post_bundle(
        api_base, headers, payload, http_mode=args.http_mode
    )
    if status_code != 201:
        message = (
            "release_bundle.post_failed: failed to persist bundle\n"
            f"status={status_code} response={response_payload or response_text}"
        )
        return _handle_failure("post", message, args.expect_failure)

    print(json.dumps(response_payload, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=(
            "Generate and submit SPS release bundle "
            "(service-principal JWT + mTLS)."
        )
    )
    ap.add_argument(
        "--manifest",
        default="sps_full_spec_package/PACKAGE-MANIFEST.json",
        help="Bundle manifest path (default: sps_full_spec_package/PACKAGE-MANIFEST.json)",
    )
    ap.add_argument(
        "--root",
        default="sps_full_spec_package",
        help="Bundle source root directory",
    )
    ap.add_argument("--release-id", required=True)
    ap.add_argument("--api-base", default=os.environ.get("API_BASE", "http://localhost:8000"))
    ap.add_argument("--bearer-token", default=os.environ.get("SPS_BEARER_TOKEN"))
    ap.add_argument(
        "--mtls-header-value",
        default=os.environ.get("SPS_MTLS_HEADER_VALUE", "cert-present"),
        help="Non-empty value for the configured mTLS signal header",
    )
    ap.add_argument(
        "--mtls-header-name",
        default=os.environ.get("SPS_MTLS_HEADER_NAME"),
        help="Override the header name used for the mTLS signal",
    )
    ap.add_argument("--approvals-file")
    ap.add_argument("--adapter-version", action="append", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--simulate-blockers", action="store_true")
    ap.add_argument(
        "--http-mode",
        choices=["urllib", "asgi"],
        default=os.environ.get("SPS_RELEASE_BUNDLE_HTTP_MODE", "urllib"),
    )
    ap.add_argument(
        "--expect-failure",
        choices=["manifest", "blockers", "post"],
        default=None,
    )
    return ap


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return run_release_bundle(args)


if __name__ == "__main__":
    raise SystemExit(main())
