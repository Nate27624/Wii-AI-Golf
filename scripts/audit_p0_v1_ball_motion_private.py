"""Offline PRIVATE audit: does a source-selected V1 ball-vector candidate vary with one witnessed swing?

Strictly secondary to upstream S001 trace/link audit PR #193. This cannot prove
guest-frame synchrony, physical ball XYZ, velocity, power, contact or scoring.
Only categorical counts/booleans go to stdout. Never upload raw watched JSON.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import struct
import sys

DATA_ROOT_NAME = "Wii-AI-Golf-Data"
STAGES = ("idle_control", "a_prime", "trace", "posttrace")
PHASES = ("idle_control", "a_prime", "trace_neutral", "backswing",
          "forward_swing", "followthrough", "a_release", "posttrace")
MAX_FILE_BYTES = 2_000_000
RECORD_WORDS = 0xCC // 4
RECORD_POSITION_INDEX = 0x54 // 4
RECORD_START_COPY_INDEX = 0x60 // 4
READ_BUDGET_US = 5000


class Reject(Exception):
    """Reject private data without exposing values or file paths."""


def require(valid: bool) -> None:
    if not valid:
        raise Reject


def vector(value: object) -> tuple[float, float, float]:
    require(isinstance(value, list) and len(value) == 3)
    require(all(type(x) in (float, int) and math.isfinite(x)
                and abs(x) <= 100000 for x in value))
    return tuple(float(x) for x in value)


def unpack_three(words: list[int], start: int) -> tuple[float, float, float]:
    return tuple(struct.unpack(">f", struct.pack(">I", w))[0]
                 for w in words[start:start + 3])


def trace_phase(index: int) -> str:
    require(type(index) is int and 0 <= index < 89)
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
    require(isinstance(report, dict) and
            report.get("kind") == "PRIVATE-UNVERIFIED-selected-ball-frame-watch")
    status = report.get("watch_status")
    trace = report.get("bridge_trace_status")
    producer = report.get("safe_summary")
    timing = report.get("controller_timing")
    require(all(isinstance(x, dict) for x in (status, trace, producer, timing)))
    require(status.get("state") == "complete" and
            trace.get("state") == "complete" and trace.get("kind") == "swing" and
            type(trace.get("id")) is int and trace["id"] > 0 and
            type(trace.get("applied_frames")) is int and trace["applied_frames"] == 89 and
            type(trace.get("total_frames")) is int and trace["total_frames"] == 89)
    lead = timing.get("observed_A_lead")
    idle_timing = timing.get("idle")
    require(isinstance(lead, dict) and isinstance(idle_timing, dict))
    require(type(lead.get("observed_frame_delta")) is int and
            lead["observed_frame_delta"] >= 45 and
            lead.get("a_button_only_requests") == 1 and
            type(idle_timing.get("observed_idle_frame_delta")) is int and
            idle_timing["observed_idle_frame_delta"] >= 24)
    require(producer.get("swing_protocol_v1_source_checked") is True and
            producer.get("watch_complete") is True and
            producer.get("source_selected_slot_stable") is True and
            producer.get("source_hole_stable") is True and
            producer.get("source_owner_consistency_checks_passed") is True and
            producer.get("read_performance_checks_passed") is True and
            producer.get("a_lead_observed_frames", 0) >= 45 and
            producer.get("trace_sha256") and
            producer.get("contact_and_movement_are_separate_human_labels") is True)
    contact = report.get("operator_contact_human")
    movement = report.get("operator_observation")
    require(contact in ("yes", "no", "unknown") and
            movement in ("yes", "no", "unknown") and
            producer.get("contact_human") == contact and
            producer.get("human_observed_ball_movement") == movement)
    rows = report.get("PRIVATE_UNVERIFIED_NUMERIC_VECTORS")
    require(isinstance(rows, list) and 2 <= len(rows) <= 80)
    if "samples" in status:
        require(type(status["samples"]) is int and status["samples"] == len(rows))

    counts: Counter[str] = Counter()
    unique_slots, holes = set(), set()
    ticks, stages, indexes = [], [], []
    start_vectors, idle_vectors, lead_vectors, neutral_vectors = [], [], [], []
    back_vectors, forward_vectors, follow_vectors, release_vectors = [], [], [], []
    post_vectors, record_vectors, record_start_copies, ball_vectors = [], [], [], []
    record_vec_word_mismatch = 0
    early_shift = False
    for row in rows:
        require(isinstance(row, dict))
        words = row.get("selected_player_record_words_PRIVATE")
        require(isinstance(words, list) and len(words) == RECORD_WORDS and
                all(type(w) is int and 0 <= w <= 0xFFFFFFFF for w in words))
        tick = row.get("frame_tick_index")
        slot, hole = row.get("selected_slot_candidate"), row.get("source_hole_index")
        budget = row.get("read_overhead_us")
        stage = row.get("input_stage")
        idx, active_id = row.get("trace_sample_index_if_active"), row.get("trace_id_if_active")
        require(type(tick) is int and tick >= 0 and
                type(slot) is int and 0 <= slot < 4 and
                type(hole) is int and 0 <= hole <= 8 and
                type(budget) is int and 0 <= budget <= READ_BUDGET_US and
                stage in STAGES and row.get("source_owner_consistent") is True)
        ticks.append(tick)
        stages.append(STAGES.index(stage))
        unique_slots.add(slot)
        holes.add(hole)
        source_ball = vector(row.get("ball_translation_f32_candidate"))
        reported_record = vector(row.get("record_translation_f32_candidate"))
        start = vector(row.get("current_start_f32_candidate"))
        from_words = unpack_three(words, RECORD_POSITION_INDEX)
        start_copy = unpack_three(words, RECORD_START_COPY_INDEX)
        require(all(math.isfinite(x) and abs(x) <= 100000
                    for x in from_words + start_copy))
        # A complete record must agree with the same sample's record +0x54.
        # For NaN/-0 signed-zero safety, compare actual binary f32 bits.
        if any(struct.pack(">f", x) != struct.pack(">f", y)
               for x, y in zip(from_words, reported_record)):
            record_vec_word_mismatch += 1
        start_vectors.append(start)
        ball_vectors.append(source_ball)
        record_vectors.append(reported_record)
        record_start_copies.append(start_copy)
        if stage == "trace":
            require(type(idx) is int and 0 <= idx < 89 and
                    type(active_id) is int and active_id == trace["id"])
            indexes.append(idx)
            phase = trace_phase(idx)
        else:
            require(idx is None and active_id is None)
            phase = stage
        counts[phase] += 1
        groups = {
            "idle_control": idle_vectors, "a_prime": lead_vectors,
            "trace_neutral": neutral_vectors, "backswing": back_vectors,
            "forward_swing": forward_vectors, "followthrough": follow_vectors,
            "a_release": release_vectors, "posttrace": post_vectors,
        }
        groups[phase].append(source_ball)
    require(ticks == sorted(set(ticks)) and
            stages == sorted(stages) and indexes == sorted(set(indexes)) and
            len(unique_slots) == 1 and len(holes) == 1 and
            record_vec_word_mismatch == 0)
    missing = [name for name in PHASES if counts[name] == 0]
    idle_stable = len(idle_vectors) >= 2 and len(set(idle_vectors)) == 1
    lead_stable = bool(idle_stable and lead_vectors and
                       all(x == idle_vectors[0] for x in lead_vectors))
    neutral_stable = bool(lead_stable and neutral_vectors and
                          all(x == idle_vectors[0] for x in neutral_vectors))
    backswing_stable = bool(neutral_stable and back_vectors and
                            all(x == idle_vectors[0] for x in back_vectors))
    tee_stable = len(set(start_vectors)) == 1
    record_start_copy_stable = len(set(record_start_copies)) == 1
    movement_phases = ("forward_swing", "followthrough", "a_release", "posttrace")
    changes = {phase: sum(v != idle_vectors[0] for v in values)
               for phase, values in (
                   ("forward_swing", forward_vectors),
                   ("followthrough", follow_vectors),
                   ("a_release", release_vectors),
                   ("posttrace", post_vectors),
               )} if idle_vectors else {x: 0 for x in movement_phases}
    moving_samples = sum(changes.values())
    early_shift = (not idle_stable or not lead_stable or
                   not neutral_stable or not backswing_stable)
    complete = not missing and tee_stable and not early_shift
    candidate = bool(complete and moving_samples > 0 and
                     sum(changes[x] for x in ("forward_swing", "followthrough")) > 0 and
                     contact == "yes" and movement == "yes")
    return {
        "kind": "P0-OFFLINE-V1-SOURCE-BALL-MOTION-EVIDENCE",
        "schema_version": 1,
        "observed_A_lead_at_least_45_frames": True,
        "completed_controller_trace_89_of_89": True,
        "trace_id_matches_all_active_watch_samples": True,
        "sample_count": len(rows),
        "source_selected_slot_and_hole_stable": True,
        "source_record_plus_0x54_words_match_reported_vector": True,
        "record_start_copy_stable": record_start_copy_stable,
        "source_current_start_stable": tee_stable,
        "sample_counts_per_phase": {phase: counts[phase] for phase in PHASES},
        "missing_phases": missing,
        "idle_a_only_neutral_and_backswing_stable": not early_shift,
        "ball_candidate_changed_samples_after_forward_start": moving_samples,
        "changed_samples_by_late_phase": changes,
        "human_contact": contact,
        "human_observed_ball_movement": movement,
        "source_ball_vector_correlated_with_observed_swing_not_physics_verified": candidate,
        "source_ball_cache_cc_f0_fc_sampled": False,
        "same_guest_physics_frame_verified": False,
        "actual_ball_world_xyz_verified": False,
        "actual_ball_velocity_xyz_verified": False,
        "collision_frame_verified": False,
        "shot_power_verified": False,
        "game_score_or_distance_verified": False,
        "approved_for_training": False,
        "github_upload": "NOT_UPLOADED_PRIVATE",
    }


def read_private(path: Path, data_root: Path) -> dict:
    require(data_root.is_dir() and not data_root.is_symlink() and
            data_root.name == DATA_ROOT_NAME)
    require(path.is_file() and not path.is_symlink() and
            path.name.endswith("-PRIVATE.json") and
            path.resolve().is_relative_to(data_root.resolve()) and
            path.stat().st_size <= MAX_FILE_BYTES)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--private-report", type=Path, required=True)
    ap.add_argument("--data-root", type=Path,
                    default=Path(__file__).resolve().parents[2] / DATA_ROOT_NAME)
    args = ap.parse_args(argv)
    try:
        result = audit(read_private(args.private_report, args.data_root))
    except (Reject, OSError, TypeError, ValueError, KeyError, OverflowError,
            struct.error, json.JSONDecodeError):
        print("P0 V1 source-ball offline evidence ABORT: invalid private provenance or source record.", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
