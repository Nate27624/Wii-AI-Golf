"""OFFLINE ONLY: rank selected-player 0xCC record changes during watched swing.

Consumes solely the S001 watched-bridge PRIVATE JSON. No Dolphin, controller,
RPC, memory writes, public publisher, paths or values on stdout. The per-frame
record is a CANDIDATE memory window, not typed swing power/club kinematics.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT.parent / "Wii-AI-Golf-Data"
WORD_COUNT = 0xCC // 4
KNOWN_AIM_WORDS = set((0x3C, 0x40, 0x44, 0x48, 0x4C)) | set(range(0x94, 0xC4, 4))
PHASES = (
    "idle_control", "a_prime", "trace_neutral", "backswing",
    "forward_swing", "followthrough", "a_release", "posttrace"
)


def _phase(row: dict) -> str:
    stage = row.get("input_stage")
    if stage in ("idle_control", "a_prime", "posttrace"):
        if row.get("trace_sample_index_if_active") is not None:
            raise ValueError("Nontrace stage contains active sample")
        return stage
    if stage != "trace":
        raise ValueError("Unknown or missing watcher input stage")
    idx = row.get("trace_sample_index_if_active")
    if type(idx) is not int or idx < 0 or idx >= 89:
        raise ValueError("Bad commanded swing sample index")
    if idx <= 11:
        return "trace_neutral"
    if idx <= 26:
        return "backswing"
    if idx <= 46:
        return "forward_swing"
    if idx <= 76:
        return "followthrough"
    return "a_release"


def analyze(report: dict) -> dict:
    if not isinstance(report, dict) or report.get("kind") != "PRIVATE-UNVERIFIED-selected-ball-frame-watch":
        raise ValueError("Unrecognized local private watch report")
    status = report.get("watch_status", {})
    safe = report.get("safe_summary", {})
    if (not isinstance(status, dict) or status.get("state") != "complete"
            or not isinstance(safe, dict)
            or safe.get("watch_complete") is not True
            or safe.get("source_owner_consistency_checks_passed") is not True
            or safe.get("read_performance_checks_passed") is not True
            or safe.get("source_selected_slot_stable") is not True
            or safe.get("source_hole_stable") is not True
            or safe.get("start_vector_stable") is not True):
        raise ValueError("Failed/partial/unstable source watch cannot be analyzed")
    rows = report.get("PRIVATE_UNVERIFIED_NUMERIC_VECTORS")
    if not isinstance(rows, list) or not 2 <= len(rows) <= 80:
        raise ValueError("Missing or unbounded private watch records")
    buckets: dict[str, list[list[int]]] = {phase: [] for phase in PHASES}
    tick_ids = []
    trace_ids = set()
    trace_sample_indexes = []
    stage_ranks = []
    slots = set()
    holes = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Malformed private row")
        words = row.get("selected_player_record_words_PRIVATE")
        if (not isinstance(words, list) or len(words) != WORD_COUNT
                or any(type(w) is not int or w < 0 or w > 0xFFFFFFFF for w in words)):
            raise ValueError("Expected 51 bounded big-endian source record u32 words")
        tick = row.get("frame_tick_index")
        if type(tick) is not int or tick < 0:
            raise ValueError("Invalid callback tick")
        tick_ids.append(tick)
        read_us = row.get("read_overhead_us")
        if type(read_us) is not int or not 0 <= read_us <= 5000:
            raise ValueError("Over-budget or absent read timing")
        if row.get("source_owner_consistent") is not True:
            raise ValueError("Player record source identity failed")
        slots.add(row.get("selected_slot_candidate"))
        holes.add(row.get("source_hole_index"))
        phase = _phase(row)
        stage = row["input_stage"]
        stage_ranks.append({"idle_control": 0, "a_prime": 1,
                            "trace": 2, "posttrace": 3}[stage])
        if stage == "trace":
            trace_ids.add(row.get("trace_id_if_active"))
            trace_sample_indexes.append(row["trace_sample_index_if_active"])
        elif row.get("trace_id_if_active") is not None:
            raise ValueError("Nontrace control row contains live trace ID")
        buckets[phase].append(words)
    if (tick_ids != sorted(set(tick_ids)) or len(slots) != 1
            or len(holes) != 1 or len(trace_ids) != 1
            or any(type(t) is not int or t < 1 for t in trace_ids)
            or stage_ranks != sorted(stage_ranks) or stage_ranks[0] != 0
            or trace_sample_indexes != sorted(set(trace_sample_indexes))):
        raise ValueError("Nonmonotone phase/trace timing or changed source ownership")
    idle = buckets["idle_control"]
    a_prime = buckets["a_prime"]
    if len(idle) < 2 or len(a_prime) < 1:
        raise ValueError("No valid idle/A-only negative control")
    phase_counts = {k: len(v) for k, v in buckets.items()}
    missing_motion = [k for k in ("backswing", "forward_swing", "followthrough")
                      if not buckets[k]]
    missing_neutral_control = not buckets["trace_neutral"]
    rows_summary = []
    for idx in range(WORD_COUNT):
        baseline = idle[-1][idx]
        idle_stable = all(row[idx] == idle[0][idx] for row in idle)
        a_only_stable_and_equal = all(row[idx] == baseline for row in a_prime)
        neutral_stable_and_equal = (not missing_neutral_control and
            all(row[idx] == baseline for row in buckets["trace_neutral"]))
        flags = {}
        for phase in PHASES:
            samples = buckets[phase]
            flags[phase] = {
                "observed": bool(samples),
                "different_from_last_idle": any(row[idx] != baseline for row in samples),
                "changed_within_stage": len({row[idx] for row in samples}) > 1,
            }
        motion_specific_candidate = bool(
            idle_stable and a_only_stable_and_equal
            and neutral_stable_and_equal and not missing_motion
            and any(flags[k]["different_from_last_idle"]
                    for k in ("backswing", "forward_swing", "followthrough")))
        if (motion_specific_candidate or
                (idle_stable and any(x["different_from_last_idle"] for x in flags.values()))):
            offset = idx * 4
            rows_summary.append({
                "source_relative_offset": f"+0x{offset:03X}",
                "source_known_aim_overlap": offset in KNOWN_AIM_WORDS,
                "known_idle_confound_offset": offset == 0x90,
                "source_state_word_untyped": offset == 0x24,
                "idle_stable": idle_stable,
                "a_only_stable_and_equal_to_idle": a_only_stable_and_equal,
                "trace_neutral_stable_and_equal_to_idle": neutral_stable_and_equal,
                "motion_specific_candidate_not_verified": motion_specific_candidate,
                "phase_flags": flags,
            })
    rows_summary.sort(
        key=lambda item: (
            not item["motion_specific_candidate_not_verified"],
            item["source_known_aim_overlap"],
            item["known_idle_confound_offset"],
            item["source_relative_offset"],
        ))
    return {
        "kind": "local-offline-swing-selected-player-record-change-ranking",
        "schema_version": 1,
        "record_aligned_words_checked": WORD_COUNT,
        "source_record_size_bytes": 0xCC,
        "private_callback_samples": len(rows),
        "phase_sample_counts": phase_counts,
        "missing_motion_phases": missing_motion,
        "trace_neutral_control_observed": not missing_neutral_control,
        "chronological_bridge_stage_order_checked": True,
        "trace_sample_index_monotonic_checked": True,
        "source_selected_actor_stable": True,
        "bridge_tick_is_not_guest_applied_frame": True,
        "source_relative_candidate_offsets": rows_summary,
        "motion_specific_candidate_count_not_verified":
            sum(bool(x["motion_specific_candidate_not_verified"]) for x in rows_summary),
        "club_head_position_verified": False,
        "swing_velocity_verified": False,
        "swing_power_verified": False,
        "contact_or_ball_world_xyz_verified": False,
        "approved_for_training": False,
        "allowed_to_publish": False,
    }


def read_private_report(path: Path) -> dict:
    root = DATA_ROOT.resolve(strict=True)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing or linked private input")
    local = path.resolve(strict=True)
    if not local.is_relative_to(root) or not local.name.endswith("-PRIVATE.json"):
        raise ValueError("Private report outside ignored Data directory")
    if local.stat().st_size > 2_000_000:
        raise ValueError("Private report unexpectedly large")
    return json.loads(local.read_text(encoding="utf-8"))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-report", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        result = analyze(read_private_report(args.private_report))
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError, json.JSONDecodeError):
        print("PRIVATE swing-record analysis failed closed; no RAM values or paths printed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
