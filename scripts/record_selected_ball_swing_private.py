"""One explicitly operator-approved swing with a PRIVATE frame-loop ball watch.

Uses the already-running, separately prepared Felk Swing V2 watched bridge.
Never launches Dolphin, never changes the 89-sample forward waveform, and
never sends raw candidate coordinates to GitHub or stdout.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.integration.swing_client import SwingTraceClient
from wii_ai_golf.integration.button_prime import prime_a_button, release_buttons
from probe_swing import build_probe

PRIVATE_ROOT = (ROOT.parent / "Wii-AI-Golf-Data")
TRACE_SAMPLES = 89


def summarize(samples: list[dict], *, human_ball_moved: str) -> dict:
    if human_ball_moved not in ("yes", "no", "unknown"):
        raise ValueError("Human observation must be yes/no/unknown")
    if not samples or len(samples) > 80:
        raise ValueError("Expected 1..80 bounded observations")
    indexes = [s["frame_tick_index"] for s in samples]
    if any(type(i) is not int for i in indexes) or indexes != sorted(set(indexes)):
        raise ValueError("Unordered or duplicated frame tick indices")
    starts = [s["current_start_f32_candidate"] for s in samples]
    balls = [s["ball_translation_f32_candidate"] for s in samples]
    records = [s["record_translation_f32_candidate"] for s in samples]
    slots = {s["selected_slot_candidate"] for s in samples}
    holes = {s["source_hole_index"] for s in samples}
    trace_frames = [s for s in samples if s["trace_sample_index_if_active"] is not None]
    idle_frames = [s for s in samples if s["trace_sample_index_if_active"] is None]
    start_fixed = all(x == starts[0] for x in starts)
    ball_changed = any(x != balls[0] for x in balls[1:])
    return {
        "kind": "private-candidate-ball-translation-frame-watch",
        "schema_version": 1,
        "samples": len(samples),
        "distinct_bridge_tick_indexes": len(set(indexes)),
        "samples_with_active_trace": len(trace_frames),
        "samples_without_active_trace": len(idle_frames),
        "source_selected_slot_stable": len(slots) == 1,
        "source_hole_stable": len(holes) == 1,
        "start_vector_stable": start_fixed,
        "candidate_ball_vector_changed_during_recording": ball_changed,
        "candidate_record_triplet_equal_ball_triplet_count":
            sum(a == b for a, b in zip(records, balls)),
        "human_observed_ball_movement": human_ball_moved,
        "candidate_motion_corroborated_by_human": (
            ball_changed and start_fixed and len(slots) == 1
            and len(holes) == 1 and human_ball_moved == "yes"),
        "guest_emulator_frame_verified": False,
        "actual_active_ball_xyz_verified": False,
        "ball_velocity_verified": False,
        "impact_contact_time_verified": False,
        "swing_power_verified": False,
        "training_allowed": False,
        "allowed_to_publish": False,
    }


def _private_output(path: Path) -> Path:
    root = PRIVATE_ROOT.resolve(strict=True)
    output = path.resolve(strict=False)
    if not output.parent.is_dir() or not output.is_relative_to(root):
        raise ValueError("Private output must stay in ignored sibling Data root")
    if output.suffix != ".json" or not output.name.endswith("-PRIVATE.json"):
        raise ValueError("Output filename must end -PRIVATE.json")
    if output.is_symlink() or output.exists():
        raise ValueError("Never overwrite existing private trace")
    return output


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attach-running", action="store_true",
                        help="Requires operator-ready Dolphin with watched bridge loaded")
    parser.add_argument("--send-live-swing", action="store_true",
                        help="EXPLICIT opt-in: sends the known-good V1 swing to Dolphin")
    parser.add_argument("--port", type=int, default=55355)
    parser.add_argument("--remote", type=int, default=0, choices=range(4))
    parser.add_argument("--a-prime-frames", type=int, default=45)
    parser.add_argument("--interval", type=int, default=4)
    parser.add_argument("--duration", type=int, default=256)
    parser.add_argument("--private-output", type=Path)
    args = parser.parse_args(argv)
    if args.a_prime_frames != 45 or args.interval != 4 or args.duration != 256:
        parser.error("This pilot fixes A lead45, interval4, duration256 to limit confounds")
    if not args.send_live_swing:
        print(json.dumps({
            "kind": "ball-watch-swing-dry-run",
            "live_input_sent": False,
            "preserved_known_good_trace_samples": TRACE_SAMPLES,
            "requires_attach_running": True,
            "private_only": True,
            "next_step": "Start prepared watched bridge in the canonical launcher, then explicitly opt in"
        }, indent=2))
        return 0
    if not args.attach_running:
        parser.error("Live study requires --attach-running (never auto-launch Dolphin)")
    if args.private_output is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        args.private_output = PRIVATE_ROOT / "captures" / (
            "selected-ball-frame-watch-" + stamp + "-PRIVATE.json")
    try:
        output = _private_output(args.private_output)
        samples = build_probe("forward", follow_through_frames=30, a_setup_frames=12)
        if len(samples) != TRACE_SAMPLES:
            raise ValueError("Known-good 89-frame waveform changed")
        with FelkRPC(port=args.port) as rpc:
            ping = rpc.call("bridge.ping", [])
            caps = rpc.call("trace.swing_capabilities", [])
            watch = rpc.call("golf.ball_watch.status", [])
            if (not isinstance(ping, dict) or not isinstance(caps, dict)
                    or caps.get("swing_protocol") != 2
                    or caps.get("neutral_button_only") is not True
                    or watch.get("state") != "idle"):
                raise RuntimeError("Wrong bridge or watch already active; no input sent")
            print("Read-only preflight passed. This command will send ONE real swing.")
            answer = input("At the stationary first ball, type SWING to begin, or Enter to cancel: ")
            if answer.strip() != "SWING":
                print("Canceled; no controller input.")
                return 0
            rpc.call("golf.ball_watch.arm", [args.duration, args.interval])
            try:
                # Idle control: frame advances with no controller commands.
                for _ in range(24):
                    rpc.call("frame.get_count", [])
                prime_a_button(rpc, remote=args.remote, requests=45)
                trace = SwingTraceClient(rpc, port=args.remote).run(samples)
                # Collect post-dispatch samples (not proof of a game-applied shot).
                for _ in range(36):
                    rpc.call("frame.get_count", [])
            finally:
                release_buttons(rpc, remote=args.remote)
                watch_report = rpc.call("golf.ball_watch.drain", [])
        status = watch_report.get("status", {})
        if status.get("state") in ("source_gate_failed", "read_overhead_exceeded"):
            raise RuntimeError("Watch source gate/performance failed; no numeric data exported")
        watch_samples = watch_report.get("samples")
        if not isinstance(watch_samples, list) or not watch_samples:
            raise RuntimeError("Watch returned zero candidate frames")
        label = (input("Did the visible ball move? yes/no/unknown [unknown]: ")
                 .strip().lower() or "unknown")
        if label not in ("yes", "no", "unknown"):
            label = "unknown"
        safe = summarize(watch_samples, human_ball_moved=label)
        report = {
            "kind": "PRIVATE-UNVERIFIED-selected-ball-frame-watch",
            "utc": datetime.now(timezone.utc).isoformat(),
            "operator_observation": label,
            "bridge_trace_status": trace,
            "watch_status": status,
            "safe_summary": safe,
            # Only in this ignored local file, NEVER uploaded or printed.
            "PRIVATE_UNVERIFIED_NUMERIC_VECTORS": watch_samples,
        }
        with output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
        print(json.dumps(safe, indent=2, sort_keys=True))
        print("Saved full numeric trace to PRIVATE Data root; do not upload the file.")
        return 0
    except (OSError, TypeError, ValueError, RuntimeError, TimeoutError,
            KeyboardInterrupt) as exc:
        print("Ball watch pilot stopped or refused: " + type(exc).__name__
              + " (no private vectors printed)", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
