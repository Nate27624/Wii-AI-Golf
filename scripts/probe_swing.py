"""Human-observed, single-shot S001 Felk swing primitive experiment.

Does NOT score shots or run unattended optimization. Requires an up-to-date
--enable-swing patched bridge and Emulated Wii Remote 1, Extension None.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.integration.savestates import StateCatalog, StateManager
from wii_ai_golf.integration.swing_client import SwingSample, SwingTraceClient

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "research" / "savestates.local.json"
REPORT = ROOT.parent / "Wii-AI-Golf-Data" / "integration" / "swing-probes.jsonl"
OBSERVATIONS = {"hit", "club-only", "menu", "none", "other"}


def build_probe(preset: str) -> list[SwingSample]:
    """Bounded hypotheses, NOT pre-calibrated Wii Sports swings."""
    if preset not in ("forward", "reverse", "sideways"):
        raise ValueError("unknown preset")
    axis = {
        "forward": (0.0, 1.0, 0.0),
        "reverse": (0.0, -1.0, 0.0),
        "sideways": (1.0, 0.0, 0.0),
    }[preset]
    neg = tuple(-x for x in axis)
    def frame(hold, direction, distance, speed, return_speed):
        return SwingSample(hold, direction, distance, speed, return_speed, 0.0)
    return (
        [frame(True, (0.0, 0.0, 0.0), 0, 0, 0) for _ in range(12)]
        + [frame(True, neg, 0.25, 1.2, 1.2) for _ in range(15)]
        + [frame(True, axis, 0.6, 3.5, 2.0) for _ in range(20)]
        + [frame(False, (0.0, 0.0, 0.0), 0, 0, 0) for _ in range(12)]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="One human-observed Wii Remote swing trial (not a trained shot)")
    parser.add_argument("--preset", choices=("forward", "reverse", "sideways"), default="forward")
    parser.add_argument("--send-live-swing", action="store_true", help="Required to change game controller state")
    parser.add_argument("--reset-profile", help="Optional named SAVED AT FIRST SHOT state; not the pre-Start screen")
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--port", type=int, default=55355)
    parser.add_argument("--remote", type=int, choices=range(4), default=0)
    args = parser.parse_args()

    samples = build_probe(args.preset)
    print(f"Single trial: preset={args.preset}, frames={len(samples)}, remote={args.remote}")
    print("Requires Emulated Wii Remote 1 / Extension None and patched --enable-swing bridge.")
    if not args.send_live_swing:
        print("DRY RUN ONLY. Add --send-live-swing to perform one trial.")
        return

    with FelkRPC(port=args.port) as rpc:
        info = rpc.call("bridge.ping")
        if not isinstance(info, dict) or not isinstance(info.get("bridge_version"), str):
            raise RuntimeError("bridge.ping failed")
        if args.reset_profile:
            profile = StateCatalog(args.catalog).get(args.reset_profile)
            print("State load:", json.dumps(StateManager(rpc).request_load(profile)))
            print("Visually verify the checkpoint loaded at the FIRST SHOT; don't fire on pre-Start.")
        answer = input("When Nueron is standing at the first ball, press ENTER to send ONE swing (or type q to cancel): ")
        if answer.strip().lower() != "":
            print("Canceled without sending a swing.")
            return
        result = SwingTraceClient(rpc, port=args.remote).run(samples)

    print(json.dumps({"source": "live-Felk-swing-dispatch-only", "trace": result}, indent=2))
    print("Observe the game before labeling. A complete trace is NOT proof of ball contact.")
    label = input("What happened? hit / club-only / menu / none / other: ").strip().lower()
    if label not in OBSERVATIONS:
        label = "other"
    record = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "source": "user-observed-live-Felk",
        "probe": "Felk Preview 4 set_wiimote_swing experimental",
        "bridge_version": info["bridge_version"],
        "preset": args.preset,
        "remote": args.remote,
        "reset_profile": args.reset_profile,
        "samples_sha256": hashlib.sha256(json.dumps([[s.hold_a, *s.direction, s.distance_m,
                    s.speed_m_s, s.return_speed_m_s, s.angle_rad] for s in samples],
                    separators=(",", ":")).encode()).hexdigest(),
        "dispatch": result,
        "human_observation": label,
        "game_score": None,
        "warning": "Human label unverified; no automatic outcome detection",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, separators=(",", ":")) + "\n")
    print(f"Recorded one S001 observation at {args.report}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, TimeoutError) as exc:
        print(f"Swing probe failed: {exc}", file=sys.stderr)
        sys.exit(1)
