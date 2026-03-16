from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from sps.config import Settings


@dataclass(frozen=True)
class PackageManifestEntry:
    path: str
    sha256: str
    bytes: int


@dataclass(frozen=True)
class ReleaseBundleComponents:
    manifest: dict[str, Any]
    artifacts: list[dict[str, str]]


class ReleaseBundleManifestError(ValueError):
    pass


def load_package_manifest(manifest_path: Path) -> list[PackageManifestEntry]:
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ReleaseBundleManifestError("PACKAGE-MANIFEST.json must be a JSON array")

    entries: list[PackageManifestEntry] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ReleaseBundleManifestError(f"Manifest entry {idx} must be an object")
        try:
            entries.append(
                PackageManifestEntry(
                    path=str(item["path"]),
                    sha256=str(item["sha256"]),
                    bytes=int(item["bytes"]),
                )
            )
        except KeyError as exc:
            raise ReleaseBundleManifestError(
                f"Manifest entry {idx} missing key: {exc}"
            ) from exc
    return entries


def _extract_frontmatter(text: str) -> dict[str, Any] | None:
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    if len(lines) < 3:
        return None
    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return None
    payload = "\n".join(lines[1:end_idx])
    try:
        data = yaml.safe_load(payload)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def _extract_artifact_id_from_json(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for key in ("x-artifact-metadata", "artifact_metadata"):
            meta = payload.get(key)
            if isinstance(meta, dict):
                artifact_id = meta.get("artifact_id")
                if isinstance(artifact_id, str) and artifact_id.strip():
                    return artifact_id.strip()
        artifact_id = payload.get("artifact_id")
        if isinstance(artifact_id, str) and artifact_id.strip():
            return artifact_id.strip()
    return None


def extract_artifact_id(path: Path) -> str | None:
    suffix = path.suffix.lower()
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None

    if suffix == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None
        return _extract_artifact_id_from_json(payload)

    frontmatter = _extract_frontmatter(text)
    if frontmatter:
        artifact_id = frontmatter.get("artifact_id")
        if isinstance(artifact_id, str) and artifact_id.strip():
            return artifact_id.strip()
        meta = frontmatter.get("artifact_metadata")
        if isinstance(meta, dict):
            artifact_id = meta.get("artifact_id")
            if isinstance(artifact_id, str) and artifact_id.strip():
                return artifact_id.strip()

    if suffix in {".yaml", ".yml"}:
        try:
            payload = yaml.safe_load(text)
        except yaml.YAMLError:
            payload = None
        if isinstance(payload, dict):
            artifact_id = payload.get("artifact_id")
            if isinstance(artifact_id, str) and artifact_id.strip():
                return artifact_id.strip()
            meta = payload.get("artifact_metadata")
            if isinstance(meta, dict):
                artifact_id = meta.get("artifact_id")
                if isinstance(artifact_id, str) and artifact_id.strip():
                    return artifact_id.strip()

    match = re.search(r"^artifact_id:\s*([A-Za-z0-9\-_.]+)", text, re.MULTILINE)
    if match:
        return match.group(1)
    return None


def _validate_against_schema(data: dict[str, Any], schema: dict[str, Any]) -> None:
    required = schema.get("required", [])
    if not isinstance(required, list):
        raise ReleaseBundleManifestError("Schema missing required fields")

    missing = [field for field in required if field not in data]
    if missing:
        raise ReleaseBundleManifestError(
            f"Release manifest missing required fields: {', '.join(sorted(missing))}"
        )

    if schema.get("additionalProperties") is False:
        allowed = set(schema.get("properties", {}).keys())
        extra = [key for key in data.keys() if key not in allowed]
        if extra:
            raise ReleaseBundleManifestError(
                f"Release manifest has unexpected fields: {', '.join(sorted(extra))}"
            )

    type_checks = {
        "string": str,
        "object": dict,
        "array": list,
    }
    properties = schema.get("properties", {})
    for key, prop in properties.items():
        if key not in data:
            continue
        expected_type = prop.get("type")
        if expected_type in type_checks and not isinstance(data[key], type_checks[expected_type]):
            raise ReleaseBundleManifestError(
                f"Release manifest field {key} expected {expected_type}"
            )


def build_release_bundle_components(
    *,
    manifest_path: Path,
    root_dir: Path,
    release_id: str,
    settings: Settings,
    approvals: list[dict[str, Any]] | None = None,
    adapter_versions: dict[str, str] | None = None,
    now: dt.datetime | None = None,
    schema_path: Path | None = None,
) -> ReleaseBundleComponents:
    entries = load_package_manifest(manifest_path)
    approvals = approvals or []
    adapter_versions = adapter_versions or settings.adapter_versions
    created_at = (now or dt.datetime.now(tz=dt.UTC)).isoformat().replace("+00:00", "Z")

    artifact_digests: dict[str, str] = {}
    artifacts: list[dict[str, str]] = []
    seen_artifacts: set[str] = set()

    for entry in entries:
        path = (root_dir / entry.path).resolve()
        if not path.exists():
            continue
        artifact_id = extract_artifact_id(path)
        if not artifact_id:
            continue
        if artifact_id in seen_artifacts:
            raise ReleaseBundleManifestError(f"Duplicate artifact_id detected: {artifact_id}")
        seen_artifacts.add(artifact_id)
        artifact_digests[artifact_id] = entry.sha256
        artifacts.append(
            {
                "artifact_id": artifact_id,
                "checksum": entry.sha256,
                "storage_uri": f"file://{path}",
            }
        )

    manifest = {
        "release_id": release_id,
        "spec_version": settings.spec_version,
        "app_version": settings.app_version,
        "schema_version": settings.schema_version,
        "model_version": settings.model_version,
        "policy_bundle_version": settings.policy_bundle_version,
        "adapter_versions": adapter_versions,
        "invariant_pack_version": settings.invariant_pack_version,
        "artifact_digests": artifact_digests,
        "approvals": approvals,
        "created_at": created_at,
    }

    schema_path = schema_path or root_dir / "model/sps/contracts/release-bundle-manifest.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        raise ReleaseBundleManifestError("Release bundle manifest schema must be a JSON object")
    _validate_against_schema(manifest, schema)

    return ReleaseBundleComponents(manifest=manifest, artifacts=artifacts)
