#!/usr/bin/env python3
"""Refresh the authoritative spec-package manifest and manage the root mirror.

The authoritative package lives under ``sps_full_spec_package/``. The repo root
retains a convenience mirror of the package contents, excluding the root
``README.md`` explainer and the authoritative manifest file itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path


EXCLUDED_ROOT_MIRROR_PATHS = {"README.md", "PACKAGE-MANIFEST.json"}


@dataclass(frozen=True)
class ManifestEntry:
    path: str
    sha256: str
    bytes: int


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_authoritative_files(authoritative_root: Path) -> list[Path]:
    return sorted(
        path
        for path in authoritative_root.rglob("*")
        if path.is_file()
        and path.relative_to(authoritative_root).as_posix() not in EXCLUDED_ROOT_MIRROR_PATHS
    )


def _build_manifest(authoritative_root: Path) -> list[ManifestEntry]:
    entries: list[ManifestEntry] = []
    for path in _iter_authoritative_files(authoritative_root):
        rel_path = path.relative_to(authoritative_root).as_posix()
        entries.append(
            ManifestEntry(
                path=rel_path,
                sha256=_sha256_file(path),
                bytes=path.stat().st_size,
            )
        )
    return entries


def _write_manifest(authoritative_root: Path) -> None:
    manifest_path = authoritative_root / "PACKAGE-MANIFEST.json"
    payload = [
        {"path": entry.path, "sha256": entry.sha256, "bytes": entry.bytes}
        for entry in _build_manifest(authoritative_root)
    ]
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _remove_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
        return
    path.unlink()


def _copy_path(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _sync_root_mirror(authoritative_root: Path, repo_root: Path) -> None:
    for src in _iter_authoritative_files(authoritative_root):
        rel_path = src.relative_to(authoritative_root)
        dst = repo_root / rel_path
        _copy_path(src, dst)
    _remove_path(repo_root / "PACKAGE-MANIFEST.json")


def _compare_file(rel_path: Path, src: Path, dst: Path) -> str | None:
    if not dst.exists():
        return f"missing:{rel_path.as_posix()}"
    if src.is_dir() != dst.is_dir():
        return f"type_mismatch:{rel_path.as_posix()}"
    if src.read_bytes() != dst.read_bytes():
        return f"content_mismatch:{rel_path.as_posix()}"
    return None


def _check_root_mirror(authoritative_root: Path, repo_root: Path) -> list[str]:
    errors: list[str] = []
    for src in _iter_authoritative_files(authoritative_root):
        rel_path = src.relative_to(authoritative_root)
        mismatch = _compare_file(rel_path, src, repo_root / rel_path)
        if mismatch:
            errors.append(mismatch)
    if (repo_root / "PACKAGE-MANIFEST.json").exists():
        errors.append("unexpected_repo_root_manifest:PACKAGE-MANIFEST.json")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authoritative-root", default="sps_full_spec_package")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--sync-root-mirror", action="store_true")
    parser.add_argument("--check-root-mirror", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    authoritative_root = (repo_root / args.authoritative_root).resolve()

    if not authoritative_root.exists():
        raise SystemExit(f"ERROR: authoritative root not found: {authoritative_root}")

    _write_manifest(authoritative_root)

    if args.sync_root_mirror:
        _sync_root_mirror(authoritative_root, repo_root)

    if args.check_root_mirror:
        errors = _check_root_mirror(authoritative_root, repo_root)
        if errors:
            print("Spec package mirror check FAILED:\n")
            for error in errors:
                print(f"- {error}")
            return 1
        print("Spec package mirror check OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
