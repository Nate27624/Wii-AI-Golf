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


def analyze(archive: Path) -> dict:
    dirs = seven._check_archive(archive)  # full original 14-bank SHA first
    source_words = []
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

    # Each archive captures the same revision's executable instructions.
    stable = all(words == source_words[0] for words in source_words[1:])
    if not stable:
        raise ValueError("Published OnCalculate source window changed across captures")
    report = classify_two_word_source(source_words[0])
    seven._check_archive(archive)  # full hash again after readers close
    return {
        "kind": "P0-SANITIZED-REV1-GOLF-ONCALCULATE-THUNK-AUDIT",
        "original_14_native_bank_SHA_before_after_verified": True,
        "seven_scene_mode_selected_source_chains_verified": True,
        "source_two_word_window_unchanged_across_seven": stable,
        "source_scene_main_member_class_by_capture": owners,
        **report,
        "source_declared_callback_name_matches_native_rev1_verified":
            bool(report["oncalculate_to_main_direct_thunk_supported"]),
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
