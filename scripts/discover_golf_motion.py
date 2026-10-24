"""Unattended source-gated Wii golf RAM differential sampler.

Move and swing manually while running. No Enter prompts. Saves full raw hex
LOCALLY; optional public upload is ONLY a compact ranked-candidate summary.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.ball_discovery import snapshot_windows, analyze_samples  # noqa: E402
from wii_ai_golf.golf_collection import make_run_id, publish_sanitized  # noqa: E402
from wii_ai_golf.integration.rpc import FelkRPC  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=45, help="5..180; Ctrl+C stops early")
    parser.add_argument("--interval", type=float, default=0.6, help="0.2..10 seconds; RPC may be slower")
    parser.add_argument("--port", type=int, default=55355)
    parser.add_argument("--data-dir", type=Path,
                        default=ROOT.parent / "Wii-AI-Golf-Data" / "captures")
    parser.add_argument("--no-upload", action="store_true", help="local only; no GitHub publication")
    args = parser.parse_args()
    if not 5 <= args.seconds <= 180:
        parser.error("--seconds must be between 5 and 180")
    if not 0.2 <= args.interval <= 10:
        parser.error("--interval must be between 0.2 and 10")
    args.data_dir.mkdir(parents=True, exist_ok=True)
    run = make_run_id()
    local = args.data_dir / f"golf-motion-{run}.jsonl"
    captured, errors = [], []
    start = time.monotonic()
    print("Read-only candidate motion scan — Wii Sports Hitting the Green (US Rev1).")
    print("Swing/play manually. No Enter. Ctrl+C stops early and preserves data.")
    print("No verified ball position, shot counter, result or wind field yet.")
    print("Raw game memory stays LOCAL; only candidate numbers can be uploaded.")
    print(f"Private output: {local}")
    with local.open("x", encoding="utf-8") as out:
        try:
            while time.monotonic() - start < args.seconds:
                tick = time.monotonic()
                try:
                    with FelkRPC(port=args.port, timeout_s=15) as rpc:
                        snapshot = snapshot_windows(rpc)
                    if not snapshot["windows"]:
                        raise RuntimeError("no valid golf windows (verify mode/bridge)")
                    row = {"elapsed_s": round(tick - start, 3), **snapshot}
                    out.write(json.dumps(row, sort_keys=True) + "\n")
                    out.flush()
                    captured.append(row)
                    print(f"  {len(captured)} samples | {snapshot['read_bytes']} bytes/sample | "
                          f"{time.monotonic()-start:.1f}s", end="\r", flush=True)
                except (OSError, RuntimeError, ValueError, KeyError) as exc:
                    errors.append({"elapsed_s": round(tick - start, 3),
                                   "error_type": type(exc).__name__})
                    print(f"\nRead-only error: {type(exc).__name__}")
                    if len(errors) >= 5 and not captured:
                        break
                pause = max(0.0, args.interval - (time.monotonic() - tick))
                if pause:
                    time.sleep(pause)
        except KeyboardInterrupt:
            print("\nCtrl+C: stopping capture.")
    print(f"\nFinished {len(captured)} samples.")
    summary = analyze_samples(captured)
    report = {"run_id": run, "schema_version": 1,
              "study_id": "S002-HG-MOTION-DISCOVERY",
              "source": "live-bounded-golf-memory-heuristic-not-verified",
              "captured_utc": datetime.now(timezone.utc).isoformat(),
              "samples": len(captured), "read_errors": errors[-10:],
              "position_candidates": summary,
              "warning": "Not a decoded ball, score, wind or shot counter. Raw memory local only."}
    summary_file = args.data_dir / f"golf-motion-{run}-summary.json"
    with summary_file.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(f"Candidates ranked: {summary['candidate_count']}; summary: {summary_file}")
    if not args.no_upload and captured:
        try:
            url = publish_sanitized(report, ROOT)
            print(f"Numerical candidate report on GitHub: {url}")
        except (OSError, RuntimeError) as exc:
            print(f"GitHub upload failed ({type(exc).__name__}); report remains local.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Discovery error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
