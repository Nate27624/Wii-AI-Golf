"""P0 source-only bounded Golf OnCalculate (two-word) dispatch gate.

Source hypotheses from public RPGolScene.h: OnCalculate PC 0x8028DFA8,
next OnReset PC 0x8028DFB0; RPGolScene::mGolMain at scene +0x9C.
This script validates *only* that exact Rev1 two-word branch structure
in the existing canonical seven 14-bank SHA-preserved archive.
Neither frameadvance nor a scene Calculate callback proves one physics step.
Raw RAM/code words, private heap addresses, hashes and file paths stay local.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

_HERE = str(Path(__file__).resolve().parent)
if _HERE in sys.path:
    sys.path.remove(_HERE)
sys.path.insert(0, _HERE)
import audit_p0_seven_numbered_source_pairs_private as seven
import audit_golf_two_bank_roster_private as roster

# Public header annotation and reviewed .text split source regions only.
CALCULATE_PC = 0x8028DFA8
NEXT_CALLBACK_PC = 0x8028DFB0
SCENE_MAIN_OFFSET = 0x9C
MAIN_UNIT_LO = 0x8028E098
MAIN_UNIT_HI = 0x8028E900
PHASES = tuple(range(1, 8))


def decode_b_target(word: int, pc: int):
    """Exact PPC 32-bit I-form direct branch. No indirect/conditional inference."""
    if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
        raise ValueError("Invalid PPC word")
    if word >> 26 != 18 or word & 1:
        return None  # not a non-linking direct b, including any bl
    li = word & 0x03FFFFFC
    if li & 0x02000000:
        li -= 0x04000000
    absolute = bool(word & 2)
    dest = li if absolute else pc + li
    if dest & 3 or not 0x80000000 <= dest <= 0x817FFFFC:
        return None
    return dest


def classify_two_word_source(words: tuple[int, int]) -> dict:
    if not isinstance(words, (list, tuple)) or len(words) != 2:
        raise ValueError("Expected exactly two source words")
    w0, w1 = words
    if any(type(w) is not int or not 0 <= w <= 0xFFFFFFFF for w in words):
        raise ValueError("Malformed PPC source words")
    if NEXT_CALLBACK_PC - CALCULATE_PC != 8:
        raise ValueError("Public annotation boundary changed")
    # Exact D-form: lwz r3,+0x9C(r3) (source main pointer hypothesis).
    direct_load = (
        w0 >> 26 == 32
        and (w0 >> 21) & 31 == 3
        and (w0 >> 16) & 31 == 3
        and w0 & 0xFFFF == SCENE_MAIN_OFFSET
    )
    target = decode_b_target(w1, CALCULATE_PC + 4)
    within_main = target is not None and MAIN_UNIT_LO <= target < MAIN_UNIT_HI
    # The target is a public static code PC. It is NOT a private heap pointer.
    return {
        "public_oncalculate_header_annotation_checked": True,
        "two_word_callback_bounds_held": True,
        "source_first_word_lwz_r3_scene_plus_0x9c": direct_load,
        "source_second_word_direct_nonlinking_b": target is not None,
        "direct_branch_target_in_published_RPGolMain_text": within_main,
        "candidate_target_public_code_pc":
            f"0x{target:08X}" if within_main and direct_load else None,
        "oncalculate_to_main_direct_thunk_supported":
            bool(direct_load and within_main),
        "branch_is_runtime_executed_verified": False,
        "main_pointer_is_physics_object_verified": False,
        "one_callback_equals_one_guest_physics_step_verified": False,
    }


# Narrow follow-up after REAL #279 OnCalculate -> main confirmation.
# Exactly 0x100 bytes of static code. This is not a function boundary or CFG.
CONFIRMED_MAIN_TARGET = 0x8028E158
MAIN_PREFIX_BYTES = 0x100
CALLEE_UNITS = (
    ("RPGolMain", 0x8028E098, 0x8028E900),
    ("RPGolFieldManager", 0x80290B44, 0x80294184),
    ("RPGolMapObjBall", 0x80296FD8, 0x8029B240),
    ("RPGolSimulateManager", 0x8029B240, 0x8029BBB4),
    ("RPGolPlayer", 0x8029E62C, 0x802A2210),
    ("RPGolPlayerManager", 0x802A2210, 0x802A3560),
)


def classify_main_prefix(words: tuple[int, ...]) -> dict:
    """Lexical direct-call opportunities; NEVER asserts a runtime code path.

    A branch, bclr or indirect call changes the real control-flow relation.
    This deliberately does NOT follow it; absence of direct BL proves nothing.
    """
    if (not isinstance(words, (tuple, list))
            or len(words) != MAIN_PREFIX_BYTES // 4
            or any(type(w) is not int or not 0 <= w <= 0xFFFFFFFF
                   for w in words)):
        raise ValueError("Incomplete exact main entry source prefix")

    direct_calls = []
    indirect_branch_count = 0
    conditional_branch_count = 0
    unconditional_nonlink_count = 0
    plain_blr_offsets = []
    first_plain_blr_at = None

    for i, word in enumerate(words):
        pc = CONFIRMED_MAIN_TARGET + 4*i
        op = word >> 26

        if op == 18:
            # PowerPC I-form b/bl, AA=0 required for a relative target.
            li = word & 0x03FFFFFC
            if li & 0x02000000:
                li -= 0x04000000
            target = li if word & 2 else pc + li
            if word & 1:  # LK=1 is static direct call.
                unit = "outside_reviewed_golf_units"
                within_unit_offset = None
                for name, lo, hi in CALLEE_UNITS:
                    if lo <= target < hi:
                        unit = name
                        within_unit_offset = f"+0x{target-lo:04X}"
                        break
                direct_calls.append({
                    "prefix_relative_callsite": f"+0x{4*i:03X}",
                    "target_public_golf_unit": unit,
                    "target_unit_relative_offset": within_unit_offset,
                })
            else:
                unconditional_nonlink_count += 1
        elif op == 16:
            conditional_branch_count += 1
        elif op == 19 and ((word >> 1) & 1023) in (16, 528):
            indirect_branch_count += 1
            # A plain blr is recognized only as an annotation, not a bound.
            if word == 0x4E800020:
                plain_blr_offsets.append(f"+0x{4*i:03X}")
                if first_plain_blr_at is None:
                    first_plain_blr_at = i

    # Prefix beyond first return can be another branch target. Conservatively
    # report both total lexical sites and those up to the first plain blr.
    first_return_reachable_call_count = (
        sum(int(int(v["prefix_relative_callsite"][3:], 16) < first_plain_blr_at*4)
            for v in direct_calls) if first_plain_blr_at is not None else None
    )
    return {
        "exact_confirmed_main_target_public_pc": "0x8028E158",
        "source_prefix_size_bytes": MAIN_PREFIX_BYTES,
        "source_direct_bl_lexical_count": len(direct_calls),
        "source_direct_bl_sites_and_public_unit_targets": direct_calls,
        "source_direct_bl_to_simulation_unit_count": sum(
            v["target_public_golf_unit"] == "RPGolSimulateManager"
            for v in direct_calls
        ),
        "source_conditional_branch_lexical_count": conditional_branch_count,
        "source_unconditional_nonlink_branch_lexical_count":
            unconditional_nonlink_count,
        "source_indirect_bclr_or_bcctr_lexical_count": indirect_branch_count,
        "source_plain_blr_lexical_offsets": plain_blr_offsets,
        "source_direct_calls_before_first_plain_blr_count":
            first_return_reachable_call_count,
        "lexical_instruction_window_is_verified_function_body": False,
        "all_reported_BL_sites_execute_in_game": False,
        "no_direct_call_does_not_exclude_indirect_or_nested_simulation": True,
        "one_main_callback_one_physics_update_verified": False,
    }


def analyze(archive: Path) -> dict:
    dirs = seven._check_archive(archive)  # full original 14-bank SHA first
    source_words = []
    main_prefixes = []
    owners = []
    for n in PHASES:
        with ExitStack() as stack:
            maps = []
            for i, size in enumerate(seven.SIZE):
                p = seven.src._file(dirs[n], f"{n}.{i + 1}.raw", size)
                fp = stack.enter_context(p.open("rb"))
                maps.append(stack.enter_context(mmap.mmap(
                    fp.fileno(), 0, access=mmap.ACCESS_READ)))
            rd = roster.TwoBankReader(*maps)
            s = seven._get(rd)  # original scene, mode, selected ball, pin/start
            u = rd.u32
            sm = u(0x804BF4D8)
            if roster._bank(sm, 0x1C) != "MEM1":
                raise ValueError("Scene manager source pointer not qualified")
            scene = u(sm + 0x0C)
            if (roster._bank(scene, 0xA0) != "MEM2"
                    or u(scene + 0x1C) != 5
                    or u(scene + 0x54) != 2):
                raise ValueError("Golf scene source identity not qualified")
            main = u(scene + SCENE_MAIN_OFFSET)
            owner_kind = roster._bank(main, 4) if main else "null"
            if owner_kind not in ("MEM1", "MEM2", "null"):
                owner_kind = "unmapped"
            owners.append(owner_kind)
            if s["hole"] not in range(9):
                raise ValueError("Selected golf hole/source control invalid")
            source_words.append((u(CALCULATE_PC), u(CALCULATE_PC + 4)))
            main_prefixes.append(tuple(u(CONFIRMED_MAIN_TARGET + 4*i)
                                       for i in range(MAIN_PREFIX_BYTES // 4)))

    # Each archive captures the same revision's executable instructions.
    stable = all(words == source_words[0] for words in source_words[1:])
    if not stable:
        raise ValueError("Published OnCalculate source window changed across captures")
    report = classify_two_word_source(source_words[0])
    if (not report["oncalculate_to_main_direct_thunk_supported"]
            or report["candidate_target_public_code_pc"] !=
               "0x8028E158"):
        raise ValueError("Confirmed OnCalculate branch target not retained")
    main_prefix_stable = all(v == main_prefixes[0]
                             for v in main_prefixes[1:])
    if not main_prefix_stable:
        raise ValueError("Main code source prefix changed between originals")
    lex = classify_main_prefix(main_prefixes[0])
    seven._check_archive(archive)  # full hash again after readers close
    return {
        "kind": "P0-SANITIZED-REV1-GOLF-ONCALCULATE-THUNK-AUDIT",
        "original_14_native_bank_SHA_before_after_verified": True,
        "seven_scene_mode_selected_source_chains_verified": True,
        "source_two_word_window_unchanged_across_seven": stable,
        "source_scene_main_member_class_by_capture": owners,
        **report,
        "source_main_0x100_code_prefix_stable_in_seven": main_prefix_stable,
        "bounded_main_source_callscan": lex,
        "public_header_annotation_correlates_with_two_word_native_pattern":
            bool(report["oncalculate_to_main_direct_thunk_supported"]),
        "declared_callback_name_runtime_verified": False,
        "source_vtable_slot_and_runtime_dispatch_verified": False,
        "source_target_is_actual_ball_simulation_function_verified": False,
        "Dolphin_guest_physics_step_clock_verified": False,
        "visual_frame_bound_to_game_update_verified": False,
        "physical_xyz_velocity_impact_power_score_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        report = analyze(a.archive)
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        print("P0_ONCALCULATE_ABSTAIN: archive/source/scene/code window invalid", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
