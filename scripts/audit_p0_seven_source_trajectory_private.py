"""PRIVATE read-only seven-human-dump source trajectory contrast.

Complements S002 generic seven-dump page-delta inventory, not a replacement.
Only compare HUMAN-LABELED within-shot driver 1->2 and wedge 5->6->7.
Putter #3 (no A) and driver #4 (A held) are controls in different poses,
NOT a valid causal difference or same-shot ballistic transition.

Expected one directory with 1.1.raw / 1.2.raw ... 7.1.raw / 7.2.raw.
Bank identity is validated by EXACT SIZE (24MiB MEM1, 64MiB MEM2),
NOT by .1/.2 suffix. All files remain local; no writes.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import mmap
from pathlib import Path
import sys

# Python -I removes the automatic script path. Reuse precisely this reviewed
# checkout's source-gated Rev1 helper modules, never globally installed copies.
SCRIPTS = str(Path(__file__).resolve().parent)
if SCRIPTS in sys.path:
    sys.path.remove(SCRIPTS)
sys.path.insert(0, SCRIPTS)
import audit_p0_inflight_vs_b0_private as source

ROSTER = source.roster
MEM1_SIZE = ROSTER.MEM1_SIZE
MEM2_SIZE = ROSTER.MEM2_SIZE
PHASE_LABELS = {
    1: "driver_ball_midair_power_rising",
    2: "same_driver_ball_stopped",
    3: "putter_backswing_A_not_pressed",
    4: "driver_medium_backswing_A_pressed",
    5: "wedge_near_peak_ball_airborne",
    6: "same_wedge_descending_ball_airborne",
    7: "same_wedge_flag_hit_ball_on_green_15p2ft",
}
TRANSITIONS = (
    ("driver_in_flight_to_settled", 1, 2),
    ("wedge_rising_to_descending", 5, 6),
    ("wedge_descending_to_flag_result", 6, 7),
    ("wedge_near_peak_to_flag_result", 5, 7),
)
FIELDS = (
    "ball_nested_plus_0x4c",
    "ball_cache_0x0cc",
    "ball_cache_0x0f0",
    "ball_cache_0x0fc",
    "record_0x054",
    "record_0x060",
    "source_current_start",
    "source_selected_pin",
)


def _private_directory(dirpath: Path) -> Path:
    if not dirpath.is_dir() or dirpath.is_symlink():
        raise ValueError("source dump directory missing or symlinked")
    return dirpath.resolve(strict=True)


def _phase_banks(directory: Path, phase: int):
    names = [directory / f"{phase}.1.raw", directory / f"{phase}.2.raw"]
    if any(not p.is_file() or p.is_symlink() for p in names):
        return None
    lengths = [p.stat().st_size for p in names]
    if sorted(lengths) != [MEM1_SIZE, MEM2_SIZE]:
        raise ValueError("wrong sized or ambiguous native bank pair")
    return {
        "MEM1": names[lengths.index(MEM1_SIZE)],
        "MEM2": names[lengths.index(MEM2_SIZE)],
    }


def _hash(path: Path) -> bytes:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.digest()


def _source_sample(mem1, mem2):
    reader = ROSTER.TwoBankReader(mem1, mem2)
    base = source._sample(reader)  # strict Rev1 PPC, scene=5, mode=4, slot, hole
    u32 = reader.u32
    field = u32(ROSTER.GOLF_FIELD_STATIC)
    pin_obj = u32(field + 0x44)
    if ROSTER._bank(pin_obj, 0x50) != "MEM2":
        raise ValueError("source selected pin object out of range")
    pin_vector = u32(pin_obj + 0x4C)
    if ROSTER._bank(pin_vector, 12) != "MEM2":
        raise ValueError("source selected pin translation out of range")
    pin_selfref = (pin_vector == pin_obj + 0x30
                   and u32(pin_obj + 0x48) == pin_obj + 0x0C)
    if not pin_selfref:
        raise ValueError("source selected pin self reference invalid")
    slot = base["selected_index"]
    pm = u32(ROSTER.PLAYER_MANAGER_STATIC_CANDIDATE)
    rec = pm + 4 + slot * ROSTER.ROSTER_STRIDE
    ball = u32(rec + 0x88)
    start_obj = u32(field + 0x50)
    if ROSTER._bank(start_obj, 0x50) != "MEM2":
        raise ValueError("source start object not in MEM2")
    vec = base["triplets"].copy()
    vec["source_selected_pin"] = tuple(u32(pin_vector + 4 * i)
                                       for i in range(3))
    return {
        "selected_index": slot, "hole": base["hole"],
        "refs": {"scene_field": field, "ball": ball,
                 "pin": pin_obj, "start": start_obj},
        "triplets": vec,
        "ball_alias_validated": bool(base["ball_constructor_translation_selfref"]),
        "pin_selfref_validated": True,
        "start_selfref_validated": bool(base["start_constructor_selfrefs"]),
    }


def _changed(a: tuple, b: tuple) -> int:
    return sum(x != y for x, y in zip(a, b))


def compare_transition(name: str, a_phase: int, b_phase: int,
                       a: dict, b: dict) -> dict:
    valid = (a["selected_index"] == b["selected_index"]
             and a["hole"] == b["hole"])
    same = {key: a["refs"][key] == b["refs"][key]
            for key in ("scene_field", "ball", "pin", "start")}
    if not valid:
        return {
            "name": name, "from_phase": a_phase, "to_phase": b_phase,
            "source_slot_and_hole_stable": False,
            "within_shot_candidate_comparison_refused": True,
            "ball_motion_proven": False,
            "training_approved": False,
        }
    counters = {
        key: _changed(a["triplets"][key], b["triplets"][key])
        for key in FIELDS
    }
    return {
        "name": name, "from_phase": a_phase, "to_phase": b_phase,
        "operator_labeled_same_shot": True,
        "source_slot_and_hole_stable": True,
        "source_runtime_pointer_value_equal": same,
        "different_component_counts_of_three": counters,
        "ball_candidate_changed_with_stable_start_and_pin": (
            counters["ball_nested_plus_0x4c"] > 0
            and counters["source_current_start"] == 0
            and counters["source_selected_pin"] == 0
            and same["ball"] and same["scene_field"]
            and same["pin"] and same["start"]
        ),
        "ball_candidate_changed_but_pin_or_pointer_confounded": (
            counters["ball_nested_plus_0x4c"] > 0
            and (counters["source_selected_pin"] > 0
                 or not all(same.values()))
        ),
        "candidate_motion_not_physical_xyz": True,
        "ball_motion_proven": False,
        "training_approved": False,
    }


def summarize(phases: dict[int,dict]) -> dict:
    edges = []
    for label,i,j in TRANSITIONS:
        if i in phases and j in phases:
            edges.append(compare_transition(label, i, j,
                                            phases[i],phases[j]))
    wedge = [phases.get(i) for i in (5,6,7)]
    wedge_three_valid = all(x is not None for x in wedge)
    wedge_unique = None
    if wedge_three_valid:
        all_same_owner = (len({w["selected_index"] for w in wedge}) == 1
                          and len({w["hole"] for w in wedge}) == 1)
        wedge_unique = (
            len({w["triplets"]["ball_nested_plus_0x4c"] for w in wedge})
            if all_same_owner else None
        )
    return {
        "kind": "PRIVATE-SANITIZED-SOURCE-GATED-SEVEN-HUMAN-PHASE-TRAJECTORY",
        "schema_version": 1,
        "human_observation_labels": PHASE_LABELS,
        "source_validated_phase_count": len(phases),
        "source_validated_phase_ids": sorted(phases),
        "within_shot_transitions": edges,
        "wedge_three_phase_selected_ball_distinct_bitpatterns": wedge_unique,
        "wedge_three_phase_motion_is_physical_xyz_verified": False,
        "different_club_and_A_controls_not_causally_compared": True,
        "operator_reported_same_shot_not_independently_time_verified": True,
        "independent_guest_frame_numbers_verified": False,
        "same_game_frame_mem1_mem2_machine_verified": False,
        "true_world_ball_xyz_verified": False,
        "velocity_or_power_verified": False,
        "contact_or_score_RAM_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
        "note": "Bitwise relative change counts and pointer identity booleans only; no game-side temporal order or world-space units verified.",
    }


def run_local(folder: Path) -> dict:
    folder = _private_directory(folder)
    banks = {i:_phase_banks(folder,i) for i in PHASE_LABELS}
    required = (1,2,5,6,7)
    if any(banks[i] is None for i in required):
        missing = [i for i in required if banks[i] is None]
        # Caller prints a PRIVATE-safe identifier list, never actual paths.
        raise ValueError("missing complete 24+64MiB pairs for phases "
                         + ",".join(map(str,missing)))
    with ExitStack() as stack:
        samples = {}
        originals = {}
        for phase, pair in banks.items():
            if pair is None:
                continue
            hashes = {name:_hash(path) for name,path in pair.items()}
            maps = {}
            for name,path in pair.items():
                fh=stack.enter_context(path.open("rb"))
                maps[name]=stack.enter_context(mmap.mmap(
                    fh.fileno(),0,access=mmap.ACCESS_READ))
            samples[phase]=_source_sample(maps["MEM1"], maps["MEM2"])
            originals[phase]=(pair,hashes)
        # Verify the source files were not modified while reading.
        for pair, hashes in originals.values():
            for name,path in pair.items():
                if _hash(path) != hashes[name]:
                    raise ValueError("native bank changed during read-only audit")
        return summarize(samples)


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dump-directory",required=True,type=Path)
    args=p.parse_args(argv)
    try:
        report=run_local(args.dump_directory)
    except (OSError,ValueError,TypeError,KeyError,OverflowError):
        print("P0_SEVEN_SOURCE_TRAJECTORY_FAILED_CLOSED: input native pair, "
              "game source, scene/actor ownership, or pin/start identity invalid.",
              file=sys.stderr)
        return 2
    print(json.dumps(report,sort_keys=True,indent=2,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
