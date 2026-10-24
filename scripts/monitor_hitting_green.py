"""Continuously log read-only golf scene positions; no Enter per shot.

Manual swings/game navigation remain human-controlled. Raw complete time series
stay locally; a small numerical report is published to GitHub by default.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.golf_monitor import run_monitor  # noqa: E402
from session_bootstrap import add_boot_options, ensure_intro  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=1.0,
                        help="target seconds between samples, default 1 (actual RPC rate can be slower)")
    parser.add_argument("--minutes", type=float, default=15.0,
                        help="automatically stop and upload after this many minutes; 0 means until Ctrl+C")
    parser.add_argument("--samples", type=int, default=0,
                        help="stop after N successful samples, 0 means no sample limit")
    parser.add_argument("--port", type=int, default=55355)
    add_boot_options(parser)
    parser.add_argument("--data-dir", type=Path,
                        default=ROOT.parent / "Wii-AI-Golf-Data" / "captures")
    parser.add_argument("--no-upload", action="store_true",
                        help="never publish results; record to local data folder only")
    args = parser.parse_args()
    ensure_intro(args)
    print("AUTOMATIC SCENE MONITOR (no per-shot Enter keys)")
    print("Tracks pin/start/cup positions, golf-mode/raw-hole changes and controller snapshots.")
    print("It does NOT know shot-contact, moving ball position, score or physical coordinate units.")
    print("Your manual shot/gameplay continues normally while it watches via Dolphin RPC.")
    if not args.no_upload:
        print("A compact NUMERICAL report will be uploaded to PUBLIC GitHub data branch at stop.")
    run_monitor(code_root=ROOT, local_dir=args.data_dir,
                interval_s=args.interval, max_minutes=args.minutes,
                max_samples=args.samples, port=args.port, upload=not args.no_upload)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Monitor error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
