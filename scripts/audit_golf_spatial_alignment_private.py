"""Private S002 intra-MEM2 coordinate relationship controls, one still pair.

Reuses source/scene/selector/ball/start PPC gates from #160/#163.
Only scalar equality and finite checks. Source-labelled map objects may be
render objects. X/Z axes, Y height, coordinate units and physics unverified.
No new capture, Dolphin/RPC/controller, broad scanning or publication.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_start_link_private as link


def analyze_one(read_u32, header: bytes) -> dict:
    baseline, private = link.analyze_one(read_u32, header)
    if not all(baseline[k] for k in (
        "source_current_start_constructor_selfrefs_match",
        "selected_ball_translation_pointer_selfref_matches_base",
        "record_candidate_triplet_finite_bounded",
        "nested_ball_candidate_triplet_finite_bounded",
        "source_current_start_triplet_finite_bounded",
    )):
        raise ValueError("source-selected start/ball constructor or bounded vec failed")
    field = read_u32(roster.GOLF_FIELD_STATIC)
    if roster._bank(field, 0xA8) != "MEM2":
        raise ValueError("source field missing")
    # These specific offsets are declared in public RPGolFieldManager.h.
    # The objects' +0x4C internal translation self-pointer is source-backed
    # by RPGolMapObjBase PPC ctor, but class type is not yet fully proven.
    def map_vec(offset):
        obj = read_u32(field + offset)
        if roster._bank(obj, 0x50) != "MEM2":
            raise ValueError("missing source-labelled map object")
        vec = read_u32(obj + 0x4C)
        if vec != obj + 0x30:
            raise ValueError("map-object translation constructor selfref mismatch")
        words = link._triplet(read_u32, vec)
        if not link._finite_bounded(words):
            raise ValueError("non-finite/out-of-bounds candidate map vector")
        return words

    pin = map_vec(0x44)
    cup = map_vec(0x54)
    tee = map_vec(0x2C)
    start = private["start"]
    selected_ball = private["ball"]
    pm = read_u32(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    selected_slot = private["selected_index"]
    if not (type(selected_slot) is int and selected_slot in range(4)):
        raise ValueError("selected slot not source-proven")
    inactive = []
    for i in range(roster.ROSTER_SLOTS):
        if i == selected_slot:
            continue
        record = pm + 4 + i * roster.ROSTER_STRIDE
        child = read_u32(record + 0x88)
        if (roster._bank(child, 0x50) != "MEM2"
                or not roster._in_data(read_u32(child), roster.BALL_DATA)):
            raise ValueError("nonselected child object source-data region mismatch")
        dest = read_u32(child + 0x4C)
        if dest != child + 0x30:
            raise ValueError("nonselected child translation selfref mismatch")
        words = link._triplet(read_u32, dest)
        if not link._finite_bounded(words):
            raise ValueError("non-finite nonselected candidate vector")
        inactive.append(words)

    def count_equal(a, b):
        return sum(x == y for x, y in zip(a, b))

    return {
        "kind": "local-private-selected-map-object-spatial-alignment",
        "schema_version": 1,
        "game_id": "RSPE01", "disc_revision": 1, "source_mode": 4,
        "selected_record_relative_index": selected_slot,
        "all_source_scene_roster_and_vector_gates_passed": True,
        "all_map_object_translation_selfpointers_match": True,
        "all_checked_vectors_finite_and_bounded": True,
        "same_MEM2_bank_comparison_only": True,
        "pin_vs_cup_component_equal_mask": [
            pin[i] == cup[i] for i in range(3)
        ],
        "pin_cup_first_and_third_components_bitwise_equal":
            pin[0] == cup[0] and pin[2] == cup[2],
        "pin_cup_middle_component_bitwise_different": pin[1] != cup[1],
        "selected_ball_vs_start_equal_component_count":
            count_equal(selected_ball, start),
        "selected_ball_and_start_all_three_words_equal":
            selected_ball == start,
        "three_nonselected_ball_objects_all_triplets_equal":
            len(inactive) == 3 and len(set(inactive)) == 1,
        "nonselected_ball_objects_matching_current_start_full_triplet":
            sum(v == start for v in inactive),
        "tee_vs_pin_equal_component_count": count_equal(tee, pin),
        "tee_vs_start_equal_component_count": count_equal(tee, start),
        "same_emulated_frame_MEM1_MEM2_verified": False,
        "pin_cup_are_true_physical_landmarks_verified": False,
        "coordinate_axis_convention_verified": False,
        "distance_units_verified": False,
        "ball_world_xyz_or_motion_verified": False,
        "record_index_is_active_human_verified": False,
        "approved_for_training": False,
        "allowed_to_publish": False,
        "warning": (
            "Intra-MEM2 positional agreement is a single still-snapshot "
            "source-structure relationship, not independently verified "
            "world coordinates, units, course distances, active-ball motion "
            "or same-frame MEM1+MEM2 provenance."
        )
    }


def run_local(first_dir: Path) -> dict:
    root = link.DATA_ROOT.resolve(strict=True)
    if first_dir.is_symlink() or not first_dir.is_dir():
        raise ValueError("private native pair directory unavailable")
    folder = first_dir.resolve(strict=True)
    if not folder.is_relative_to(root):
        raise ValueError("private pair outside ignored data root")
    p1 = link._approved_bank(folder / "mem1.raw", root, roster.MEM1_SIZE)
    p2 = link._approved_bank(folder / "mem2.raw", root, roster.MEM2_SIZE)
    with ExitStack() as stack:
        f1 = stack.enter_context(p1.open("rb"))
        f2 = stack.enter_context(p2.open("rb"))
        b1 = stack.enter_context(mmap.mmap(f1.fileno(), 0, access=mmap.ACCESS_READ))
        b2 = stack.enter_context(mmap.mmap(f2.fileno(), 0, access=mmap.ACCESS_READ))
        reader = roster.TwoBankReader(b1, b2)
        return analyze_one(reader.u32, reader.header())


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--first-dir", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        out = run_local(args.first_dir)
    except (OSError, ValueError, TypeError, OverflowError):
        print("Private pin/cup/ball geometry source gate refused. "
              "No memory words, paths or runtime addresses disclosed.",
              file=sys.stderr)
        return 1
    print(json.dumps(out, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
