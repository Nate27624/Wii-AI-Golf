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


# Resolve the canonical source checkout BEFORE importing wii_ai_golf.
# Editable pip installs may point at a different Git worktree.
# This also works with Python -I (isolated mode) and from any CWD.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_LOCAL_SRC = str(_REPO_ROOT / "src")
if _LOCAL_SRC in sys.path:
    sys.path.remove(_LOCAL_SRC)
sys.path.insert(0, _LOCAL_SRC)

from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.integration.savestates import StateCatalog, StateManager
from wii_ai_golf.integration.swing_client import SwingSample, SwingTraceClient

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "research" / "savestates.local.json"
REPORT = ROOT.parent / "Wii-AI-Golf-Data" / "integration" / "swing-probes.jsonl"
OBSERVATIONS = {"hit", "club-only", "menu", "none", "other"}


def build_probe(preset: str, *, follow_through_frames: int = 30) -> list[SwingSample]:
    """Bounded swing probe. Keep A held through a tunable follow-through.

    Before this change A was released after 47 samples (12+15+20);
    user observed premature release in Wii Sports on a live trial.
    """
    if type(follow_through_frames) is not int or not 0 <= follow_through_frames <= 180:
        raise ValueError("follow_through_frames must be an integer 0..180")
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
        # Do not release A immediately after forward motion: the club needs
        # time to finish the stroke while the button is still held.
        + [frame(True, (0.0, 0.0, 0.0), 0, 0, 0) for _ in range(follow_through_frames)]
        + [frame(False, (0.0, 0.0, 0.0), 0, 0, 0) for _ in range(12)]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="One human-observed Wii Remote swing trial (not a trained shot)")
    parser.add_argument("--preset", choices=("forward", "reverse", "sideways"), default="forward")
    parser.add_argument("--follow-through-frames", type=int, default=30,
                        help="Extra frames holding A after the forward stroke, before release (0..180; default 30)")
    parser.add_argument("--send-live-swing", action="store_true", help="Required to change game controller state")
    parser.add_argument("--reset-profile", help="Optional named SAVED AT FIRST SHOT state; not the pre-Start screen")
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--port", type=int, default=55355)
    parser.add_argument("--remote", type=int, choices=range(4), default=0)
    args = parser.parse_args()

    if not 0 <= args.follow_through_frames <= 180:
        parser.error("--follow-through-frames must be between 0 and 180")
    samples = build_probe(args.preset, follow_through_frames=args.follow_through_frames)
    a_held_frames = sum(sample.hold_a for sample in samples)
    print(f"Single trial: preset={args.preset}, frames={len(samples)}, remote={args.remote}")
    print(f"A held for {a_held_frames} frames; first released on sample {a_held_frames + 1} "
          f"(1-based). Extra follow-through: {args.follow_through_frames} frames.")
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
        "follow_through_frames": args.follow_through_frames,
        "a_held_frames": a_held_frames,
        "first_a_release_sample_1_based": a_held_frames + 1,
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
