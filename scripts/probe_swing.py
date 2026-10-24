"""Human-observed, single-shot S001 Felk swing primitive experiment.

Does NOT score shots or run unattended optimization. Requires an up-to-date
--enable-swing patched bridge and Emulated Wii Remote 1, Extension None.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import subprocess
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
from wii_ai_golf.integration.button_prime import prime_a_button, release_buttons

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "research" / "savestates.local.json"
REPORT = ROOT.parent / "Wii-AI-Golf-Data" / "integration" / "swing-probes.jsonl"
OBSERVATIONS = {"hit", "club-only", "menu", "none", "other"}


def build_probe(preset: str, *, follow_through_frames: int = 30,
                a_setup_frames: int = 12) -> list[SwingSample]:
    """Build the unchanged 89-frame first-hit baseline by default.

    Note: A-held neutral SwingSample frames still call set_wiimote_swing.
    To press A *without* touching the swing API, call prime_a_button
    independently BEFORE submitting this trace.
    """
    if type(follow_through_frames) is not int or not 0 <= follow_through_frames <= 180:
        raise ValueError("follow_through_frames must be an integer 0..180")
    if type(a_setup_frames) is not int or not 1 <= a_setup_frames <= 180:
        raise ValueError("a_setup_frames must be an integer 1..180")
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
        # Button precharge is neutral: no translation, speed, or angle.
        [frame(True, (0.0, 0.0, 0.0), 0, 0, 0) for _ in range(a_setup_frames)]
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
    parser.add_argument("--a-setup-frames", type=int, default=12,
                        help="Neutral samples INSIDE the swing trace (1..180; first-hit baseline 12)")
    parser.add_argument("--a-prime-frames", type=int, default=60,
                        help="Separate A-button-only RPC requests BEFORE any swing API call (0..180; default 60)")
    parser.add_argument("--send-live-swing", action="store_true", help="Required to change game controller state")
    parser.add_argument("--attach-running", action="store_true",
                        help="ADVANCED: bypass canonical Dolphin launch/savestate/A-A+B-A intro; "
                             "only for an ALREADY RUNNING, ready-to-swing Dolphin bridge")
    checkpoint = parser.add_mutually_exclusive_group()
    checkpoint.add_argument("--slot", type=int, help="Full-launch only: registered pre-start slot, e.g. 2")
    checkpoint.add_argument("--profile", help="Full-launch only: registered pre-start profile")
    parser.add_argument("--reset-profile", help="Optional named SAVED AT FIRST SHOT state; not the pre-Start screen")
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--port", type=int, default=55355)
    parser.add_argument("--remote", type=int, choices=range(4), default=0)
    args = parser.parse_args()

    if not 0 <= args.follow_through_frames <= 180:
        parser.error("--follow-through-frames must be between 0 and 180")
    if not 1 <= args.a_setup_frames <= 180:
        parser.error("--a-setup-frames must be between 1 and 180")
    if not 0 <= args.a_prime_frames <= 180:
        parser.error("--a-prime-frames must be between 0 and 180")
    samples = build_probe(args.preset,
                          follow_through_frames=args.follow_through_frames,
                          a_setup_frames=args.a_setup_frames)
    a_held_frames = sum(sample.hold_a for sample in samples)
    first_motion_sample = args.a_setup_frames + 1
    print(f"Single trial: preset={args.preset}, frames={len(samples)}, remote={args.remote}")
    print(f"BEFORE ANY swing API call: {args.a_prime_frames} separate BUTTON-ONLY "
          "A-held RPC requests (no set_wiimote_swing).")
    print(f"Within trace: {args.a_setup_frames} A-held zero-motion samples; "
          f"first backswing on sample {first_motion_sample} (1-based).")
    print(f"A held for {a_held_frames} frames; first released on sample {a_held_frames + 1} "
          f"(1-based). Extra follow-through: {args.follow_through_frames} frames.")
    print("Requires Emulated Wii Remote 1 / Extension None and patched --enable-swing bridge.")
    if not args.send_live_swing:
        print("DRY RUN ONLY. Add --send-live-swing to perform one trial.")
        return
    if args.port not in range(1, 65536):
        parser.error("--port must be 1..65535")

    if not args.attach_running:
        if args.reset_profile:
            parser.error("--reset-profile requires --attach-running; the standard "
                         "launcher restores green-pre-start and runs A / A+B / A automatically")
        # Canonical path; no RPC connection is attempted until the launcher
        # has configured Emulated Wii Remote, started Felk Dolphin, loaded the
        # registered pre-start state, and executed the known-good menu sequence.
        # launch_golf.py invokes this probe child with --attach-running to
        # avoid recursive launch.
        command = [
            sys.executable, str(ROOT / "scripts" / "launch_golf.py"),
            "--swing", "--preset", args.preset,
            "--follow-through-frames", str(args.follow_through_frames),
            "--a-setup-frames", str(args.a_setup_frames),
            "--a-prime-frames", str(args.a_prime_frames),
            "--port", str(args.port), "--remote", str(args.remote),
            "--catalog", str(args.catalog), "--report", str(args.report),
        ]
        if args.slot is not None:
            command += ["--slot", str(args.slot)]
        if args.profile is not None:
            command += ["--profile", args.profile]
        print("Starting canonical full golf session: Felk Dolphin -> Emulated Wii "
              "Remote -> pre-start savestate -> A / A+B / A -> guarded swing.", flush=True)
        returncode = subprocess.run(command, check=False).returncode
        if returncode != 0:
            raise SystemExit(returncode)
        return

    if args.slot is not None or args.profile is not None:
        parser.error("--slot/--profile only apply to a full startup, without --attach-running")

    with FelkRPC(port=args.port) as rpc:
        info = rpc.call("bridge.ping")
        if not isinstance(info, dict) or not isinstance(info.get("bridge_version"), str):
            raise RuntimeError("bridge.ping failed")
        # Fail BEFORE any button or swing input if the user is still running
        # the earlier generated bridge. V1 calls set_wiimote_swing on zero
        # motion frames, which is not a reliable A-only hold.
        try:
            caps = rpc.call("trace.swing_capabilities", [])
        except Exception as exc:
            raise RuntimeError(
                "Swing bridge V2 is required. Close Dolphin and run "
                "'py scripts/golf.py bridge upgrade-swing' to regenerate "
                "the version-pinned local bridge (previous bridge is backed up), "
                "then retry the full swing command."
            ) from exc
        if not isinstance(caps, dict) or caps.get("swing_protocol") != 2 or caps.get("neutral_button_only") is not True:
            raise RuntimeError("Swing bridge V2 capability mismatch: refusing to send swing.")
        print("Verified swing bridge V2: neutral trace frames are button-only.", flush=True)
        if args.reset_profile:
            profile = StateCatalog(args.catalog).get(args.reset_profile)
            print("State load:", json.dumps(StateManager(rpc).request_load(profile)))
            print("Visually verify the checkpoint loaded at the FIRST SHOT; don't fire on pre-Start.")
        answer = input("When Nueron is standing at the first ball, press ENTER to send ONE swing (or type q to cancel): ")
        if answer.strip().lower() != "":
            print("Canceled without sending a swing.")
            return
        # No set_wiimote_swing occurs until all button-only requests
        # return. This preserves the first confirmed successful 89-frame
        # waveform while solving the faulty "zero swing = A prime" design.
        print("Sending BUTTON-ONLY A press before initiating the swing...", flush=True)
        try:
            prime_report = prime_a_button(rpc, remote=args.remote,
                                          requests=args.a_prime_frames)
            print(f"Button prehold completed: {prime_report['button_only_requests']} "
                  "RPC requests. Scheduling actual swing now.", flush=True)
            result = SwingTraceClient(rpc, port=args.remote).run(samples)
        finally:
            # Never leave the emulated A press stuck after errors/timeouts.
            release_buttons(rpc, remote=args.remote)

    print(json.dumps({"source": "live-Felk-swing-dispatch-only",
                      "button_prehold": prime_report, "trace": result}, indent=2))
    print("Observe the game before labeling. A complete trace is NOT proof of ball contact.")
    label = input("What happened? hit / club-only / menu / none / other: ").strip().lower()
    if label not in OBSERVATIONS:
        label = "other"
    # These fields are intentionally HUMAN observations, never inferred from
    # a successful bridge ACK. Blank means unknown, not zero or a miss.
    contact = input("Did the ball visibly move? yes / no / unknown [unknown]: ").strip().lower() or "unknown"
    if contact not in ("yes", "no", "unknown"):
        contact = "unknown"
    green = input("Did the ball land on the green? yes / no / unknown [unknown]: ").strip().lower() or "unknown"
    if green not in ("yes", "no", "unknown"):
        green = "unknown"
    distance_text = input("Displayed landing distance to target (number, blank if unknown): ").strip()
    units = None
    distance = None
    if distance_text:
        try:
            parsed = float(distance_text)
            if not math.isfinite(parsed) or parsed < 0:
                raise ValueError("distance must be nonnegative")
            units = input("Distance unit shown in game (e.g. ft, yd, m): ").strip() or None
            if not units:
                print("Unit unknown: retaining distance as UNVERIFIED rather than a scored value.")
            distance = parsed
        except ValueError:
            print("Distance not numeric/nonnegative; recording it as unknown.")
    power_text = input("Visual power gauge estimate 0..100 (blank if unknown): ").strip()
    power_estimate = None
    if power_text:
        try:
            parsed_power = float(power_text)
            if not math.isfinite(parsed_power) or not 0 <= parsed_power <= 100:
                raise ValueError("power outside 0..100")
            power_estimate = parsed_power
        except ValueError:
            print("Invalid gauge estimate; recording unknown.")
    record = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "source": "user-observed-live-Felk",
        "probe": "Felk Preview 4 set_wiimote_swing experimental",
        "bridge_version": info["bridge_version"],
        "preset": args.preset,
        "follow_through_frames": args.follow_through_frames,
        "a_setup_frames": args.a_setup_frames,
        "a_prime_frames": args.a_prime_frames,
        "button_prime_method": "controller.set_wiimote_buttons-only-before-trace.submit_swing",
        "button_prime_dispatch": prime_report,
        "first_motion_sample_1_based": first_motion_sample,
        "a_held_frames": a_held_frames,
        "first_a_release_sample_1_based": a_held_frames + 1,
        "remote": args.remote,
        "reset_profile": args.reset_profile,
        "samples_sha256": hashlib.sha256(json.dumps([[s.hold_a, *s.direction, s.distance_m,
                    s.speed_m_s, s.return_speed_m_s, s.angle_rad] for s in samples],
                    separators=(",", ":")).encode()).hexdigest(),
        "dispatch": result,
        "human_observation": label,
        "human_ball_moved": contact,
        "human_on_green": green,
        "human_displayed_distance": distance,
        "human_displayed_distance_unit": units,
        "human_visual_power_gauge_estimate_pct": power_estimate,
        "observations_quality": "human-reported-not-verified",
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
