"""OFFLINE ONLY: four native plain 24MiB Wii MEM1 checkpoint image comparison.

Only after S001 verified a safe native memory-dump route in the operator's
actual Felk fork. Never use 24MiB per-byte Felk RPC, never put whole RAM in
GitHub/ChatGPT, and never confuse Dolphin savestates with raw memory dumps.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.audit.mem1_checkpoint_diff import analyze_private_mem1_files


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--private-root", type=Path, required=True,
                    help="Existing local ignored folder containing private plain MEM1 images")
    ap.add_argument("--b0", type=Path, required=True,
                    help="Native plain MEM1 image, first-ball stationary")
    ap.add_argument("--b1", type=Path, required=True,
                    help="Native plain MEM1 image, later stationary")
    ap.add_argument("--b2", type=Path, required=True,
                    help="Native plain MEM1 image, manual WASD pointer only")
    ap.add_argument("--b3", type=Path, required=True,
                    help="Native plain MEM1 image, later idle")
    ap.add_argument("--output", type=Path, required=True,
                    help="New, never overwritten local sanitized JSON at private root")
    ap.add_argument("--max-pages", type=int, default=24,
                    help="Number of aggregate 4KiB relative pages to retain, 1..24")
    args = ap.parse_args(argv)
    try:
        result = analyze_private_mem1_files(
            [args.b0, args.b1, args.b2, args.b3],
            private_root=args.private_root, output=args.output,
            max_pages=args.max_pages)
    except (OSError, ValueError, TypeError, KeyError) as error:
        # Do not include exception text: paths may reveal private user folders.
        print("MEM1 offline comparison stopped: " + type(error).__name__ +
              " (inspect local provenance/format/bounds; no upload)", file=sys.stderr)
        return 1
    print("MEM1 offline comparison complete: local sanitized counts only.")
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
