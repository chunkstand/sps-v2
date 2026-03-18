#!/usr/bin/env python3
"""Verify PACKAGE-MANIFEST.json matches on-disk files.

This is used to validate the legacy bundle source consumed by SPS release-bundle
generation. By default it verifies only the files listed in the manifest
(it does NOT fail on extra files).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ManifestEntry:
    path: str
    sha256: str
    bytes: int


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_manifest(manifest_path: Path) -> list[ManifestEntry]:
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Manifest must be a JSON array")

    out: list[ManifestEntry] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"Manifest entry {i} must be an object")
        try:
            out.append(
                ManifestEntry(
                    path=str(item["path"]),
                    sha256=str(item["sha256"]),
                    bytes=int(item["bytes"]),
                )
            )
        except KeyError as e:
            raise ValueError(f"Manifest entry {i} missing key: {e}") from e
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="PACKAGE-MANIFEST.json")
    ap.add_argument("--root", default="sps_full_spec_package")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    manifest_path = (root / args.manifest).resolve()

    if not manifest_path.exists():
        raise SystemExit(f"ERROR: manifest not found: {manifest_path}")

    entries = _load_manifest(manifest_path)

    errors: list[str] = []
    seen_paths: set[str] = set()

    for e in entries:
        if e.path in seen_paths:
            errors.append(f"Duplicate manifest path: {e.path}")
            continue
        seen_paths.add(e.path)

        p = root / e.path
        if not p.exists():
            errors.append(f"Missing file: {e.path}")
            continue
        if not p.is_file():
            errors.append(f"Not a file: {e.path}")
            continue

        actual_bytes = p.stat().st_size
        if actual_bytes != e.bytes:
            errors.append(f"Size mismatch: {e.path} expected={e.bytes} actual={actual_bytes}")

        actual_sha = _sha256_file(p)
        if actual_sha.lower() != e.sha256.lower():
            errors.append(f"SHA mismatch: {e.path} expected={e.sha256} actual={actual_sha}")

    if errors:
        print("PACKAGE-MANIFEST verification FAILED:\n")
        for err in errors:
            print(f"- {err}")
        return 1

    print(f"PACKAGE-MANIFEST verification OK ({len(entries)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
