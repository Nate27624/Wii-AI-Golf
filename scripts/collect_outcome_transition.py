"""Action-only S002 RAM/score discovery AFTER the canonical fresh Dolphin intro.

Full user command:
 py scripts/run_golf_experiment.py --send-live --script collect_outcome_transition.py -- --send-live-swing
Outer command launches Dolphin, restores green-pre-start and executes A/A+B/A.
This action does NOT launch Dolphin or reset the savestate a second time.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import re
from datetime import datetime, timezone
import hashlib
import json
import math
import random
from dataclasses import replace
from pathlib import Path
import sys
import time
import uuid
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
_LOCAL_SRC = str(ROOT / "src")
if _LOCAL_SRC in sys.path:
    sys.path.remove(_LOCAL_SRC)
sys.path.insert(0, _LOCAL_SRC)
# probe_swing is a sibling script; support an isolated Python -I invocation.
sys.path.insert(0, str(ROOT / "scripts"))

from wii_ai_golf.operator_dialogs import operator_input
from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.integration.swing_client import SwingTraceClient
from wii_ai_golf.integration.button_prime import prime_a_button, release_buttons
from wii_ai_golf.shared.controller_timing import hold_a_for_observed_frames
from wii_ai_golf.audit.outcome_transition import (
    capture_outcome_windows, rank_outcome_candidates)
from wii_ai_golf.audit.outcome_recovery import parse_displayed_distance
from probe_swing import build_probe

DATA_DIR = ROOT.parent / "Wii-AI-Golf-Data" / "captures"


def _answer(prompt: str, *, allowed: set[str],
            input_fn: Callable[[str], str]) -> str:
    while True:
        response = input_fn(prompt).strip().lower()
        if response == "q":
            raise RuntimeError("Operator canceled outcome labeling")
        if response in allowed:
            return response
        print("Choose one of: " + ", ".join(sorted(allowed)))


def _visual_label(input_fn: Callable[[str], str]) -> dict[str, Any]:
    contact = _answer("Was the ball visibly struck? [yes/no/unknown]: ",
                      allowed={"yes", "no", "unknown"}, input_fn=input_fn)
    green = _answer("Did the ball finish on the green? [yes/no/unknown]: ",
                    allowed={"yes", "no", "unknown"}, input_fn=input_fn)
    # Do not discard a successful 14-sample capture because a user enters
    # the game's natural "100.0ft" rather than a bare "100.0".
    while True:
        raw = input_fn("Displayed distance (e.g. 2.1ft, 100.0ft; blank if none): ")
        if raw.strip().lower() == "q":
            raise RuntimeError("Operator canceled outcome labeling")
        try:
            distance, suffix_unit = parse_displayed_distance(raw)
            break
        except ValueError as exc:
            print(f"Invalid distance: {exc}. Please try again; no RAM was lost.")
    unit = "not-visible" if distance is None else (suffix_unit or _answer(
        "Displayed unit [yd/ft/m/unknown]: ",
        allowed={"yd", "ft", "m", "unknown"}, input_fn=input_fn))
    return {"contact_human": contact, "finished_on_green_human": green,
            "displayed_distance_human": distance, "displayed_unit_human": unit,
            "game_distance_verified_by_memory": False}


def _visual_first_label(input_fn: Callable[[str], str]) -> dict[str, Any]:
    """One fast HUMAN terminal-screen note before any post-shot RAM reads.

    G[:distance], M[:distance], U (not sure), T (screen already gone).
    This is not a machine score or an independently authenticated screenshot.
    """
    while True:
        value = input_fn(
            "WATCH THE RESULT NOW. BEFORE next screen enter "
            "G:15.2ft (green), M:100ft (miss), G, M, U (unknown), "
            "T (transitioned), or q to cancel: ").strip()
        if value.lower() == "q":
            raise RuntimeError("Operator canceled terminal result labeling")
        category, colon, number = value.partition(":")
        category = category.strip().lower()
        if category not in ("g", "m", "u", "t") or (colon and category not in ("g", "m")):
            print("Use G[:number], M[:number], U, T, or q.")
            continue
        try:
            distance, unit = parse_displayed_distance(number) if colon else (None, None)
        except ValueError:
            print("Invalid displayed number; use e.g. G:15.2ft or M:100ft.")
            continue
        seen = category in ("g", "m")
        source = (
            "offgreen_100ft_penalty" if category == "m" and distance == 100.0 and unit == "ft"
            else "offgreen_display_unverified" if category == "m" and distance is not None
            else "ongreen_display_human" if category == "g" and distance is not None
            else "unseen_or_not_recorded"
        )
        return {
            "finished_on_green_human": {"g": "yes", "m": "no", "u": "unknown", "t": "unknown"}[category],
            "terminal_screen_seen_before_transition_human": (
                True if seen else False if category == "t" else None),
            "visible_result_class_human": {
                "g": "green", "m": "offgreen", "u": "uncertain", "t": "transitioned"
            }[category],
            "displayed_distance_human": distance,
            "displayed_unit_human": unit or ("unknown" if distance is not None else "not-visible"),
            "displayed_distance_source": source,
            "game_distance_verified_by_memory": False,
        }


def run_session(rpc: Any, *, raw_path: Path, pre_samples: int,
                post_samples: int, settled_samples: int, interval: float,
                input_fn: Callable[[str], str] = operator_input,
                sleep_fn: Callable[[float], None] = time.sleep,
                snapshot_fn: Callable[..., dict[str, Any]] = capture_outcome_windows,
                swing_fn: Callable[[Any], Any] | None = None,
                a_prime_requests: int = 0,
                a_lead_frames: int = 0,
                observe_start_pose: bool = False,
                motion_scale: float = 1.0,
                speed_scale: float = 1.0,
                backswing_scale: float = 1.0,
                trial_seed: int | None = None,
                ask_power: bool = False,
                visual_first: bool = False) -> dict[str, Any]:
    """One opted-in forward shot, bounded RAM snapshots and human landing label.

    Write private raw JSONL immediately, exclusively; cancellation preserves
    any recorded evidence. No inferred hit or landing based on controller ACK.
    """
    if min(pre_samples, post_samples, settled_samples) < 2 or not 0 <= interval <= 5:
        raise ValueError("require >=2 samples per phase, interval between 0 and 5 seconds")
    if type(a_prime_requests) is not int or not 0 <= a_prime_requests <= 180:
        raise ValueError("a_prime_requests must be 0..180")
    if type(a_lead_frames) is not int or not 0 <= a_lead_frames <= 90:
        raise ValueError("a_lead_frames must be 0..90")
    if a_prime_requests and a_lead_frames:
        raise ValueError("choose either RPC-count A prime OR frame-measured A lead, not both")

    # Compute the actual trace length from Worker 1's current waveform.
    # That worker can refine its initial held-A setup without changing this
    # collector; do not claim a fixed 89-frame swing in evidence labels.
    if motion_scale not in (0.6, 0.8, 1.0, 1.2):
        raise ValueError("invalid motion scale")
    if speed_scale not in (0.8, 0.9, 1.0, 1.1) or (motion_scale != 1.0 and speed_scale != 1.0):
        raise ValueError("speed scale must be 0.8/0.9/1.0/1.1 and vary alone")
    if backswing_scale not in (0.8, 1.0, 1.2):
        raise ValueError("backswing scale must be 0.8/1.0/1.2")
    if backswing_scale != 1.0 and (speed_scale != 1.0 or motion_scale != 1.0):
        raise ValueError("backswing study changes one physical parameter only")
    samples = build_probe("forward", follow_through_frames=30)
    if backswing_scale != 1.0:
        samples = [replace(s, distance_m=s.distance_m * backswing_scale)
                   if s.direction == (0.0, -1.0, 0.0) else s for s in samples]
    if motion_scale != 1.0:
        samples = [replace(s, distance_m=s.distance_m * motion_scale,
                           speed_m_s=s.speed_m_s * motion_scale,
                           return_speed_m_s=s.return_speed_m_s * motion_scale)
                   for s in samples]
    if speed_scale != 1.0:
        samples = [replace(s, speed_m_s=s.speed_m_s * speed_scale) for s in samples]
    trace_sha256 = hashlib.sha256(json.dumps(
        [[s.hold_a, *s.direction, s.distance_m, s.speed_m_s,
          s.return_speed_m_s, s.angle_rad] for s in samples],
        separators=(",", ":")).encode()).hexdigest()
    canonical_swing = swing_fn is None
    a_lead_report: dict[str, Any] | None = None
    if canonical_swing:
        def swing_fn(client):
            nonlocal a_lead_report
            # Original, user-confirmed V1 control program stays the default.
            # A lead is a ONE-variable, opt-in timing experiment; it is NOT a
            # validated fix and must never silently affect other experiments.
            if not a_prime_requests and not a_lead_frames:
                return SwingTraceClient(client, port=0).run(samples)
            try:
                if a_lead_frames:
                    print(f"Pressing A BEFORE swing, then observing >= "
                          f"{a_lead_frames} emulated frames without ANY motion RPC.",
                          flush=True)
                    a_lead_report = hold_a_for_observed_frames(
                        client, frames=a_lead_frames, remote=0)
                    print(f"A lead achieved: "
                          f"{a_lead_report['observed_frame_delta']} Dolphin frames "
                          f"(NOT proof the game registered A).", flush=True)
                else:
                    # Historical request-count priming retained only for
                    # explicit diagnosis; RPC count is NOT frame duration.
                    prime_a_button(client, remote=0, requests=a_prime_requests)
                return SwingTraceClient(client, port=0).run(samples)
            finally:
                release_buttons(client, remote=0)
    ready = input_fn("Visually verify golfer is ready. ENTER starts capture; type q to cancel: ")
    if ready.strip():
        return {"cancelled": True, "raw_data_created": False}
    start_pose = None
    if observe_start_pose:
        # Human visual annotation is not an inferred controller angle.
        start_pose = _answer(
            "BEFORE pressing A, initial club position [back/center/forward/unknown]: ",
            allowed={"back", "center", "forward", "unknown"}, input_fn=input_fn)
    rows: list[dict[str, Any]] = []
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    # The visual-first pilot never produces or ranks raw RAM. Other studies
    # retain their original pre/post/settled capture contract unchanged.
    with (nullcontext(None) if visual_first else raw_path.open("x", encoding="utf-8")) as stream:
        def capture_stage(phase: str, count: int) -> None:
            for i in range(count):
                row = snapshot_fn(rpc, phase)
                rows.append(row)
                stream.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
                stream.flush()
                print(f'{phase} {i+1}/{count}: frame {row.get("frame_start")}..{row.get("frame_end")}',
                      flush=True)
                if i + 1 < count and interval:
                    sleep_fn(interval)
        if not visual_first:
            capture_stage("pre", pre_samples)
        approval = input_fn(f"Press ENTER to execute ONE {len(samples)}-frame forward swing; q cancels: ")
        if approval.strip():
            return {"cancelled": True, "raw_data_created": True, "partial_samples": len(rows)}
        shot_start_frame = None
        if observe_start_pose:
            frame = rpc.call("frame.get_count", [])
            if type(frame) is not int or frame < 0:
                raise RuntimeError("invalid frame count before swing")
            shot_start_frame = frame
        stroke = swing_fn(rpc)
        if not isinstance(stroke, dict):
            raise RuntimeError("Swing scheduler did not return a status dict")
        print("Swing dispatch finished; this does NOT establish ball contact.", flush=True)
        if visual_first:
            # No post/settled RPC calls delay the transient terminal result.
            # Only a single compact human observation is requested here.
            annotation = _visual_first_label(input_fn)
            annotation["contact_human"] = _answer(
                "Was the ball visibly struck? [yes/no/unknown]: ",
                allowed={"yes", "no", "unknown"}, input_fn=input_fn)
            stage_valid = annotation["terminal_screen_seen_before_transition_human"] is True
        else:
            print("WATCH THE BALL: only brief post-shot snapshots precede the landing prompt. "
                  "Do not wait for the game's automatic next-screen transition.", flush=True)
            capture_stage("post", post_samples)
            while True:
                label = input_fn(
                    "As soon as the ball stops (BEFORE next screen), press ENTER. "
                    "If already transitioned, type t; q cancels: ").strip().lower()
                if label in ("", "t", "q"):
                    break
                print("Please use ENTER, t (already transitioned), or q.")
            if label == "q":
                return {"cancelled": True, "raw_data_created": True,
                        "partial_samples": len(rows), "swing_dispatch": stroke}
            stage_valid = label == ""
            capture_stage("settled", settled_samples)
    if not visual_first:
        annotation = _visual_label(input_fn)
    if ask_power:
        while True:
            value = input_fn("Observed on-screen power percent (0..100; blank if not visible): ").strip()
            if not value:
                annotation["displayed_power_percent_human"] = None
                break
            try:
                num = float(value.rstrip("%"))
                if not math.isfinite(num) or not 0 <= num <= 100:
                    raise ValueError("outside 0..100")
                annotation["displayed_power_percent_human"] = num
                break
            except ValueError:
                print("Enter power between 0 and 100 or leave blank.")
        annotation["displayed_power_verified_by_memory"] = False
    if observe_start_pose:
        annotation["initial_club_pose_human"] = start_pose
        annotation["initial_club_pose_verified_by_memory"] = False
        annotation["shot_start_frame_before_controller_trace"] = shot_start_frame
    ranked = None if visual_first else rank_outcome_candidates(
        rows, human_distance=annotation["displayed_distance_human"])
    return {"schema_version": 1, "source": "live-emulator-read-only-US-Rev1+human-result-label",
            "utc": datetime.now(timezone.utc).isoformat(),
            "study_id": "S002-HG-OUTCOME-TRANSITION-EXPLORATORY",
            "raw_data_created": not visual_first, "swing_dispatch": stroke,
            "outcome_collection_mode": ("human_terminal_first_no_ram" if visual_first
                                        else "exploratory_ram_post_first"),
            "known_good_swing_request": {
                "preset": "forward", "follow_through_frames": 30,
                "motion_scale": motion_scale, "speed_scale": speed_scale,
                "backswing_scale": backswing_scale,
                "trial_seed": trial_seed,
                "generated_trace_frames": len(samples),
                "trace_generator": "probe_swing.build_probe",
                "trace_sha256": trace_sha256,
                "a_button_only_prime_requests": (
                    (1 if a_lead_frames else a_prime_requests) if canonical_swing else None),
                "a_button_prime_applied": (
                    bool(a_prime_requests or a_lead_frames) if canonical_swing else None),
                "a_lead_requested_frames": a_lead_frames if canonical_swing else None,
                "a_lead_observed_frame_delta": (
                    a_lead_report["observed_frame_delta"] if a_lead_report else None),
                "a_lead_start_frame": (
                    a_lead_report["start_frame_after_a_request"] if a_lead_report else None),
                "a_lead_last_observed_frame": (
                    a_lead_report["last_observed_frame"] if a_lead_report else None),
                "a_priming_evidence": (
                    "frame_observed_A_requested_not_game_verified"
                    if canonical_swing and a_lead_frames
                    else "operator_opt_in_unverified_rpc_count"
                    if canonical_swing and a_prime_requests
                    else "no_separate_button_only_prime" if canonical_swing
                    else "externally_injected_swing_unknown"),
            },
            "human_observation": annotation,
            "settled_screen_observation": (
                "human_terminal_before_transition" if visual_first and stage_valid
                else "human_terminal_unseen_or_unknown" if visual_first
                else "operator_confirmed_before_transition" if stage_valid
                else "screen_had_already_transitioned_before_settled_samples"),
            "candidate_ranking": ranked,
            "warning": "Candidate RAM and labels unverified; no automatic game score or ball XYZ."}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--send-live-swing", action="store_true",
                   help="Explicit opt-in to ONE forward stroke using the current known-good generator")
    p.add_argument("--port", type=int, default=55355)
    p.add_argument("--data-dir", type=Path, default=DATA_DIR,
                   help="PRIVATE local directory; never automatically uploaded")
    p.add_argument("--pre-samples", type=int, default=3)
    p.add_argument("--a-prime-requests", type=int, default=0,
                   help="Optional BUTTON-ONLY A requests before swing (default 0; last observed hits used no separate prime)")
    p.add_argument("--observe-start-pose", action="store_true",
                   help="Ask the operator to label visible initial club pose before swing; V1 repeatability study")
    p.add_argument("--a-lead-frames", type=int, default=0,
                   help="Experimental observed Dolphin frames holding A before trace; default 0, use 12 for V1 timing hypothesis")
    p.add_argument("--post-samples", type=int, default=2)
    p.add_argument("--settled-samples", type=int, default=3)
    p.add_argument("--interval", type=float, default=0.0)
    p.add_argument("--motion-scale", type=float, choices=(0.6,0.8,1.0,1.2), default=1.0)
    p.add_argument("--speed-scale", type=float, choices=(0.8,0.9,1.0,1.1), default=1.0)
    p.add_argument("--backswing-scale", type=float, choices=(0.8,1.0,1.2), default=1.0,
                   help="Scale only backward-travel distance; preserve forward travel, speed and A timing")
    p.add_argument("--trial-seed", type=int, default=None)
    p.add_argument("--ask-power", action="store_true",help="Record the visible game power meter if shown")
    p.add_argument("--visual-first", action="store_true",
                   help="M1.5 human result-first; no post/settled RAM capture or ranking")
    p.add_argument("--run-token", help="Strict unique token supplied by the canonical parent CLI")
    args = p.parse_args(argv)
    if not args.send_live_swing:
        p.error("Requires --send-live-swing and the canonical fresh-launch wrapper")
    if not 1 <= args.port <= 65535:
        p.error("port must be 1..65535")
    if not (2 <= args.pre_samples <= 10 and 2 <= args.post_samples <= 40
            and 2 <= args.settled_samples <= 10):
        p.error("pre=2..10, post=2..40, settled=2..10")
    if not math.isfinite(args.interval) or not 0 <= args.interval <= 5:
        p.error("interval must be finite, 0..5 seconds")
    if not 0 <= args.a_prime_requests <= 180:
        p.error("--a-prime-requests must be between 0 and 180")
    if not 0 <= args.a_lead_frames <= 90:
        p.error("--a-lead-frames must be between 0 and 90")
    if args.a_prime_requests and args.a_lead_frames:
        p.error("cannot combine --a-prime-requests and --a-lead-frames")
    scale = random.Random(args.trial_seed).choice((0.6,0.8,1.0,1.2)) if args.trial_seed is not None else args.motion_scale
    print(f"Motion scale: {scale}; seed: {args.trial_seed}; power unverified",flush=True)
    if args.run_token is not None and not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-[a-f0-9]{10}", args.run_token):
        p.error("Invalid parent run token")
    run_id = args.run_token or (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8])
    raw_file = args.data_dir / f"outcome-{run_id}-RAW-PRIVATE.jsonl"
    summary_file = args.data_dir / f"outcome-{run_id}-candidates.json"
    print("Private raw RAM output:", raw_file)
    print("Never upload the RAW file. Only share the summary after inspection.")
    print("Outer command must already have launched Dolphin and run A/A+B/A.")
    with FelkRPC(port=args.port, timeout_s=15) as rpc:
        result = run_session(rpc, raw_path=raw_file, pre_samples=args.pre_samples,
                             post_samples=args.post_samples,
                             settled_samples=args.settled_samples, interval=args.interval,
                             a_prime_requests=args.a_prime_requests,
                             a_lead_frames=args.a_lead_frames,
                             observe_start_pose=args.observe_start_pose,
                             motion_scale=scale,speed_scale=args.speed_scale,
                             backswing_scale=args.backswing_scale,
                             trial_seed=args.trial_seed,
                             ask_power=args.ask_power,
                             visual_first=args.visual_first)
    if result.get("cancelled"):
        print("Session cancelled:", result)
        # M1.5 cancellation must not be mistaken for a completed shot by parent.
        return 4 if args.visual_first else 0
    result["run_token"] = run_id
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    with summary_file.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print("Candidate summary saved locally:", summary_file)
    if args.visual_first:
        print("M1.5 human terminal result recorded; no RAM candidate ranking performed.")
    else:
        print("Persistent RAM changes:", result["candidate_ranking"]["all_phase_stable_change_count"])
    print("No candidate is yet a verified ball position or official score.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        print(f"Outcome transition experiment failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
