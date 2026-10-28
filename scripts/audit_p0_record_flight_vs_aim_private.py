"""Offline private B0–B3 no-shot vs human-airborne selected-player record mask.

Uses existing #223/#181 full-bank SHA and Rev1 source-selected parser.
Only field-relative 0xCC record offsets and categorical counts reach stdout.
Not guest-frame-atomic; never proves ball XYZ, velocity, power or training.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

# -I omits script parent; allow ONLY this checked-out script sibling directory.
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import audit_p0_inflight_vs_b0_private as inflight
import audit_selected_ball_four_phase_private as four
import audit_golf_two_bank_roster_private as roster

SLOTS = ("B0", "B1", "B2", "B3", "FLIGHT")
RECORD_WORDS = roster.ROSTER_STRIDE // 4
NO_SHOT_PAIRS = (("B0", "B1"), ("B1", "B2"), ("B2", "B3"))


def offsets(words: list[int] | tuple[int, ...], other: list[int] | tuple[int, ...]) -> set[int]:
    if len(words) != RECORD_WORDS or len(other) != RECORD_WORDS:
        raise ValueError("Expected exactly 51 full record words")
    if any(type(x) is not int or not (0 <= x <= 0xFFFFFFFF)
           for x in (*words, *other)):
        raise ValueError("Invalid source-selected u32 record")
    return {i * 4 for i, (a, b) in enumerate(zip(words, other)) if a != b}


def _offset_strings(indices: set[int]) -> list[str]:
    return [f"+0x{x:03X}" for x in sorted(indices)]


def _triplet_changes(x: tuple[int, ...], y: tuple[int, ...]) -> int:
    if len(x) != 3 or len(y) != 3:
        raise ValueError("Three-word control triplet required")
    return sum(a != b for a, b in zip(x, y))


def summarize(samples: dict[str, dict]) -> dict:
    if set(samples) != set(SLOTS):
        raise ValueError("Expected exact B0/B1/B2/B3/FLIGHT cohort")
    origin = samples["B0"]
    ref_slot, ref_hole = origin["selected_index"], origin["hole"]
    for phase in SLOTS:
        sample = samples[phase]
        if (type(sample["selected_index"]) is not int or
                type(sample["hole"]) is not int or
                sample["selected_index"] != ref_slot or sample["hole"] != ref_hole or
                sample.get("ball_constructor_translation_selfref") is not True or
                sample.get("start_constructor_selfrefs") is not True):
            raise ValueError("Selected owner/hole/constructor changed or gate incomplete")
        offsets(origin["whole_record"], sample["whole_record"])

    pair_diffs = {
        f"{a}_to_{b}": offsets(samples[a]["whole_record"], samples[b]["whole_record"])
        for a, b in NO_SHOT_PAIRS
    }
    no_shot_union = set().union(*pair_diffs.values())
    wasd_only = pair_diffs["B1_to_B2"]
    idle_flanks = pair_diffs["B0_to_B1"] | pair_diffs["B2_to_B3"]
    changed_flight = offsets(origin["whole_record"], samples["FLIGHT"]["whole_record"])
    shared = changed_flight & no_shot_union
    novel = changed_flight - no_shot_union
    negative_only = no_shot_union - changed_flight
    start = [samples[phase]["triplets"]["source_current_start"] for phase in SLOTS]
    ball = [samples[phase]["triplets"]["ball_nested_plus_0x4c"] for phase in SLOTS]

    return {
        "kind": "P0-PRIVATE-B0-B3-VS-HUMAN-AIRBORNE-RECORD-CHANGE-MASK",
        "schema_version": 1,
        "game_id": "RSPE01",
        "disc_revision": 1,
        "phase_labels_operator_not_independent_frame_proof": list(SLOTS),
        "source_scene_owner_selected_slot_hole_stable": True,
        "same_guest_physics_frame_verified": False,
        "same_boot_verified": False,
        "selected_record_words_per_phase": RECORD_WORDS,
        "no_shot_transition_changed_counts": {
            key: len(indices) for key, indices in pair_diffs.items()
        },
        "no_shot_transition_changed_offsets": {
            key: _offset_strings(indices) for key, indices in pair_diffs.items()
        },
        "wasd_aim_B1_to_B2_changed_offsets": _offset_strings(wasd_only),
        "idle_flank_changed_offsets": _offset_strings(idle_flanks),
        "no_shot_any_changed_offsets": _offset_strings(no_shot_union),
        "airborne_vs_B0_changed_offsets": _offset_strings(changed_flight),
        "airborne_vs_B0_changed_word_count": len(changed_flight),
        "shared_airborne_and_no_shot_changed_offsets": _offset_strings(shared),
        "shared_airborne_and_no_shot_changed_count": len(shared),
        "airborne_only_relative_to_no_shot_offsets": _offset_strings(novel),
        "airborne_only_relative_to_no_shot_count": len(novel),
        "no_shot_only_relative_to_airborne_offsets": _offset_strings(negative_only),
        "no_shot_only_relative_to_airborne_count": len(negative_only),
        "source_ball_B0_vs_airborne_changed_components": _triplet_changes(ball[0], ball[-1]),
        "source_start_B0_vs_airborne_changed_components": _triplet_changes(start[0], start[-1]),
        "no_shot_ball_triplet_stable": len(set(ball[:4])) == 1,
        "no_shot_start_triplet_stable": len(set(start[:4])) == 1,
        "record_offset_change_does_not_establish_semantic_field": True,
        "airborne_only_is_NOT_verified_physical_motion": True,
        "pin_control_checked_by_this_study": False,
        "pin_control_confounded_in_independent_real_report": True,
        "source_selected_ball_world_xyz_verified": False,
        "ball_velocity_verified": False,
        "shot_power_verified": False,
        "actual_human_contact_joined_to_frames": False,
        "approved_for_training": False,
        "allowed_to_publish": False,
        "raw_private_data_uploaded": False,
    }


def read_private(baseline: Path, flight: Path) -> dict:
    root = inflight.selected.DATA_ROOT.resolve(strict=True)
    b0 = inflight._under_data(baseline, root)
    fp = inflight._under_data(flight, root)
    if b0 == fp:
        raise ValueError("Cannot use one private session twice")
    original = four._validate_manifest(b0)
    inflight._flight_manifest(fp)  # verifies private flight files SHA against manifest
    samples = {}
    with ExitStack() as stack:
        for phase in SLOTS:
            folder = b0 if phase != "FLIGHT" else fp
            names = (
                (f"{phase}-MEM1.bin", f"{phase}-MEM2.bin")
                if phase != "FLIGHT" else ("mem1.raw", "mem2.raw")
            )
            files = [
                inflight._file(folder, names[0], roster.MEM1_SIZE),
                inflight._file(folder, names[1], roster.MEM2_SIZE),
            ]
            if phase != "FLIGHT":
                for path, kind in zip(files, ("MEM1", "MEM2")):
                    if four._hash(path) != original[phase]["sha256"][kind].lower():
                        raise ValueError("B0-B3 native SHA verification failed")
            maps = []
            for path in files:
                f = stack.enter_context(path.open("rb"))
                maps.append(stack.enter_context(mmap.mmap(
                    f.fileno(), 0, access=mmap.ACCESS_READ)))
            sample = inflight._sample(roster.TwoBankReader(*maps))
            samples[phase] = sample
        return summarize(samples)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--flight", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = read_private(args.baseline, args.flight)
    except (ValueError, OSError, KeyError, TypeError, OverflowError):
        print("P0 record no-shot/airborne mask ABSTAIN: invalid private source, SHA, selected owner or fields. No private data disclosed.", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
