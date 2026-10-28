"""Offline gate for PRIVATE future selected-ball temporal observations.

This is NOT a Dolphin sampler, game controller, real-time monitor, publisher,
or proof of world XYZ. It consumes four *future* same-boot, frame-bracketed
records from S001's ONLY permitted single frame coroutine. Existing separate
GUI MEM1/MEM2 dumps are NOT eligible for this gate.

Raw three-word values and runtime pointers never leave the private input.
STDOUT contains only fixed aggregate booleans, counts and failure classes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

KIND = "private_s001_s002_ball_temporal_four_phase_v1"
EXPECTED_STAGES = ("idle_before", "idle_after", "event_before", "event_after")
EXPECTED_SOURCE = "same_felk_frame_coroutine"
EXPECTED_CONTRACT = "S002-160-selected-ball-start-rev1"
MEM2_BEGIN, MEM2_END = 0x90000000, 0x94000000
MAX_PRIVATE_BYTES = 131072
MAX_FRAME_SPAN = 2


def _is_u32(v) -> bool:
    return type(v) is int and 0 <= v <= 0xFFFFFFFF


def _three_words(v) -> tuple[int, int, int]:
    if type(v) is not list or len(v) != 3 or not all(_is_u32(x) for x in v):
        raise ValueError("expected three private u32 words")
    return tuple(v)


def _private_mem2_pointer(v) -> bool:
    return _is_u32(v) and v % 4 == 0 and MEM2_BEGIN <= v < MEM2_END


def _validated_samples(record: dict) -> list[dict]:
    if type(record) is not dict or set(record) != {
        "kind", "schema_version", "samples", "idle_no_action_observed",
        "human_ball_motion_observed", "human_contact_observed",
        "event_between_before_after_observed", "source_contract_id",
        "waveform_unmodified_attested"
    }:
        raise ValueError("unknown or missing private schema members")
    if (record["kind"] != KIND or record["schema_version"] != 1
            or record["source_contract_id"] != EXPECTED_CONTRACT):
        raise ValueError("unsupported private temporal record or source contract")
    if type(record["samples"]) is not list or len(record["samples"]) != 4:
        raise ValueError("four stages required")
    for key in ("idle_no_action_observed", "human_ball_motion_observed",
                "human_contact_observed", "event_between_before_after_observed",
                "waveform_unmodified_attested"):
        if type(record[key]) is not bool:
            raise ValueError("operator observation flags must be exact booleans")
    result = []
    expected_keys = {
        "stage", "boot_token", "game_id", "revision", "scene_id",
        "sport_id", "game_mode", "hole_index", "selected_record_index",
        "frame_start", "frame_end", "acquisition_source",
        "source_path_gates_passed", "selected_record_pointer",
        "ball_owner_pointer", "start_object_pointer", "selected_ball_vec",
        "current_start_vec", "record_pos_054_vec", "record_pos_060_vec",
    }
    for i, s in enumerate(record["samples"]):
        if type(s) is not dict or set(s) != expected_keys:
            raise ValueError("unknown or missing private sample fields")
        if s["stage"] != EXPECTED_STAGES[i] or s["acquisition_source"] != EXPECTED_SOURCE:
            raise ValueError("unapproved stage or read origin")
        if (type(s["boot_token"]) is not str or
                not 8 <= len(s["boot_token"]) <= 128):
            raise ValueError("missing session identity")
        if (s["game_id"] != "RSPE01" or type(s["revision"]) is not int
                or s["revision"] != 1
                or type(s["scene_id"]) is not int or s["scene_id"] != 5
                or type(s["sport_id"]) is not int or s["sport_id"] != 2
                or type(s["game_mode"]) is not int or s["game_mode"] != 4
                or type(s["hole_index"]) is not int
                or not 0 <= s["hole_index"] <= 17):
            raise ValueError("wrong game/scene/mode/hole")
        if (type(s["selected_record_index"]) is not int
                or not 0 <= s["selected_record_index"] <= 3
                or s["source_path_gates_passed"] is not True):
            raise ValueError("selected record or source gate not verified")
        if (type(s["frame_start"]) is not int
                or type(s["frame_end"]) is not int
                or s["frame_start"] < 0
                or not s["frame_start"] <= s["frame_end"]
                                  <= s["frame_start"] + MAX_FRAME_SPAN):
            raise ValueError("frame bracket too wide, missing, or reversed")
        if not all(_private_mem2_pointer(s[k]) for k in
                   ("selected_record_pointer", "ball_owner_pointer",
                    "start_object_pointer")):
            raise ValueError("unmapped or unaligned private pointer")
        for field in ("selected_ball_vec", "current_start_vec",
                      "record_pos_054_vec", "record_pos_060_vec"):
            _three_words(s[field])
        result.append(s)
    return result


def evaluate(record: dict) -> dict:
    """Never return raw values, addresses, boot token, absolute frames or path."""
    samples = _validated_samples(record)
    first = samples[0]
    same_boot_claimed = len({s["boot_token"] for s in samples}) == 1
    same_hole = len({s["hole_index"] for s in samples}) == 1
    chronological = all(
        left["frame_end"] < right["frame_start"]
        for left, right in zip(samples, samples[1:])
    )
    indices_stable = len({s["selected_record_index"] for s in samples}) == 1
    owner_stable = all(
        len({s[k] for s in samples}) == 1 for k in
        ("selected_record_pointer", "ball_owner_pointer",
         "start_object_pointer")
    )
    start_stable = all(
        _three_words(s["current_start_vec"]) ==
        _three_words(first["current_start_vec"]) for s in samples[1:]
    )
    idle_ball_stable = (
        _three_words(samples[0]["selected_ball_vec"]) ==
        _three_words(samples[1]["selected_ball_vec"])
    )
    before_event_same_as_idle = (
        _three_words(samples[1]["selected_ball_vec"]) ==
        _three_words(samples[2]["selected_ball_vec"])
    )
    event_changed_components = sum(
        a != b for a, b in zip(
            _three_words(samples[2]["selected_ball_vec"]),
            _three_words(samples[3]["selected_ball_vec"]))
    )
    selected_post = samples[3]
    post_matches_054 = (
        _three_words(selected_post["selected_ball_vec"]) ==
        _three_words(selected_post["record_pos_054_vec"])
    )
    post_matches_060 = (
        _three_words(selected_post["selected_ball_vec"]) ==
        _three_words(selected_post["record_pos_060_vec"])
    )
    no_shot_control = record["idle_no_action_observed"]
    human_motion = record["human_ball_motion_observed"]
    human_contact = record["human_contact_observed"]
    event_temporally_observed = record["event_between_before_after_observed"]
    trace_unmodified = record["waveform_unmodified_attested"]
    gates = {
        "all_four_source_gated_same_bridge_samples": True,
        "operator_claims_one_boot": same_boot_claimed,
        "same_source_hole_all_phases": same_hole,
        "strictly_ordered_emulated_frame_brackets": chronological,
        "source_selected_slot_index_stable": indices_stable,
        "selected_record_ball_and_start_pointer_stable": owner_stable,
        "source_start_translation_static": start_stable,
        "idle_control_selected_ball_static": idle_ball_stable,
        "event_prestate_matches_idle_baseline": before_event_same_as_idle,
        "operator_reports_no_action_in_idle_control": no_shot_control,
        "operator_reports_ball_movement": human_motion,
        "operator_reports_ball_contact": human_contact,
        "operator_reports_event_between_frame_brackets": event_temporally_observed,
        "baseline_waveform_unmodified_operator_attested": trace_unmodified,
        "selected_ball_words_changed_after_event": event_changed_components > 0,
    }
    status = ("provisional_motion_correlated_candidate"
              if all(gates.values()) else "abstain_inadequate_controls_or_provenance")
    return {
        "kind": "local_selected_ball_temporal_evidence_counts_only",
        "schema_version": 1,
        "result": status,
        "stage_count": len(samples),
        "emulated_frame_bracket_max_span": MAX_FRAME_SPAN,
        "changed_selected_ball_word_components_after_event":
            event_changed_components,
        "selected_ball_post_equals_record_054": post_matches_054,
        "selected_ball_post_equals_record_060": post_matches_060,
        "control_gates": gates,
        "same_boot_independently_verified": False,
        "human_observation_independently_verified": False,
        "physical_world_xyz_verified": False,
        "actual_ball_physics_object_verified": False,
        "recognized_swing_power_verified": False,
        "training_approved": False,
        "automatic_publication_approved": False,
        "warning": (
            "Only a provisional correlation of operator-labelled movement "
            "with a source-path candidate under one claimed boot. "
            "Frame-hook and human labels are not independently verified, "
            "and this cannot establish game physics, units, velocity or power."
        )
    }


def _safe_private_file(path: Path) -> Path:
    # All paths must reside in the ignored sibling Data, never a git worktree.
    data_root = (Path(__file__).resolve().parents[2] /
                 "Wii-AI-Golf-Data").resolve(strict=True)
    if not data_root.is_dir() or path.is_symlink() or not path.is_file():
        raise ValueError("missing private input")
    resolved = path.resolve(strict=True)
    if (not resolved.is_relative_to(data_root)
            or not 1 <= resolved.stat().st_size <= MAX_PRIVATE_BYTES):
        raise ValueError("private file size or location rejected")
    return resolved


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-json", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        path = _safe_private_file(args.private_json)
        report = evaluate(json.loads(path.read_text(encoding="utf-8")))
        print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError):
        print("Private temporal evidence gate stopped: invalid schema, "
              "provenance or ignored-Data file.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
