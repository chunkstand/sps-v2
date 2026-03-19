from __future__ import annotations

from pathlib import Path


def test_env_gated_tests_are_explicitly_marked_integration() -> None:
    tests_root = Path(__file__).resolve().parent
    missing_markers: list[str] = []

    for path in sorted(tests_root.rglob("*.py")):
        text = path.read_text()
        if "SPS_RUN_TEMPORAL_INTEGRATION" not in text:
            continue
        if "pytestmark = pytest.mark.integration" in text:
            continue
        if "@pytest.mark.integration" in text:
            continue
        missing_markers.append(path.relative_to(tests_root.parent).as_posix())

    assert not missing_markers, (
        "Env-gated DB/Temporal tests must declare integration coverage explicitly: "
        + ", ".join(missing_markers)
    )
