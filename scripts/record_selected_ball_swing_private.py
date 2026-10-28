"""One explicitly operator-approved swing with a PRIVATE frame-loop ball watch.

Uses the already-running, separately prepared Felk Swing V2 watched bridge.
Never launches Dolphin, never changes the 89-sample forward waveform, and
never sends raw candidate coordinates to GitHub or stdout.
"""
from __future__ import annotations

import argparse
import hashlib
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
EXPECTED_BASELINE_SHA256 = "b63a1818ba5086c64b0fe7338236a498240e4be97bbd111809a772d783699891"


def verify_frozen_waveform(samples) -> None:
    """The exact #147 V1 human-contact trace; never accept 89 changed samples."""
    if not isinstance(samples, list) or len(samples) != TRACE_SAMPLES:
        raise ValueError("Known-good 89-frame waveform length changed")
    rows = [[s.hold_a, *s.direction, s.distance_m, s.speed_m_s,
             s.return_speed_m_s, s.angle_rad] for s in samples]
    actual = hashlib.sha256(json.dumps(rows, separators=(",", ":"))
                            .encode("utf-8")).hexdigest()
    if actual != EXPECTED_BASELINE_SHA256:
        raise ValueError("Frozen #147 waveform digest changed")




def summarize(samples: list[dict], *, human_ball_moved: str) -> dict:
    """Conservatively corroborate only COMPLETE, source-consistent pilot rows.

    Bridge coroutine ticks are NOT independently verified guest frames, and
    trace samples are requested commands, NOT game-applied shot events.
    """
    if human_ball_moved not in ("yes", "no", "unknown"):
        raise ValueError("Human observation must be yes/no/unknown")
    if not isinstance(samples, list) or not 1 <= len(samples) <= 80:
        raise ValueError("Expected 1..80 bounded observations")
    if any(not isinstance(s, dict) for s in samples):
        raise ValueError("Expected source-gated observation objects")
    indexes = [s.get("frame_tick_index") for s in samples]
    if (any(type(i) is not int for i in indexes)
            or indexes != sorted(set(indexes))):
        raise ValueError("Unordered or duplicated frame tick indices")
    required_vectors = (
        "current_start_f32_candidate",
        "ball_translation_f32_candidate",
        "record_translation_f32_candidate",
    )
    if any(not isinstance(s.get(k), list) or len(s[k]) != 3
           for s in samples for k in required_vectors):
        raise ValueError("Missing source-gated three-component vector")
    starts = [s["current_start_f32_candidate"] for s in samples]
    balls = [s["ball_translation_f32_candidate"] for s in samples]
    records = [s["record_translation_f32_candidate"] for s in samples]
    slots = {s.get("selected_slot_candidate") for s in samples}
    holes = {s.get("source_hole_index") for s in samples}
    owners_ok = all(s.get("source_owner_consistent") is True for s in samples)
    read_budget_ok = all(type(s.get("read_overhead_us")) is int
                         and 0 <= s["read_overhead_us"] <= 5000
                         for s in samples)
    raw_trace_indices = [s.get("trace_sample_index_if_active") for s in samples]
    if any(t is not None and (type(t) is not int or not 0 <= t < 89)
           for t in raw_trace_indices):
        raise ValueError("Invalid commanded trace sample index")
    trace_ids = [s.get("trace_id_if_active") for s in samples
                 if s.get("trace_sample_index_if_active") is not None]
    stable_trace_id = (len(trace_ids) > 0
                       and all(type(tid) is int and tid == trace_ids[0]
                               for tid in trace_ids))
    trace_frames = [s for s in samples
                    if s.get("trace_sample_index_if_active") is not None]
    idle_frames = [s for s in samples
                   if s.get("trace_sample_index_if_active") is None]
    first_trace = next((i for i, s in enumerate(samples)
                        if s.get("trace_sample_index_if_active") is not None),
                       None)
    pretrace_count = first_trace if first_trace is not None else len(samples)
    pretrace_balls = balls[:pretrace_count]
    pretrace_stable = (
        pretrace_count >= 2
        and all(v == pretrace_balls[0] for v in pretrace_balls)
    )
    # A zero-length pretrace has NO approved baseline; do not index [0].
    ball_changed_after_trace_starts = (
        first_trace is not None and pretrace_count >= 1
        and any(x != pretrace_balls[0] for x in balls[first_trace:])
    )
    start_fixed = all(x == starts[0] for x in starts)
    ball_changed = any(x != balls[0] for x in balls[1:])
    slot_stable = len(slots) == 1 and all(type(x) is int and 0 <= x < 4 for x in slots)
    hole_stable = len(holes) == 1 and all(type(x) is int and 0 <= x < 9 for x in holes)
    corroborated = (
        pretrace_stable and ball_changed_after_trace_starts
        and start_fixed and slot_stable and hole_stable
        and owners_ok and read_budget_ok and stable_trace_id
        and human_ball_moved == "yes"
    )
    return {
        "kind": "private-candidate-ball-translation-frame-watch",
        "schema_version": 1,
        "samples": len(samples),
        "distinct_bridge_tick_indexes": len(set(indexes)),
        "samples_with_active_trace": len(trace_frames),
        "samples_without_active_trace": len(idle_frames),
        "source_selected_slot_stable": slot_stable,
        "source_hole_stable": hole_stable,
        "source_owner_consistent_all_samples": owners_ok,
        "read_overhead_within_budget_all_samples": read_budget_ok,
        "commanded_trace_id_stable": stable_trace_id,
        "start_vector_stable": start_fixed,
        "pretrace_control_samples": pretrace_count,
        "pretrace_candidate_ball_stationary": pretrace_stable,
        "candidate_ball_vector_changed_during_recording": ball_changed,
        "candidate_ball_changed_after_trace_start": ball_changed_after_trace_starts,
        "candidate_record_triplet_equal_ball_triplet_count":
            sum(a == b for a, b in zip(records, balls)),
        "human_observed_ball_movement": human_ball_moved,
        "candidate_motion_corroborated_by_human": corroborated,
        "no_button_idle_independently_verified": False,
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
        verify_frozen_waveform(samples)
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
        if status.get("state") != "complete":
            raise RuntimeError("Watch not complete or source/performance gate failed")
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
