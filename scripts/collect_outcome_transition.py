"""Action-only S002 RAM/score discovery AFTER the canonical fresh Dolphin intro.

Full user command:
 py scripts/run_golf_experiment.py --send-live --script collect_outcome_transition.py -- --send-live-swing
Outer command launches Dolphin, restores green-pre-start and executes A/A+B/A.
This action does NOT launch Dolphin or reset the savestate a second time.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
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

from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.integration.swing_client import SwingTraceClient
from wii_ai_golf.audit.outcome_transition import (
    capture_outcome_windows, rank_outcome_candidates)
from probe_swing import build_probe

DATA_DIR = ROOT.parent / "Wii-AI-Golf-Data" / "captures"


def _answer(prompt: str, *, allowed: set[str],
            input_fn: Callable[[str], str]) -> str:
    while True:
        response = input_fn(prompt).strip().lower()
        if response in allowed:
            return response
        print("Choose one of: " + ", ".join(sorted(allowed)))


def _visual_label(input_fn: Callable[[str], str]) -> dict[str, Any]:
    contact = _answer("Was the ball visibly struck? [yes/no/unknown]: ",
                      allowed={"yes", "no", "unknown"}, input_fn=input_fn)
    green = _answer("Did the ball finish on the green? [yes/no/unknown]: ",
                    allowed={"yes", "no", "unknown"}, input_fn=input_fn)
    distance = None
    raw = input_fn("Exact DISPLAYED distance number (blank if not shown): ").strip()
    if raw:
        try:
            distance = float(raw)
        except ValueError as exc:
            raise ValueError("Displayed distance must be a number; leave blank if unknown") from exc
        if not math.isfinite(distance) or distance < 0:
            raise ValueError("Displayed distance must be a nonnegative finite number")
    unit = "not-visible"
    if distance is not None:
        unit = _answer("Displayed unit [yd/ft/m/unknown]: ",
                       allowed={"yd", "ft", "m", "unknown"}, input_fn=input_fn)
    return {"contact_human": contact, "finished_on_green_human": green,
            "displayed_distance_human": distance, "displayed_unit_human": unit,
            "game_distance_verified_by_memory": False}


def run_session(rpc: Any, *, raw_path: Path, pre_samples: int,
                post_samples: int, settled_samples: int, interval: float,
                input_fn: Callable[[str], str] = input,
                sleep_fn: Callable[[float], None] = time.sleep,
                snapshot_fn: Callable[..., dict[str, Any]] = capture_outcome_windows,
                swing_fn: Callable[[Any], Any] | None = None) -> dict[str, Any]:
    """One opted-in forward shot, bounded RAM snapshots and human landing label.

    Write private raw JSONL immediately, exclusively; cancellation preserves
    any recorded evidence. No inferred hit or landing based on controller ACK.
    """
    if min(pre_samples, post_samples, settled_samples) < 2 or not 0 <= interval <= 5:
        raise ValueError("require >=2 samples per phase, interval between 0 and 5 seconds")
    # Compute the actual trace length from Worker 1's current waveform.
    # That worker can refine its initial held-A setup without changing this
    # collector; do not claim a fixed 89-frame swing in evidence labels.
    samples = build_probe("forward", follow_through_frames=30)
    if swing_fn is None:
        swing_fn = lambda client: SwingTraceClient(client, port=0).run(samples)
    ready = input_fn("Visually verify golfer is ready. ENTER starts capture; type q to cancel: ")
    if ready.strip():
        return {"cancelled": True, "raw_data_created": False}
    rows: list[dict[str, Any]] = []
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    with raw_path.open("x", encoding="utf-8") as stream:
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
        capture_stage("pre", pre_samples)
        approval = input_fn(f"Press ENTER to execute ONE {len(samples)}-frame forward swing; q cancels: ")
        if approval.strip():
            return {"cancelled": True, "raw_data_created": True, "partial_samples": len(rows)}
        stroke = swing_fn(rpc)
        if not isinstance(stroke, dict):
            raise RuntimeError("Swing scheduler did not return a status dict")
        print("Swing dispatch finished; this does NOT establish ball contact.", flush=True)
        capture_stage("post", post_samples)
        label = input_fn("Wait until ball stops/result is visible, then ENTER (q if uncertain): ")
        if label.strip():
            return {"cancelled": True, "raw_data_created": True,
                    "partial_samples": len(rows), "swing_dispatch": stroke}
        capture_stage("settled", settled_samples)
    annotation = _visual_label(input_fn)
    ranked = rank_outcome_candidates(rows, human_distance=annotation["displayed_distance_human"])
    return {"schema_version": 1, "source": "live-emulator-read-only-US-Rev1+human-result-label",
            "utc": datetime.now(timezone.utc).isoformat(),
            "study_id": "S002-HG-OUTCOME-TRANSITION-EXPLORATORY",
            "raw_data_created": True, "swing_dispatch": stroke,
            "known_good_swing_request": {
                "preset": "forward", "follow_through_frames": 30,
                "generated_trace_frames": len(samples),
                "trace_generator": "probe_swing.build_probe",
            },
            "human_observation": annotation, "candidate_ranking": ranked,
            "warning": "Candidate RAM and labels unverified; no automatic game score or ball XYZ."}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--send-live-swing", action="store_true",
                   help="Explicit opt-in to ONE forward stroke using the current known-good generator")
    p.add_argument("--port", type=int, default=55355)
    p.add_argument("--data-dir", type=Path, default=DATA_DIR,
                   help="PRIVATE local directory; never automatically uploaded")
    p.add_argument("--pre-samples", type=int, default=3)
    p.add_argument("--post-samples", type=int, default=8)
    p.add_argument("--settled-samples", type=int, default=3)
    p.add_argument("--interval", type=float, default=0.4)
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
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
    raw_file = args.data_dir / f"outcome-{run_id}-RAW-PRIVATE.jsonl"
    summary_file = args.data_dir / f"outcome-{run_id}-candidates.json"
    print("Private raw RAM output:", raw_file)
    print("Never upload the RAW file. Only share the summary after inspection.")
    print("Outer command must already have launched Dolphin and run A/A+B/A.")
    with FelkRPC(port=args.port, timeout_s=15) as rpc:
        result = run_session(rpc, raw_path=raw_file, pre_samples=args.pre_samples,
                             post_samples=args.post_samples,
                             settled_samples=args.settled_samples, interval=args.interval)
    if result.get("cancelled"):
        print("Session cancelled:", result)
        return 0
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    with summary_file.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print("Candidate summary saved locally:", summary_file)
    print("Persistent RAM changes:", result["candidate_ranking"]["all_phase_stable_change_count"])
    print("No candidate is yet a verified ball position or official score.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        print(f"Outcome transition experiment failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
