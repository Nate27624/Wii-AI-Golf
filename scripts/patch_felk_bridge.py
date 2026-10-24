"""Local-only generator for an experimental atomic-input Felk bridge patch."""
import argparse
import os
import shutil
from pathlib import Path

import sys

# Resolve the canonical source checkout BEFORE importing wii_ai_golf.
# Editable pip installs may point at a different Git worktree.
# This also works with Python -I (isolated mode) and from any CWD.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_LOCAL_SRC = str(_REPO_ROOT / "src")
if _LOCAL_SRC in sys.path:
    sys.path.remove(_LOCAL_SRC)
sys.path.insert(0, _LOCAL_SRC)

from wii_ai_golf.integration.atomic_patch import patch_bridge, git_blob_sha
from wii_ai_golf.integration.savestates import StateCatalog
from wii_ai_golf.integration.swing_patch import extend_atomic_bridge_with_swing


def main() -> None:
    parser = argparse.ArgumentParser(description="Patch a pinned upstream mcp_bridge.py; retains its MIT licensing")
    parser.add_argument("--source", type=Path, required=True, help="Source mcp_bridge.py obtained from upstream")
    parser.add_argument("--output", type=Path, required=True, help="A separate output path; never overwrites input")
    choices = parser.add_mutually_exclusive_group()
    choices.add_argument("--startup-slot", type=int, default=None,
                         help="Optional slot 0..99 to auto-load once after first emulated frame")
    choices.add_argument("--startup-profile", default=None,
                         help="Named state from local catalog; preferred over hardcoded slot")
    parser.add_argument("--enable-swing", action="store_true",
                        help="Opt in to Felk Preview 4 dedicated swing input tracing")
    parser.add_argument("--catalog", type=Path,
                        default=Path(__file__).resolve().parents[1] / "research" / "savestates.local.json")
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error("Output must not overwrite the original bridge")
    source = args.source.read_text(encoding="utf-8")
    selected_slot = args.startup_slot
    if args.startup_profile is not None:
        selected_slot = StateCatalog(args.catalog).get(args.startup_profile).slot
    new = patch_bridge(source, startup_slot=selected_slot)
    if args.enable_swing:
        new = extend_atomic_bridge_with_swing(new)
    # Source is SHA pinned; output is a disposable generated script. Preserve
    # the FIRST previously deployed bridge when upgrading from V1 to V2.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    backup = args.output.with_name(args.output.name + ".before-neutral-v2.bak")
    if args.enable_swing and args.output.is_file() and not backup.exists():
        shutil.copy2(args.output, backup)
        print(f"Saved first existing generated bridge backup: {backup}")
    temp = args.output.with_name(args.output.name + ".tmp")
    try:
        temp.write_text(new, encoding="utf-8")
        os.replace(temp, args.output)
    finally:
        if temp.exists():
            temp.unlink()
    print(f"Wrote EXPERIMENTAL bridge at {args.output}; original blob SHA {git_blob_sha(source)}")
    print("This patch requires validation in Felk Dolphin; NO gameplay success is implied.")
    if args.enable_swing:
        print("Preview 4 swing protocol V2 ENABLED: neutral swing samples dispatch buttons only.")
        print("Game recognition and contact still require human verification.")
    if selected_slot is not None:
        print(f"Startup AUTO-LOAD REQUEST configured for slot {selected_slot}; requires existing compatible state.")


if __name__ == "__main__":
    main()
