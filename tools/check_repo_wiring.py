#!/usr/bin/env python3
"""Check canonical repo wiring exists.

This is a *shape* check derived from spec section 30 (Repo Wiring) plus a few
additional package-critical files.

Goal: fail fast in CI if the canonical spec package isn't discoverable at the
expected paths.
"""

from __future__ import annotations

import argparse
import glob
from pathlib import Path

import yaml


REQUIRED_GLOBS: list[str] = [
    # spec + build plan
    "specs/sps/build-approved/spec.md",
    "specs/sps/build-approved/runtime-implementation-profile.md",
    "specs/sps/build-approved/plan.md",
    "specs/sps/build-approved/tasks.md",
    "specs/sps/build-approved/clarifications.md",
    "specs/sps/build-approved/intent.md",
    "specs/sps/build-approved/lineage.yaml",
    "specs/sps/build-approved/artifact-obligations.yaml",
    # model + contracts
    "model/sps/model.yaml",
    "model/sps/contracts/*.json",
    # invariants
    "invariants/sps/index.yaml",
    "invariants/sps/INV-*/invariant.yaml",
    "invariants/sps/guard-assertions.yaml",
    # traceability
    "traceability/sps/traceability.yaml",
    # runbooks + ops
    "runbooks/sps/*.md",
    "observability/sps/*.yaml",
    # release templates
    "releases/sps/templates/*",
    # governance templates
    "incidents/sps/*.yaml",
    "reviews/sps/*.yaml",
    "dissent/sps/*.yaml",
    "overrides/sps/*.yaml",
    "waivers/sps/*.yaml",
    # diagrams
    "diagrams/sps/*.mmd",
    # CI policy artifact
    "ci/sps/merge-authorization.yaml",
]


def _matches(root: Path, pattern: str) -> list[Path]:
    paths = [Path(p) for p in glob.glob(str(root / pattern))]
    return sorted([p for p in paths if p.exists()])


def _parse_yaml_file(path: Path) -> None:
    # ensure YAML is syntactically valid
    with path.open("r", encoding="utf-8") as f:
        yaml.safe_load(f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()

    root = Path(args.root).resolve()

    missing: list[str] = []
    yaml_files: list[Path] = []

    for pattern in REQUIRED_GLOBS:
        matches = _matches(root, pattern)
        if not matches:
            missing.append(pattern)
            continue

        for p in matches:
            if p.suffix in {".yaml", ".yml"}:
                yaml_files.append(p)

    yaml_errors: list[str] = []
    for p in sorted(set(yaml_files)):
        try:
            _parse_yaml_file(p)
        except Exception as e:  # noqa: BLE001
            yaml_errors.append(f"YAML parse failed: {p.relative_to(root)}: {e}")

    if missing or yaml_errors:
        print("Repo wiring check FAILED:\n")
        if missing:
            print("Missing required paths (glob patterns):")
            for m in missing:
                print(f"- {m}")
            print()
        if yaml_errors:
            print("YAML parse errors:")
            for e in yaml_errors:
                print(f"- {e}")
        return 1

    print("Repo wiring check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
