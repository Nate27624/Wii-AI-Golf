#!/usr/bin/env python3
"""Validate and remember an existing local source-94 PRIVATE JSON for inspector.

No original RAM or tree coordinates are printed or committed. Does not run
Dolphin. Source/schema verification uses the inspector's strict loader.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.inspector.asset_preferences import (
    SavedAssetError, load_asset_selections, remember_asset, save_asset_selections,
)
from wii_ai_golf.inspector.tree_positions import (
    TreePositionsError, load_private_tree_positions,
)


def register(filename: Path) -> tuple[str, int]:
    source = load_private_tree_positions(filename)
    state = remember_asset(load_asset_selections(), "tree_json", filename)
    save_asset_selections(state)
    return "PRIVATE_TREE_JSON_REGISTERED", len(source.positions)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        state, count = register(args.file)
    except (TreePositionsError, SavedAssetError, ValueError, OSError) as exc:
        print("PRIVATE_TREE_JSON_REGISTRATION_FAILED:", type(exc).__name__, str(exc))
        return 2
    print(f"{state} count={count}; next inspector launch will load the file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
