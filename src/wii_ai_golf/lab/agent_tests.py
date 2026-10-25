"""Discover merged Python unittest files without requiring manual registry edits.

A discovered test is runnable ONLY from the local checked-out source tree.
No scanning/sourcing arbitrary branch, PR JSON, or network response.
"""
from __future__ import annotations

from pathlib import Path
import re

TEST_NAME = re.compile(r"test_[a-z0-9_]+\.py\Z")
ID_PREFIX = "agent-tests."


def owner_for_file(filename: str) -> str:
    """Best-effort owner label; ownership is NOT an authority grant."""
    name = filename.lower()
    if name.startswith(("test_integration_", "test_menu_", "test_golf_experiment_",
                        "test_audit_local_swing_", "test_protocol_")):
        return "S001"
    if name.startswith(("test_outcome_", "test_audit_motion_", "test_evaluation_",
                        "test_focused_", "test_golf_ram_")):
        return "S002"
    if name.startswith(("test_model_", "test_calibration_", "test_swing_model_")):
        return "S003"
    if name.startswith(("test_learning_", "test_policy_", "test_bayes_")):
        return "S004"
    if name.startswith(("test_generalization_", "test_holdout_")):
        return "S005"
    return "S000"


def discover_agent_tests(root: Path) -> list[dict[str, str]]:
    folder = root / "tests"
    if not folder.is_dir():
        return []
    results: list[dict[str, str]] = []
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.is_symlink() or not TEST_NAME.fullmatch(path.name):
            continue
        stem = path.stem
        results.append({
            "id": ID_PREFIX + stem,
            "owner": owner_for_file(path.name),
            "title": path.name,
            "description": ("Committed offline unittest file at tests/" + path.name +
                            "; agent ownership inferred from filename. "
                            "Python tests can run code; use only trusted merged main."),
            "mode": "offline",
            "kind": "test_file",
        })
    return results


def combined_catalog(root: Path, static_entries: list[dict[str, str]]) -> list[dict[str, str]]:
    discovered = discover_agent_tests(root)
    ids = {x["id"] for x in static_entries}
    if any(x["id"] in ids for x in discovered):
        raise ValueError("Registered experiment collides with discovered test filename")
    return [*static_entries, *discovered]


def validated_test_filename(identifier: str, root: Path) -> str:
    if not identifier.startswith(ID_PREFIX):
        raise ValueError("Not an agent test ID")
    stem = identifier[len(ID_PREFIX):]
    filename = stem + ".py"
    if not TEST_NAME.fullmatch(filename):
        raise ValueError("Invalid agent test filename")
    path = root / "tests" / filename
    if not path.is_file() or path.is_symlink() or path.resolve().parent != (root / "tests").resolve():
        raise ValueError("Agent test not found in checked-out tests/ folder")
    return filename
