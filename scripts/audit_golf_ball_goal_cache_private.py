"""S002 local-only PPC callgraph + source-labelled goal-position cache check.

Uses existing S002 #160/#163 source/scene/selected-ball input gates. It reads
the *already captured* native US RSPE01 Rev1 private MEM1/MEM2 pair, never
starts Dolphin, scans arbitrary RAM, performs RPC or writes a result.

PPC source locations are public research offsets; memory words, heap pointers,
exact float values, source code bytes, and local paths are NEVER emitted.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_start_link_private as selected

# Offsets within RPGolFieldManager, see kiwi515/ogws_info header.
TARGET_COUNT_MEMBER = 0x30
CURRENT_PIN_MEMBER = 0x44
MAP_TRANSLATION_MEMBER = 0x4C
CACHE_TRIPLES = (0xCC, 0xF0, 0xFC)


def _bc_to(read, pc: int, target: int) -> bool:
    return roster._relative_branch_target(pc, read(pc), 16) == target


def _b_to(read, pc: int, target: int) -> bool:
    return roster._relative_branch_target(pc, read(pc), 18) == target


def source_goal_and_cache_checks(read) -> dict:
    """Verify exact Rev1 field-member, register, branch and float copy shapes.

    This proves static *source dataflow*, not invocation or which instance
    was receiver in a particular capture. Code can also contain paths
    never visited in training mode.
    """
    getter = all((
        roster._dform_matches(read, 0x80292294, 32, 0, 3, TARGET_COUNT_MEMBER),
        roster._dform_matches(read, 0x80292298, 11, 0, 0, 0),
        _bc_to(read, 0x8029229C, 0x802922A8),
        roster._dform_matches(read, 0x802922A0, 32, 3, 3, 0x34),
        _b_to(read, 0x802922A4, 0x802B6F24),
        roster._dform_matches(read, 0x802922A8, 32, 3, 3, CURRENT_PIN_MEMBER),
        roster._dform_matches(read, 0x802922AC, 32, 3, 3, MAP_TRANSLATION_MEMBER),
    ))
    # 0x80299C70 receives a destination r3 -> r27. Its dynamic refresh
    # pulls source-global ball +0x4C vec and writes r27+0xCC..D4.
    refreshed = (
        roster._mr_matches(read, 0x80299C90, 27, 3)
        and roster._dform_matches(read, 0x80299CD4, 32, 3, 3, 0x4C)
        and all(
            roster._dform_matches(read, loadpc, 48, 0, 3, j * 4)
            and roster._dform_matches(read, storepc, 52, 0, 27, 0xCC + j * 4)
            for j, (loadpc, storepc) in enumerate((
                (0x80299CD8, 0x80299CDC),
                (0x80299CE0, 0x80299CE4),
                (0x80299CE8, 0x80299CEC),
            ))
        )
    )
    goal_proximity = all((
        roster._dform_matches(read, 0x80299EE4, 32, 3, 13, -23320),
        roster._bl_matches(read, 0x80299EE8, 0x80292294),
        roster._dform_matches(read, 0x80299EEC, 48, 4, 27, 0xD4),
        roster._dform_matches(read, 0x80299EF0, 48, 1, 3, 8),
        roster._dform_matches(read, 0x80299EF4, 48, 0, 27, 0xF8),
        roster._dform_matches(read, 0x80299EFC, 48, 3, 27, 0xCC),
        roster._dform_matches(read, 0x80299F04, 48, 2, 3, 0),
        roster._dform_matches(read, 0x80299F08, 48, 0, 27, 0xF0),
        _bc_to(read, 0x80299F38, 0x80299F54),
        roster._dform_matches(read, 0x80299F44, 52, 3, 27, 0xF0),
        roster._dform_matches(read, 0x80299F48, 52, 0, 27, 0xF4),
        roster._dform_matches(read, 0x80299F4C, 52, 4, 27, 0xF8),
        roster._dform_matches(read, 0x80299F60, 48, 1, 27, 0xD0),
        roster._dform_matches(read, 0x80299F64, 48, 0, 27, 0x100),
        _bc_to(read, 0x80299F6C, 0x80299F90),
        roster._dform_matches(read, 0x80299F80, 52, 2, 27, 0xFC),
        roster._dform_matches(read, 0x80299F84, 52, 1, 27, 0x100),
        roster._dform_matches(read, 0x80299F88, 52, 0, 27, 0x104),
    ))
    # Ensure the two planar comparison chains are actual floating point
    # subtract and square/add operations, not merely offset coincidences.
    planar_math = all(
        read(pc) >> 26 == 59
        for pc in (
            0x80299EF8, 0x80299F00, 0x80299F0C, 0x80299F10,
            0x80299F18, 0x80299F1C, 0x80299F24, 0x80299F2C,
        )
    )
    return {
        "field_goal_getter_target_else_pin_source_supported": getter,
        "ball_unit_global_position_to_cc_cache_copy_source_supported":
            refreshed,
        "conditional_f0_and_fc_candidate_cache_writers_source_supported":
            goal_proximity,
        "planar_first_third_component_squared_difference_math_source_supported":
            planar_math,
        "all_required_static_source_evidence": (
            getter and refreshed and goal_proximity and planar_math
        ),
        "source_callee_receiver_is_selected_ball_runtime_object_verified":
            False,
        "cache_semantics_as_real_shot_distance_or_score_verified": False,
    }


def analyze_one(read_u32, header):
    # Base #163 source and selected-record owner checks, including all
    # trusted Rev1 scene/config/ball/current-start provenance.
    safe, private = selected.analyze_one(read_u32, header)
    checks = source_goal_and_cache_checks(read_u32)
    if not checks["all_required_static_source_evidence"]:
        raise ValueError("source goal or ball-cache register/branch chain failed")

    field = read_u32(roster.GOLF_FIELD_STATIC)
    if roster._bank(field, 0x50) != "MEM2":
        raise ValueError("Golf field source identity absent")
    target_count = read_u32(field + TARGET_COUNT_MEMBER)
    if type(target_count) is not int or target_count > 256:
        raise ValueError("target-object count candidate outside safe range")
    pin = read_u32(field + CURRENT_PIN_MEMBER)
    if roster._bank(pin, 0x50) != "MEM2":
        raise ValueError("current source pin pointer absent")
    pin_translation_ptr = read_u32(pin + MAP_TRANSLATION_MEMBER)
    if pin_translation_ptr != pin + 0x30:
        raise ValueError("pin candidate translation constructor self-pointer failed")
    pin_words = selected._triplet(read_u32, pin_translation_ptr)
    if not selected._finite_bounded(pin_words):
        raise ValueError("nonfinite or enormous pin candidate")
    pm = read_u32(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    idx = private["selected_index"]
    record = pm + 4 + idx * roster.ROSTER_STRIDE
    ball = read_u32(record + 0x88)
    if roster._bank(ball, 0x1AC) != "MEM2":
        raise ValueError("selected child lacks entire source ball buffer")
    caches = [selected._triplet(read_u32, ball + off) for off in CACHE_TRIPLES]
    if not all(selected._finite_bounded(x) for x in caches):
        raise ValueError("source-backed candidate cache vector not bounded")
    selected_current = private["ball"]
    start = private["start"]
    count_equal = lambda a, b: sum(u == v for u, v in zip(a, b))
    return {
        "kind": "local-private-golf-ball-goal-cache-source-candidates",
        "schema_version": 1,
        "source_game": "RSPE01", "disc_revision": 1, "source_mode": 4,
        "selected_record_relative_index": idx,
        "static_PPC_source_proofs": checks,
        "source_field_target_count_is_zero": target_count == 0,
        "field_goal_getter_uses_pin_branch_for_this_snapshot":
            target_count == 0,
        "source_current_pin_translation_is_valid_and_bounded": True,
        "selected_ball_nested_current_vector_vs_start_equal_words":
            count_equal(selected_current, start),
        "selected_cc_cache_vs_current_ball_equal_components":
            count_equal(caches[0], selected_current),
        "selected_f0_cache_vs_start_equal_components":
            count_equal(caches[1], start),
        "selected_fc_cache_vs_start_equal_components":
            count_equal(caches[2], start),
        "all_three_cache_triplets_equal_each_other": (
            caches[0] == caches[1] == caches[2]
        ),
        "source_selected_goal_is_physically_verified_pin": False,
        "source_cache_is_verified_closest_approach_or_score": False,
        "gameplay_ball_world_xyz_verified": False,
        "swing_contact_velocity_power_verified": False,
        "independent_same_frame_banks_proven": False,
        "approved_for_training": False,
        "allowed_to_publish": False,
        "warning": (
            "PPC proves a field-count-based target/pin getter and separate "
            "conditional cache copy/update instructions; it does not prove "
            "cache receiver is the observed selected ball, that any cache "
            "updates executed, physical approach distance, wind, power, score "
            "or world-space units. A single stationary native bank pair "
            "cannot establish a dynamic trajectory."
        )
    }


def run_local(private_dir: Path):
    root = selected.DATA_ROOT.resolve(strict=True)
    if private_dir.is_symlink() or not private_dir.is_dir():
        raise ValueError("invalid private source pair")
    location = private_dir.resolve(strict=True)
    if not location.is_relative_to(root):
        raise ValueError("outside ignored private Data root")
    m1 = selected._approved_bank(location / "mem1.raw", root, roster.MEM1_SIZE)
    m2 = selected._approved_bank(location / "mem2.raw", root, roster.MEM2_SIZE)
    with ExitStack() as stack:
        f1 = stack.enter_context(m1.open("rb"))
        f2 = stack.enter_context(m2.open("rb"))
        b1 = stack.enter_context(mmap.mmap(f1.fileno(), 0, access=mmap.ACCESS_READ))
        b2 = stack.enter_context(mmap.mmap(f2.fileno(), 0, access=mmap.ACCESS_READ))
        bank = roster.TwoBankReader(b1, b2)
        return analyze_one(bank.u32, bank.header())


def main(argv=None):
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--first-dir", required=True, type=Path)
    parsed = args.parse_args(argv)
    try:
        report = run_local(parsed.first_dir)
    except (OSError, ValueError, TypeError, OverflowError):
        print("Private ball cache/goal callgraph study refused; "
              "source, private path, or selected owner check failed. "
              "No raw floats, RAM, paths or instruction words exposed.",
              file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
