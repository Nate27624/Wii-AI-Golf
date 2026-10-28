"""S001 P0: read-only runtime qualification of the V1 source-selected 51-word watch.

Intended as action for canonical scripts/run_golf_experiment.py AFTER its fresh
Dolphin boot, existing named green-pre-start checkpoint and original menu intro.
This action makes ZERO controller calls, swing traces or guest-memory writes.
Arming the in-memory Felk watcher only schedules source-gated guest RAM reads.

DRAFT: S001/S002/S000 review required; a PASS does NOT approve a live shot.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

from record_selected_ball_swing_v1_private import (
    WATCHED_BRIDGE_NAME,
    preflight,
    verify_local_bridge,
    watched_v1_rpc,
)

WATCH_DURATION = 128
WATCH_INTERVAL = 4
EXPECTED_SAMPLES = 32
MAX_READ_US = 5000
VECTOR_STABILITY_TOL = 1e-4


def _checked_vec(value: object) -> tuple[float, float, float]:
    if (not isinstance(value, list) or len(value) != 3
            or any(type(x) not in (float, int) or not math.isfinite(x)
                   or abs(x) > 100000 for x in value)):
        raise RuntimeError("invalid private candidate vector shape")
    return tuple(float(x) for x in value)


def summarize_qualification(response: dict, *, elapsed_s: float) -> dict:
    """Validate PRIVATE samples locally, return ONLY sanitized aggregate facts."""
    if not isinstance(response, dict):
        raise RuntimeError("missing private watch result")
    status, samples = response.get("status"), response.get("samples")
    if (not isinstance(status, dict) or status.get("state") != "complete"
            or type(status.get("max_read_us")) is not int
            or not isinstance(samples, list)
            or len(samples) != EXPECTED_SAMPLES
            or status.get("samples") != len(samples)
            or response.get("training_allowed") is not False):
        raise RuntimeError("incomplete or ineligible private watch result")
    overhead = status["max_read_us"]
    if overhead < 0 or overhead > MAX_READ_US:
        raise RuntimeError("51-word callback exceeded 5ms budget")
    if type(elapsed_s) not in (float, int) or not 0 <= elapsed_s <= 30:
        raise RuntimeError("invalid observation duration")
    slots, holes, frames = set(), set(), []
    vectors = {field: [] for field in (
        "ball_translation_f32_candidate",
        "record_translation_f32_candidate",
        "current_start_f32_candidate",
    )}
    for row in samples:
        if (not isinstance(row, dict)
                or row.get("input_stage") != "idle_control"
                or row.get("source_owner_consistent") is not True
                or row.get("trace_id_if_active") is not None
                or row.get("trace_sample_index_if_active") is not None):
            raise RuntimeError("watch contaminated by motion/identity transition")
        words = row.get("selected_player_record_words_PRIVATE")
        if (not isinstance(words, list) or len(words) != 51
                or any(type(w) is not int or not 0 <= w <= 0xFFFFFFFF for w in words)):
            raise RuntimeError("source-selected 51-word record incomplete")
        tick = row.get("frame_tick_index")
        if type(tick) is not int or tick < 0:
            raise RuntimeError("invalid bridge tick")
        frames.append(tick)
        slot, hole = row.get("selected_slot_candidate"), row.get("source_hole_index")
        if (type(slot) is not int or not 0 <= slot <= 3
                or type(hole) is not int or not 0 <= hole <= 8):
            raise RuntimeError("selected source slot/hole invalid")
        slots.add(slot)
        holes.add(hole)
        sample_overhead = row.get("read_overhead_us")
        if type(sample_overhead) is not int or not 0 <= sample_overhead <= MAX_READ_US:
            raise RuntimeError("per-sample read budget exceeded")
        for field in vectors:
            vectors[field].append(_checked_vec(row.get(field)))
    if (len(slots) != 1 or len(holes) != 1
            or any(b - a != WATCH_INTERVAL for a, b in zip(frames, frames[1:]))):
        raise RuntimeError("record ownership/frame interval instability")
    stability = {
        field.replace("_f32_candidate", "") + "_stable": all(
            max(abs(a[i] - b[i]) for i in range(3)) <= VECTOR_STABILITY_TOL
            for a, b in zip(values, values[1:])
        )
        for field, values in vectors.items()
    }
    if not all(stability.values()):
        raise RuntimeError("stationary scene did not have stable candidate vectors")
    return {
        "kind": "P0_V1_STATIONARY_WATCH_RUNTIME_QUALIFICATION_REDACTED",
        "result": "PASS",
        "genuine_emulator_source_checked": True,
        "input_or_swing_sent_by_qualifier": False,
        "watch_source_identity_stable": True,
        "same_source_slot_and_hole_throughout": True,
        "sample_count": len(samples),
        "watch_interval_bridge_ticks": WATCH_INTERVAL,
        "maximum_sample_read_microseconds": overhead,
        "read_limit_microseconds": MAX_READ_US,
        "observer_elapsed_seconds_rounded": round(float(elapsed_s), 2),
        "frame_counter_type": "bridge_coroutine_tick_not_guest_physics_frame",
        "stationary_candidate_vectors": stability,
        "raw_words_printed_or_uploaded": False,
        "ball_world_xyz_verified": False,
        "impact_or_power_verified": False,
        "training_allowed": False,
        "live_swing_automatically_authorized": False,
    }


def qualify_running(rpc: Any, *,
                    clock: Callable[[], float] = time.monotonic,
                    sleep: Callable[[float], None] = time.sleep) -> dict:
    """No controller, trace.submit, savestate, or memory write RPC calls."""
    preflight(rpc)
    start = clock()
    armed = rpc.call("golf.ball_watch.arm", [WATCH_DURATION, WATCH_INTERVAL])
    if (not isinstance(armed, dict) or armed.get("state") != "armed"
            or armed.get("requested_duration_frames") != WATCH_DURATION
            or armed.get("interval_frames") != WATCH_INTERVAL):
        raise RuntimeError("read-only watcher did not arm as specified")
    for _ in range(700):
        status = rpc.call("golf.ball_watch.status", [])
        if not isinstance(status, dict):
            raise RuntimeError("malformed watcher status")
        if status.get("state") == "complete":
            private = rpc.call("golf.ball_watch.drain", [])
            return summarize_qualification(private, elapsed_s=clock() - start)
        if status.get("state") not in ("armed", "recording"):
            raise RuntimeError("source gate/overhead failure during stationary watch")
        if clock() - start > 15:
            raise TimeoutError("read-only qualification timed out; no shot attempted")
        sleep(0.018)
    raise TimeoutError("read-only qualification exhausted polling budget")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read-only-live", action="store_true",
                        help="Explicitly qualify an already booted V1 watcher with no input")
    parser.add_argument("--port", type=int, default=55355)
    args = parser.parse_args(argv)
    if not args.read_only_live:
        print(json.dumps({
            "kind": "P0_V1_STATIONARY_WATCH_DRY_RUN",
            "dolphin_or_rpc_contacted": False,
            "input_or_swing_sent": False,
            "watch_frames": WATCH_DURATION,
            "sample_interval": WATCH_INTERVAL,
            "live_swing_approved": False,
        }, indent=2))
        return 0
    if not 1 <= args.port <= 65535:
        parser.error("invalid port")
    try:
        verify_local_bridge(ROOT.parent / "tools" / WATCHED_BRIDGE_NAME)
        with watched_v1_rpc(port=args.port) as rpc:
            report = qualify_running(rpc)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (OSError, RuntimeError, ValueError, TimeoutError, TypeError):
        print("P0 stationary watched runtime qualification REFUSED (no shot sent).",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
