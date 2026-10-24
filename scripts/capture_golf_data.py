"""Read-only Dolphin observation capture and offline RAM comparison (no decoding)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from session_bootstrap import add_boot_options, ensure_intro

from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.observation_capture import capture, compare, parse_range, write_snapshot

DEFAULT_DIR = Path("research/game-data.local")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="operation", required=True)
    take = actions.add_parser("capture", help="read-only live RPC snapshot")
    take.add_argument("--label", required=True, help="e.g. green1-before")
    take.add_argument("--range", action="append", default=[], dest="ranges",
                      help="bounded window 0x80000000:4096, repeatable")
    take.add_argument("--out", type=Path, help="JSON path, must not already exist")
    take.add_argument("--port", type=int, default=55355)
    add_boot_options(take)
    take.add_argument("--wiimote", type=int, default=0)
    take.add_argument("--screenshot-file", type=Path,
                      help="existing manually captured frame; hash only")
    take.add_argument("--on-screen-distance", type=str,
                      help="raw human-readable number, NOT verified")
    take.add_argument("--on-screen-unit", type=str,
                      help="raw displayed unit such as yd/m/ft")
    take.add_argument("--shot-index", type=int)
    take.add_argument("--savestate-profile", type=str)
    take.add_argument("--scene-note", type=str)
    diff = actions.add_parser("compare", help="offline before/after RAM difference")
    diff.add_argument("--before", type=Path, required=True)
    diff.add_argument("--after", type=Path, required=True)
    diff.add_argument("--target", type=float,
                      help="human-read displayed number; unverified candidate search")
    diff.add_argument("--tolerance", type=float, default=0.1)
    diff.add_argument("--max-results", type=int, default=40)
    args = parser.parse_args()
    if args.operation == "capture":
        # Offline compare mode must never start or reset Dolphin.
        annotations = {k: v for k, v in {
            "on_screen_distance": args.on_screen_distance,
            "on_screen_unit": args.on_screen_unit,
            "shot_index": args.shot_index,
            "savestate_profile": args.savestate_profile,
            "scene_note": args.scene_note,
        }.items() if v is not None}
        target = args.out or DEFAULT_DIR / f"{args.label}.json"
        if target.exists():
            parser.error(f"refusing to overwrite evidence: {target}")
        ensure_intro(args)
        with FelkRPC(port=args.port) as rpc:
            snapshot = capture(rpc, args.label, [parse_range(r) for r in args.ranges],
                               wiimote_port=args.wiimote, annotations=annotations,
                               screenshot_path=args.screenshot_file)
        write_snapshot(snapshot, target)
        print(json.dumps({"saved": str(target), "label": snapshot["label"],
                          "frame_start": snapshot["frame_start"],
                          "frame_end": snapshot["frame_end"],
                          "memory_bytes": sum(s["length"] for s in snapshot["memory"]),
                          "controller": snapshot["controller"],
                          "warning": snapshot["source"]}, indent=2))
    else:
        before = json.loads(args.before.read_text(encoding="utf-8"))
        after = json.loads(args.after.read_text(encoding="utf-8"))
        report = compare(before, after, target=args.target,
                         tolerance=args.tolerance, max_results=args.max_results)
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
