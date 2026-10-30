#!/usr/bin/env python3
"""Open local, read-only P0 JSONL replay; intentionally never launches Dolphin."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", default="", help="Local SHA-verified JSONL candidate events")
    parser.add_argument("--manifest", default="", help="Matching SHA-256 manifest")
    parser.add_argument("--terrain-obj", default="", help="Opt-in private OBJ to load on startup")
    args = parser.parse_args(argv)
    if bool(args.capture) != bool(args.manifest):
        parser.error("--capture and --manifest must be supplied together")
    from wii_ai_golf.inspector.gui import launch
    try:
        return launch(args.capture, args.manifest, args.terrain_obj)
    except (OSError, RuntimeError) as exc:
        print(f"Offline inspector could not start: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
