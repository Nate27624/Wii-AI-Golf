#!/usr/bin/env python3
"""Read-only local diagnostics for Issue #431 source-94 tree startup.

No coordinates, ROM bytes, textures, or file contents are printed or copied.
Use: py -3 -I scripts/diagnose_inspector_tree_loading.py
"""
from __future__ import annotations

from pathlib import Path
import sys

CHECKOUT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CHECKOUT / "src"))

from wii_ai_golf.inspector.asset_preferences import (
    SavedAssetError, inspect_private_trees, load_asset_selections, local_settings_path,
)
from wii_ai_golf.inspector.tree_positions import (
    TreePositionsError, load_private_tree_positions,
)


def main() -> int:
    print("=== PRIVATE 94-TREE INSPECTOR STARTUP DIAGNOSTICS (READ ONLY) ===")
    print("Checkout:", CHECKOUT)
    print("Settings path:", local_settings_path())
    try:
        saved = load_asset_selections()
    except (SavedAssetError, OSError) as exc:
        print("Settings rejected:", type(exc).__name__, str(exc))
        return 0
    print("Auto-discovery enabled:", saved.auto_find_trees)
    print("Saved tree path:", saved.tree_json or "(none)")
    if saved.tree_json:
        try:
            data = load_private_tree_positions(saved.tree_json)
        except (TreePositionsError, OSError, ValueError) as exc:
            print("Saved tree validation: REJECTED:", type(exc).__name__, str(exc))
        else:
            print("Saved tree validation: PASS; count:", len(data.positions))
        print("A saved tree path takes priority over discovery, even when rejected.")
    elif not saved.auto_find_trees:
        print("Auto-discovery disabled (Clear trees was used). Re-select one file in the inspector.")
    else:
        found, examined = inspect_private_trees(CHECKOUT)
        for candidate, verdict in examined:
            print("Candidate:", candidate, "=>", verdict)
        print("Discovery:", "PASS" if found is not None else "NOT LOADED")
    print("Note: loaded trees only RENDER once source-qualified replay/live data is available.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
