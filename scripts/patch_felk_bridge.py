"""Local-only generator for an experimental atomic-input Felk bridge patch."""
import argparse
from pathlib import Path

from wii_ai_golf.integration.atomic_patch import patch_bridge, git_blob_sha
from wii_ai_golf.integration.savestates import StateCatalog


def main() -> None:
    parser = argparse.ArgumentParser(description="Patch a pinned upstream mcp_bridge.py; retains its MIT licensing")
    parser.add_argument("--source", type=Path, required=True, help="Source mcp_bridge.py obtained from upstream")
    parser.add_argument("--output", type=Path, required=True, help="A separate output path; never overwrites input")
    choices = parser.add_mutually_exclusive_group()
    choices.add_argument("--startup-slot", type=int, default=None,
                         help="Optional slot 0..99 to auto-load once after first emulated frame")
    choices.add_argument("--startup-profile", default=None,
                         help="Named state from local catalog; preferred over hardcoded slot")
    parser.add_argument("--catalog", type=Path,
                        default=Path(__file__).resolve().parents[1] / "research" / "savestates.local.json")
    parser.add_argument("--startup-slot", type=int, default=None, help="Optional savestate slot (0..255) to restore once on first emulated frame")
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error("Output must not overwrite the original bridge")
    source = args.source.read_text(encoding="utf-8")
    selected_slot = args.startup_slot
    if args.startup_profile is not None:
        selected_slot = StateCatalog(args.catalog).get(args.startup_profile).slot
    new = patch_bridge(source, startup_slot=selected_slot)
    args.output.write_text(new, encoding="utf-8")
    print(f"Wrote EXPERIMENTAL bridge at {args.output}; original blob SHA {git_blob_sha(source)}")
    if args.startup_slot is not None:
        print(f"Startup will request savestate slot {args.startup_slot} once after first frame; ensure slot exists.")
    print("This patch requires validation in Felk Dolphin; NO gameplay success is implied.")
    if selected_slot is not None:
        print(f"Startup AUTO-LOAD REQUEST configured for slot {selected_slot}; requires existing compatible state.")


if __name__ == "__main__":
    main()
