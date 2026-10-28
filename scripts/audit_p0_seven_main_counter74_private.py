"""Source-gated seven-capture test of the untyped RPGolMain +0x74 counter.

ALL values, guest addresses, native RAM and SHA256 remain local. This is a
clock/background-activity DISCRIMINATOR, not a machine guest-frame timestamp.
Reuses canonical #231 original 14-bank SHA and per-capture Rev1 selected scene
source gates. No Dolphin, controller, capture, writes, uploading or training.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as seven
import audit_golf_two_bank_roster_private as roster

PHASES = tuple(range(1, 8))
# Only within human-annotated SAME-shot pairs; not the putter-v-driver #3/#4.
EDGES = ((1, 2, "driver_airborne_to_settled"),
         (5, 6, "wedge_near_apex_to_descent"),
         (6, 7, "wedge_descent_to_flag_ui"),
         (5, 7, "wedge_near_apex_to_flag_ui"))
U32_LIMIT = 1 << 32


def _intword(v):
    if type(v) is not int or not 0 <= v < U32_LIMIT:
        raise ValueError("Invalid native private u32")
    return v


def _sample(rd):
    # S002 #231 validates the native game revision, scene5, sport2, mode4,
    # player/hole/active selected ball and the source pin/tee translation.
    s = seven._get(rd)
    u = rd.u32
    manager = u(roster.SCENE_MANAGER_STATIC)
    scene = u(manager + 0x0C)
    main = u(scene + 0x9C)
    if (roster._bank(main, 0x78) != "MEM2"
            or not roster._in_data(u(main), roster.MAIN_DATA)
            or u(manager + 0x18) != 5
            or u(scene + 0x1C) != 5
            or u(scene + 0x20) != manager
            or u(scene + 0x54) != 2):
        raise ValueError("RPGolMain source identity or scene failed")
    pm = u(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    record = pm + 4 + roster.ROSTER_STRIDE * s["selected_index"]
    if roster._bank(record, roster.ROSTER_STRIDE) != "MEM2":
        raise ValueError("Selected player record escaped MEM2")
    ball = u(record + 0x88)
    if roster._bank(ball, 0x108) != "MEM2" or u(ball + 0x4C) != ball + 0x30:
        raise ValueError("Selected ball source selfref failed")
    field = u(roster.GOLF_FIELD_STATIC)
    pin = u(field + 0x44)
    start = u(field + 0x50)
    config = u(roster.GOLF_CONFIG_STATIC)
    if any(roster._bank(p, 0x50) != "MEM2" for p in (pin, start)):
        raise ValueError("Source pin/tee object escaped MEM2")
    if u(pin + 0x4C) != pin + 0x30 or u(start + 0x4C) != start + 0x30:
        raise ValueError("Pin/tee source geometry selfref failed")
    return {
        "main_counter": _intword(u(main + 0x74)),
        # Pointers used ONLY internally as source equality controls.
        "owner": (manager, scene, main, pm, record, ball, field,
                  pin, start, config),
        "selection": (s["selected_index"], s["hole"],
                      s["cfg_bc"], s["cfg_c0"], s["cfg_c4"]),
        "pin": tuple(_intword(v) for v in s["pin"]),
        "tee": tuple(_intword(v) for v in
                     s["triplets"]["source_current_start"]),
        "ball": tuple(_intword(v) for v in
                      s["triplets"]["ball_object_0x030"]),
    }


def _strict_state(sample):
    if type(sample) is not dict:
        raise ValueError("Invalid source sample")
    for key, width in (("owner", 10), ("selection", 5),
                       ("pin", 3), ("tee", 3), ("ball", 3)):
        a = sample.get(key)
        if type(a) not in (tuple, list) or len(a) != width:
            raise ValueError("Invalid source sample field structure")
        for word in a:
            _intword(word)
    _intword(sample.get("main_counter"))


def _compatible(a, b):
    return all(a[k] == b[k] for k in
               ("owner", "selection", "pin", "tee"))


def _count_changed(a, b):
    return sum(x != y for x, y in zip(a, b))


def _comparison(a, b):
    if a == b:
        return "unchanged"
    if b > a:
        return "numerically_increased"
    # A backwards u32 could be a reset, wrap, allocator reuse or actual
    # decrement; NEVER fabricate an unwrapped frame count.
    return "numerically_decreased_or_wrapped_unknown"


def summarize(states):
    if set(states) != set(PHASES):
        raise ValueError("Exactly seven numbered native samples required")
    for s in states.values():
        _strict_state(s)
    out = []
    for lo, hi, label in EDGES:
        a, b = states[lo], states[hi]
        if not _compatible(a, b):
            raise ValueError("Within-shot source owner/geometry/selector changed")
        c1, c2 = a["main_counter"], b["main_counter"]
        out.append({
            "human_phase_edge_unverified_frame_link": label,
            "source_owner_selection_pin_tee_equal": True,
            "ball_changed_components_of_three":
                _count_changed(a["ball"], b["ball"]),
            "main_plus_0x74_word_equal": c1 == c2,
            "main_plus_0x74_numerical_order": _comparison(c1, c2),
        })

    w5, w6, w7 = (states[i]["main_counter"] for i in (5, 6, 7))
    strictly_increasing = w5 < w6 < w7
    relative_gap = "not_calculable_as_positive_monotone_u32"
    if strictly_increasing:
        early, late = w6 - w5, w7 - w6
        relative_gap = (
            "earlier_numerical_increment_smaller" if early < late
            else "earlier_numerical_increment_larger" if early > late
            else "increments_equal"
        )

    return {
        "kind": "P0-SANITIZED-SEVEN-RPGOLMAIN-74-COUNTER-ORDINAL-AUDIT",
        "schema_version": 1,
        "original_seven_pair_archive_SHA_gated": True,
        "source_scene_owner_and_geometry_gated": True,
        "measured_native_field": "source_RPGolMain_plus_0x74_untyped_u32",
        "new_native_data_captured": False,
        "comparisons": out,
        "wedge_main_plus_0x74_strictly_numerically_increasing":
            strictly_increasing,
        "wedge_increment_comparison_if_strictly_increasing": relative_gap,
        "legacy_B0_to_B3_counter_increased_in_idle_aim":
            "previously_observed_separate_cohort_not_independently_rechecked",
        "counter_is_guest_frame_number_verified": False,
        "counter_is_monotonic_game_tick_verified": False,
        "counter_is_swing_power_verified": False,
        "counter_rate_in_frames_per_second_verified": False,
        "same_emulator_boot_across_captures_machine_verified": False,
        "pair_mem1_mem2_same_guest_frame_machine_verified": False,
        "ball_world_xyz_or_velocity_verified": False,
        "shot_result_or_score_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
        "interpretation_limit": (
            "Numerical u32 changes in a source scene-main field are not "
            "frame counts, time deltas, motion signals or power. Human shot "
            "phase order may not equal guest-frame or same-boot identity."
        ),
    }


def analyze(archive: Path):
    # Canonical #231 verifies ALL fourteen native SHA-256 checks FIRST,
    # before reading any source object from any of the seven captures.
    folders = seven._check_archive(archive)
    with ExitStack() as stack:
        states = {}
        for n in PHASES:
            banks = []
            for i, size in enumerate(seven.SIZE):
                file = seven.src._file(folders[n], f"{n}.{i + 1}.raw", size)
                f = stack.enter_context(file.open("rb"))
                banks.append(stack.enter_context(
                    mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)))
            states[n] = _sample(roster.TwoBankReader(*banks))
        return summarize(states)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", required=True, type=Path)
    opts = p.parse_args(argv)
    try:
        report = analyze(opts.archive)
    except (OSError, ValueError, TypeError, KeyError, OverflowError, IndexError):
        print("P0_MAIN_COUNTER_74_ABSTAIN: archive SHA, native source, "
              "field or unchanged owner/geometry gate failed.", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
