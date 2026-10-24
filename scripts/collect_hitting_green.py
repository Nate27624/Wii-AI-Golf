"""Walk through Hitting the Green manually and publish sanitized results to GitHub.

Only read-only Dolphin RPC is automated. You make each swing by hand.
Uses canonical code repo for scripts, sibling Wii-AI-Golf-Data for local results.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
# Always use source from THIS checkout, not a stale editable installation from a
# second worktree (a previously observed source/test mismatch).
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.golf_collection import collect, session_steps  # noqa: E402
from session_bootstrap import add_boot_options, ensure_intro  # noqa: E402

DATA = ROOT.parent / "Wii-AI-Golf-Data" / "captures"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-shot", type=int, default=1,
                        help="first Hitting the Green shot (1..10, ignored by --plan)")
    parser.add_argument("--shots", type=int, default=10,
                        help="number of shots/plan attempts to collect, max 10")
    parser.add_argument("--plan", type=Path, help="optional observed scenario plan created by scripts/plan_scenarios.py")
    parser.add_argument("--port", type=int, default=55355)
    add_boot_options(parser)
    parser.add_argument("--data-dir", type=Path, default=DATA,
                        help="private local JSON files; NEVER committed by this tool")
    parser.add_argument("--no-upload", action="store_true",
                        help="save observations locally only; default automatically git-pushes compact report")
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8")) if args.plan else None
    steps = session_steps(start_shot=args.start_shot, shots=args.shots, plan=plan)
    ensure_intro(args)
    print("HITTING THE GREEN — MANUAL SHOT COLLECTION")
    print("This script never swings or writes RAM. Startup loaded the named state and navigated menus.")
    print(f"Prepare to manually perform up to {len(steps)} shot(s).")
    print(f"Local evidence: {args.data_dir}")
    if not args.no_upload:
        print("At the end, a compact report (coordinates, frame counters, human score)")
        print("will be pushed to a PUBLIC GitHub data branch in Nate27624/Wii-AI-Golf.")
        print("NO raw memory dumps, screenshots, savestates, ROMs or local paths are uploaded.")
        print("GitHub authentication via the existing 'git' origin is required.")
    local, public = collect(steps=steps, port=args.port, data_dir=args.data_dir,
                            code_root=ROOT, upload=not args.no_upload)
    if local is not None:
        print(f"Local report: {local}")
    if public:
        print(f"Share this URL back in ChatGPT for review: {public}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, RuntimeError, KeyError) as exc:
        print(f"Collector error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
