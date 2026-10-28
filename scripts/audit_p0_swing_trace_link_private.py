"""Independent OFFLINE audit of a PRIVATE watched swing / controller-trace link.

No Dolphin, controller/RPC, game-memory writes, upload or raw value stdout.
This validates a local report schema, not the game physics or guest frame clock.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys

DATA_ROOT = Path(__file__).resolve().parents[2] / "Wii-AI-Golf-Data"
STAGES = ("idle_control", "a_prime", "trace", "posttrace")
PHASES = ("idle_control", "a_prime", "trace_neutral", "backswing",
          "forward_swing", "followthrough", "a_release", "posttrace")
WORDS = 0xCC // 4


def _vec(row: dict, name: str) -> tuple[float, float, float]:
    value = row.get(name)
    if (not isinstance(value, list) or len(value) != 3 or
            any(type(x) not in (int, float) or not math.isfinite(x)
                or abs(x) > 100000 for x in value)):
        raise ValueError("Invalid bounded source vector")
    return tuple(float(x) for x in value)


def _phase(index: int) -> str:
    if index < 12:
        return "trace_neutral"
    if index < 27:
        return "backswing"
    if index < 47:
        return "forward_swing"
    if index < 77:
        return "followthrough"
    return "a_release"


def audit(report: dict) -> dict:
    if not isinstance(report, dict) or report.get("kind") != "PRIVATE-UNVERIFIED-selected-ball-frame-watch":
        raise ValueError("Unrecognized private capture")
    status = report.get("watch_status")
    trace = report.get("bridge_trace_status")
    producer = report.get("safe_summary")
    if not all(isinstance(x, dict) for x in (status, trace, producer)):
        raise ValueError("Missing producer status")
    trace_id = trace.get("id")
    if (status.get("state") != "complete" or
            trace.get("state") != "complete" or trace.get("kind") != "swing" or
            type(trace_id) is not int or trace_id < 1 or
            type(trace.get("total_frames")) is not int or trace["total_frames"] != 89 or
            type(trace.get("applied_frames")) is not int or trace["applied_frames"] != 89):
        raise ValueError("Incomplete or wrong controller trace / watcher")
    rows = report.get("PRIVATE_UNVERIFIED_NUMERIC_VECTORS")
    if not isinstance(rows, list) or not 2 <= len(rows) <= 80:
        raise ValueError("Missing or unbounded memory samples")
    if ("samples" in status and
            (type(status["samples"]) is not int or status["samples"] != len(rows))):
        raise ValueError("Watcher sample count inconsistent")
    label = report.get("operator_observation")
    if label not in ("yes", "no", "unknown"):
        raise ValueError("Missing independent human observation")

    counts: Counter[str] = Counter()
    ticks: list[int] = []
    trace_indexes: list[int] = []
    stages: list[int] = []
    slots: set[int] = set()
    holes: set[int] = set()
    start: list[tuple[float, float, float]] = []
    pretrace: list[tuple[float, float, float]] = []
    idle_ball: list[tuple[float, float, float]] = []
    after_trace: list[tuple[float, float, float]] = []
    trace_seen = False
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid sample")
        words = row.get("selected_player_record_words_PRIVATE")
        if (not isinstance(words, list) or len(words) != WORDS or
                any(type(w) is not int or not 0 <= w <= 0xFFFFFFFF for w in words)):
            raise ValueError("Incomplete source-selected record")
        tick = row.get("frame_tick_index")
        elapsed = row.get("read_overhead_us")
        slot = row.get("selected_slot_candidate")
        hole = row.get("source_hole_index")
        stage = row.get("input_stage")
        index = row.get("trace_sample_index_if_active")
        active_id = row.get("trace_id_if_active")
        if (type(tick) is not int or tick < 0 or type(elapsed) is not int or
                not 0 <= elapsed <= 5000 or type(slot) is not int or
                not 0 <= slot < 4 or type(hole) is not int or
                not 0 <= hole <= 8 or row.get("source_owner_consistent") is not True or
                stage not in STAGES):
            raise ValueError("Invalid source, timing, or watch budget")
        ticks.append(tick)
        slots.add(slot)
        holes.add(hole)
        stages.append(STAGES.index(stage))
        vector = _vec(row, "ball_translation_f32_candidate")
        start.append(_vec(row, "current_start_f32_candidate"))
        _vec(row, "record_translation_f32_candidate")
        if stage == "trace":
            if (type(index) is not int or not 0 <= index < 89 or
                    type(active_id) is not int or active_id != trace_id):
                raise ValueError("Watched swing trace ID mismatch")
            trace_indexes.append(index)
            counts[_phase(index)] += 1
            trace_seen = True
        else:
            if index is not None or active_id is not None:
                raise ValueError("Nontrace stage claims active swing")
            counts[stage] += 1
        if not trace_seen:
            pretrace.append(vector)
        else:
            after_trace.append(vector)
        if stage == "idle_control":
            idle_ball.append(vector)
    if (ticks != sorted(set(ticks)) or stages != sorted(stages) or
            trace_indexes != sorted(set(trace_indexes)) or
            len(slots) != 1 or len(holes) != 1 or
            not trace_indexes):
        raise ValueError("Chronological source identity / trace integrity failed")
    stable_start = len(set(start)) == 1
    stable_idle = len(idle_ball) >= 2 and len(set(idle_ball)) == 1
    stable_pretrace = len(pretrace) >= 2 and len(set(pretrace)) == 1
    changed_after_trace = bool(pretrace and any(v != pretrace[0] for v in after_trace))
    if (producer.get("watch_complete") is not True or
            producer.get("source_selected_slot_stable") is not True or
            producer.get("source_hole_stable") is not True or
            producer.get("source_owner_consistency_checks_passed") is not True or
            producer.get("read_performance_checks_passed") is not True or
            producer.get("start_vector_stable") is not stable_start or
            producer.get("idle_control_vector_stationary") is not stable_idle or
            producer.get("pretrace_candidate_ball_stationary") is not stable_pretrace or
            producer.get("candidate_ball_changed_after_trace_start") is not changed_after_trace or
            producer.get("human_observed_ball_movement") != label):
        raise ValueError("Producer summary conflicts with private evidence")
    missing = [phase for phase in PHASES if counts[phase] == 0]
    complete_controls = not missing and stable_start and stable_idle and stable_pretrace
    correlated = bool(complete_controls and changed_after_trace and label == "yes")
    return {
        "kind": "p0-offline-private-trace-watch-link-audit",
        "schema_version": 1,
        "private_sample_count": len(rows),
        "bridge_trace_id_matches_all_active_memory_samples": True,
        "bridge_reports_completed_89_frame_swing": True,
        "sampled_phase_counts": {p: counts[p] for p in PHASES},
        "missing_phases": missing,
        "chronological_stages_and_trace_indexes_verified": True,
        "source_owner_slot_hole_stable": True,
        "source_start_stable": stable_start,
        "idle_and_pretrace_stationary": stable_idle and stable_pretrace,
        "ball_candidate_changed_after_trace_started": changed_after_trace,
        "human_observed_movement": label,
        "complete_control_coverage": complete_controls,
        "candidate_motion_corroborated_not_physical_proof": correlated,
        "bridge_callback_tick_is_guest_frame_verified": False,
        "frame_applied_input_time_verified": False,
        "actual_ball_xyz_or_collision_verified": False,
        "power_or_velocity_verified": False,
        "uncensored_result_distance_verified": False,
        "approved_for_training": False,
        "allowed_to_publish": False,
    }


def _read_private(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or not path.name.endswith("-PRIVATE.json"):
        raise ValueError("Missing or linked private report")
    root = DATA_ROOT.resolve(strict=True)
    actual = path.resolve(strict=True)
    if not actual.is_relative_to(root) or actual.stat().st_size > 2_000_000:
        raise ValueError("Untrusted private report location/size")
    return json.loads(actual.read_text(encoding="utf-8"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = audit(_read_private(args.private_report))
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    except (OSError, ValueError, TypeError, KeyError, OverflowError, json.JSONDecodeError):
        print("P0 private trace-link verification refused; no raw values or paths exposed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
