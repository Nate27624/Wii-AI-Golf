#!/usr/bin/env python3
"""Private, read-only 25-P0 Rev1 seven-pair differential; NOT a physics reader.

Uses existing original archive SHA, PPC, scene, selected-owner and source-global
readers; never scans arbitrary memory. Output is intentionally nonpublishable.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
import os
from pathlib import Path
import stat
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) in sys.path:
    sys.path.remove(str(HERE))
sys.path.insert(0, str(HERE))

P0_IDS = (
    "scene.current_id", "golf.main_ptr", "golf.tee_start.map_translation_xyz",
    "golf.pin.map_translation_xyz", "golf.cup.map_translation_xyz", "golf.ball.world_xyz",
    "golf.player.selected_record.initial_position_candidate",
    "golf.player.selected_record.start_copy_candidate",
    "golf.ball_object.current_translation_candidate",
    "golf.ball_object.initialized_cache_cc", "golf.ball_object.conditional_cache_f0",
    "golf.ball_object.conditional_cache_fc",
    "golf.player.selected_record.aim_rotation",
    "golf.ball.source_global_translation_candidate",
    "golf.ball_object.cache_f0_update_tag_118",
    "golf.ball_object.cache_fc_update_tag_11c",
    "golf.config.standard_scores_table_4x9",
    "golf.player.selected_record.scalar_030",
    "golf.player.selected_record.scalar_090",
    "golf.sequence_mgr.golf_scores_hole_major_9x4",
    "golf.player.selected_record.stroke_count_source_candidate",
    "golf.config.mode_selector_094_source_candidate",
    "golf.config.current_hole_index_098_source_candidate",
    "golf.wind.hole_direction_table_source_candidate",
    "golf.wind.hole_speed_table_source_candidate",
)
# Source-qualified named offsets only, never broad scans. Raw words stay local.
FIELDS = {
    "golf.tee_start.map_translation_xyz": "source_current_start",
    "golf.pin.map_translation_xyz": "pin",
    "golf.player.selected_record.initial_position_candidate": "record_0x054",
    "golf.player.selected_record.start_copy_candidate": "record_0x060",
    "golf.ball_object.current_translation_candidate": "ball_object_0x030",
    "golf.ball_object.initialized_cache_cc": "ball_cache_0x0cc",
    "golf.ball_object.conditional_cache_f0": "ball_cache_0x0f0",
    "golf.ball_object.conditional_cache_fc": "ball_cache_0x0fc",
    "golf.player.selected_record.aim_rotation": "aim_word",
    "golf.ball_object.cache_f0_update_tag_118": "tag_118",
    "golf.ball_object.cache_fc_update_tag_11c": "tag_11c",
    "golf.config.standard_scores_table_4x9": "standard_score_table",
    "golf.player.selected_record.scalar_030": "scalar_030",
    "golf.player.selected_record.scalar_090": "scalar_090",
    "golf.sequence_mgr.golf_scores_hole_major_9x4": "sequence_score_table",
    "golf.player.selected_record.stroke_count_source_candidate": "stroke_word",
    "golf.config.mode_selector_094_source_candidate": "mode_word",
    "golf.config.current_hole_index_098_source_candidate": "hole_word",
    "golf.ball.source_global_translation_candidate": "global_current",
}
# These three roots do not have a sufficiently gated archive source reader here.
NOT_MEASURED = {
    "golf.cup.map_translation_xyz", "golf.ball.world_xyz",
    "golf.wind.hole_direction_table_source_candidate",
    "golf.wind.hole_speed_table_source_candidate",
}
EDGES = ((5, 6), (6, 7), (5, 7))
SOURCE_FIRST = {
    "golf.cup.map_translation_xyz", "golf.wind.hole_direction_table_source_candidate",
    "golf.wind.hole_speed_table_source_candidate",
    "golf.sequence_mgr.golf_scores_hole_major_9x4",
    "golf.player.selected_record.stroke_count_source_candidate",
    "golf.config.mode_selector_094_source_candidate",
    "golf.config.current_hole_index_098_source_candidate",
}
HIGH_PRIORITY = {
    "golf.ball.world_xyz", "golf.ball_object.current_translation_candidate",
    "golf.ball.source_global_translation_candidate",
}


def registry_entries(registry: dict) -> list[dict]:
    if type(registry) is not dict or registry.get("schema_version") != 1:
        raise ValueError("untrusted registry schema")
    variables = registry.get("variables")
    if type(variables) is not list:
        raise ValueError("missing registry variable list")
    p0 = [v for v in variables if type(v) is dict and v.get("priority") == "P0"]
    names = [v.get("id") for v in p0]
    if len(names) != 25 or len(set(names)) != 25 or set(names) != set(P0_IDS):
        raise ValueError("P0 registry IDs changed; fail closed")
    for v in p0:
        loc = v.get("memory_locator")
        if not isinstance(loc, dict) or not isinstance(loc.get("kind"), str):
            raise ValueError("invalid registered locator")
        controls = v.get("required_controls")
        if type(controls) is not list or not all(isinstance(x, str) for x in controls):
            raise ValueError("unqualified source witness")
        if v.get("status") not in registry.get("status_vocabulary", []):
            raise ValueError("unqualified registry status")
    return p0


def _bits_changed(left: tuple, right: tuple) -> int:
    if not isinstance(left, tuple) or not isinstance(right, tuple) or len(left) != len(right):
        raise ValueError("incompatible typed word dimensions")
    if not left or any(type(w) is not int or not 0 <= w <= 0xFFFFFFFF for w in left + right):
        raise ValueError("invalid big-endian word candidate")
    return sum(a != b for a, b in zip(left, right))


def _overlap(a: int, length_a: int, b: int, length_b: int) -> bool:
    return max(a, b) < min(a + length_a, b + length_b)


def _qualify_wedge(samples: dict) -> None:
    if set(samples) != set(range(1, 8)):
        raise ValueError("original seven numbered phases required")
    for before, after in EDGES:
        x, y = samples[before], samples[after]
        if any(x[k] != y[k] for k in (
            "selected_index", "hole", "selected_ball_obj", "pin_obj",
            "start_obj", "field", "cfg_bc", "cfg_c0", "cfg_c4",
        )):
            raise ValueError("wedge owner/scene identity changed")
        if x["mode_word"] != y["mode_word"] or x["hole_word"] != y["hole_word"]:
            raise ValueError("wedge config mode/hole identity changed")
    for sample in samples.values():
        if sample.get("source_gate") is not True or sample.get("scene_gate") is not True:
            raise ValueError("Rev1 source/scene gate unqualified")


def matrix(registry: dict, samples: dict[int, dict]) -> dict:
    """Pure synthetic-testable analysis; input words/pointers NEVER serialized."""
    entries = registry_entries(registry)
    _qualify_wedge(samples)
    d1_equal = _bits_changed(samples[1]["ball_object_0x030"],
                             samples[1]["source_current_start"]) == 0
    rows = []
    for v in entries:
        id_ = v["id"]
        key = FIELDS.get(id_)
        measured = key is not None and all(isinstance(samples[n].get(key), tuple) for n in range(1, 8))
        counts = [_bits_changed(samples[a][key], samples[b][key]) for a, b in EDGES] if measured else []
        if id_ in ("scene.current_id", "golf.main_ptr"):
            observed = "source_gate_passed_not_dynamic_field_verification"
        elif id_ == "golf.ball.world_xyz":
            observed = "unresolved_no_rendered_ball_locator"
        elif key == "global_current" and not measured:
            observed = "source_global_gate_unavailable"
        elif measured:
            observed = "candidate_changed" if any(counts) else "candidate_stable_control"
        else:
            observed = "not_source_measured_in_this_reader"
        c = v.get("required_controls", [])
        source_confidence = v.get("evidence", {}).get("source_confidence", "unspecified")
        if not isinstance(source_confidence, str):
            raise ValueError("malformed source confidence")
        # This is a source/archival state, NOT runtime verification or a new registry promotion.
        row = {
            "id": id_, "registered_status": v["status"],
            "proposed_source_locator": v["memory_locator"].get("expression"),
            "locator_kind": v["memory_locator"]["kind"],
            "source_owner_confidence": source_confidence,
            "archive_observation": observed,
            "wedge_5_6_6_7_5_7_changed_word_counts": counts,
            "stationary_negative_control": "wedge_PIN_and_START_categorical_comparison",
            "independent_no_input_control": "not_available_no_A_and_A_held_are_different_poses",
            "supports_candidate_temporal_change_only": observed == "candidate_changed",
            "contradictory_evidence": [],
            "new_capture": "source_witness_first" if id_ in SOURCE_FIRST else "required_for_semantic_verification",
            "next_source_or_capture_witness": c[0] if c else "independent source writer and exact same-shot visual/frame control",
            "priority": 1 if id_ in HIGH_PRIORITY else (2 if measured else 3),
            "physical_or_rendered_ball_verified": False,
            "same_guest_physics_frame_verified": False,
            "training_approved": False,
        }
        if d1_equal and key in ("ball_object_0x030", "global_current", "ball_cache_0x0cc", "ball_cache_0x0f0", "ball_cache_0x0fc"):
            row["contradictory_evidence"].append("D1_human_airborne_selected_equals_START_unverified_mapping")
        if key in ("ball_object_0x030", "global_current"):
            row["contradictory_evidence"].append("global_source_distinct_from_all_roster_7_of_7_historical_only")
        rows.append(row)
    # Preserve both independent negative controls, including a confounded PIN if seen.
    wedge_pin_counts = [_bits_changed(samples[a]["pin"], samples[b]["pin"]) for a,b in EDGES]
    wedge_start_counts = [_bits_changed(samples[a]["source_current_start"], samples[b]["source_current_start"]) for a,b in EDGES]
    if any(wedge_pin_counts) or any(wedge_start_counts):
        for row in rows:
            if row["id"] in HIGH_PRIORITY:
                row["contradictory_evidence"].append("wedge_reference_geometry_changed_confounded")
                row["supports_candidate_temporal_change_only"] = False
    return {
        "kind": "p0-private-archive-variable-differential", "schema_version": 1,
        "status": "source_gated_archive_candidates_only", "number_of_p0_rows": len(rows),
        "p0_rows": rows, "control_summary": {
            "wedge_pin_changed_counts": wedge_pin_counts,
            "wedge_tee_changed_counts": wedge_start_counts,
            "D1_selected_current_equals_start": d1_equal,
            "D1_operator_airborne_annotation_independently_confirmed": False,
            "W5_W7_same_shot_guest_frame_verified": False,
            "W5_W7_object_pointer_equality_does_not_prove_generation": True,
        },
        "absence_from_registry": ["verified_power", "verified_impact_frame", "verified_velocity", "verified_result_distance"],
        "native_sha_pre_post_checked_by_existing_reader": False,
        "same_boot_verified": False, "rendered_actor_verified": False,
        "game_mode_hole_across_new_boot_verified": False,
        "training_approved": False, "allowed_to_publish": False,
    }


def _read_one(rd, seven, glob, roster) -> dict:
    """Read only named source candidates after canonical Rev1/owner gates."""
    s = seven._get(rd)
    u = rd.u32
    config = u(roster.GOLF_CONFIG_STATIC)
    if roster._bank(config, 0xC8) != "MEM2":
        raise ValueError("config identity failed")
    pm = u(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    rec = pm + 4 + s["selected_index"] * roster.ROSTER_STRIDE
    ball = s["selected_ball_obj"]
    if roster._bank(ball, 0x1AC) != "MEM2":
        raise ValueError("selected inline ball allocation incomplete")
    s.update({"source_gate": True, "scene_gate": True,
        "mode_word": (u(config + 0x94),), "hole_word": (u(config + 0x98),),
        "aim_word": (s["whole_record"][0x3C // 4],),
        "scalar_030": (s["whole_record"][0x30 // 4],),
        "scalar_090": (s["whole_record"][0x90 // 4],),
        "stroke_word": (s["whole_record"][0x78 // 4],),
        "tag_118": (u(ball + 0x118),), "tag_11c": (u(ball + 0x11C),),
        "standard_score_table": tuple(u(config + 0x04 + 4*i) for i in range(36)),
    })
    for name in ("ball_object_0x030", "ball_cache_0x0cc", "ball_cache_0x0f0",
                 "ball_cache_0x0fc", "record_0x054", "record_0x060", "source_current_start"):
        s[name] = tuple(s["triplets"][name])
    s["pin"] = tuple(s["pin"])
    # A separately source-gated static r13 global load and 4-slot membership.
    # Treat any missing code, bad pointer or intersecting allocation as ABSTAIN.
    import audit_p0_cache_global_receiver_private as global_reader
    import audit_p0_global_ball_roster_receiver_private as global_roster
    p = global_reader.source_global_slot(u)
    if not p["static_source_global_slot_supported"]:
        raise ValueError("source-global PPC load unqualified")
    shaped = {"refs": {"ball": ball}, "selected_index": s["selected_index"],
              "triplets": {"ball_nested_plus_0x4c": s["ball_object_0x030"],
                           "ball_cache_0x0cc": s["ball_cache_0x0cc"],
                           "source_current_start": s["source_current_start"]}}
    runtime = global_reader.sample_runtime(u, shaped, p)
    if runtime.get("supported") is not True:
        raise ValueError("source-global receiver runtime unqualified")
    gp = runtime["_private_runtime_source_global_pointer"]
    member = global_roster.roster_global_membership(u,
        {"selected_index": s["selected_index"], "refs": {"ball": ball}}, gp)
    if not member["global_matches_exactly_zero_player_slots"]:
        raise ValueError("source-global aliases selected/inactive roster")
    if any(_overlap(gp, 0x50, ptr, 0x1AC) for ptr in member["_private_roster_ball_pointers"]):
        raise ValueError("global and roster allocations overlap")
    s["global_current"] = tuple(runtime["_private_runtime_global_current_words"])
    s["_global_identity_private"] = gp  # intentionally never serialized
    # The sequence-score source consumer/type is not yet verified by this reader.
    return s


def analyze(archive: Path, registry_path: Path | None = None) -> dict:
    import audit_p0_seven_numbered_source_pairs_private as seven
    roster = seven.roster
    registry_file = registry_path or ROOT / "research" / "memory-variables" / "registry.json"
    registry = json.loads(registry_file.read_text(encoding="utf-8"))
    registry_entries(registry)
    # Existing original 14-bank size/SHA/source privacy contract. No fallback paths.
    folders = seven._check_archive(archive)
    samples = {}
    try:
        for n in range(1, 8):
            with ExitStack() as stack:
                banks = []
                for bank, size in enumerate(seven.SIZE, 1):
                    path = seven.src._file(folders[n], f"{n}.{bank}.raw", size)
                    before = path.lstat()
                    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
                    fd = os.open(path, flags)
                    stack.callback(os.close, fd)
                    opened = os.fstat(fd)
                    if (not stat.S_ISREG(opened.st_mode) or
                        (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) !=
                        (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)):
                        raise ValueError("native pair file identity changed")
                    mm = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
                    stack.callback(mm.close)
                    banks.append(mm)
                samples[n] = _read_one(roster.TwoBankReader(*banks), seven, None, roster)
        # Check unchanged sources and object lifetime within operator-labeled wedge.
        for a,b in EDGES:
            if samples[a]["_global_identity_private"] != samples[b]["_global_identity_private"]:
                raise ValueError("source-global pointer changed during wedge")
        result = matrix(registry, samples)
    finally:
        # Original SHA check also runs if a read fails; errors never expose paths.
        seven._check_archive(archive)
    result["native_sha_pre_post_checked_by_existing_reader"] = True
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = analyze(args.archive)
    except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError, AttributeError):
        print(json.dumps({"kind": "p0-private-archive-variable-differential",
                          "status": "ABSTAIN", "reason_code": "source_archive_or_identity_gate_failed",
                          "training_approved": False, "allowed_to_publish": False}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
