"""S002 read-only *pin confound* follow-up to source-gated B0 vs airborne PR #223.

NO Dolphin/RPC/controller/pause/ROM read/write, RAM scan, network or publisher.
Reuses #223's strict private SHA manifests + PPC golfer/ball/field provenance.
Raw vectors and dynamic object pointers exist transiently only in memory.
All printed fields are booleans or source-relative component counts.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import math
import mmap
from pathlib import Path
import struct
import sys

# Python -I intentionally excludes the script directory from sys.path.
# Admit only this checked-out script's own directory for sibling source
# modules; do not accept arbitrary cwd files or user-supplied Python paths.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_p0_inflight_vs_b0_private as audit
import audit_golf_two_bank_roster_private as roster

VEC_NAMES = ("selected_ball", "start", "pin", "cache_cc", "cache_f0", "cache_fc")
OBJECT_KEYS = ("field_manager", "golf_config", "player_manager",
               "selected_record", "selected_ball", "selected_start", "selected_pin")
ROUNDING_REL_TOL = 1e-6
ROUNDING_ABS_TOL = 1e-4


def _float_from_word(word: int) -> float:
    if type(word) is not int or not 0 <= word <= 0xffffffff:
        raise ValueError("invalid private big endian f32")
    val = struct.unpack(">f", struct.pack(">I", word))[0]
    if not math.isfinite(val) or abs(val) > 100000.0:
        raise ValueError("unbounded scene/ball candidate")
    return val


def _vec(words) -> tuple[float, float, float]:
    if len(words) != 3:
        raise ValueError("source vector is not exactly three u32 words")
    return tuple(_float_from_word(w) for w in words)


def _near(a, b) -> bool:
    return math.isclose(a, b, rel_tol=ROUNDING_REL_TOL, abs_tol=ROUNDING_ABS_TOL)


def _snap(rd: roster.TwoBankReader) -> dict:
    # Independent Rev1 source/RAM validation is delegated to #223.
    src = audit._sample(rd)
    u = rd.u32
    field = u(roster.GOLF_FIELD_STATIC)
    pm = u(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    rec = pm + 4 + src["selected_index"] * roster.ROSTER_STRIDE
    ball = u(rec + 0x88)
    start = u(field + 0x50)
    pin = u(field + 0x44)
    config = u(roster.GOLF_CONFIG_STATIC)
    if (roster._bank(pin, 0x50) != "MEM2"
            or u(pin + 0x48) != pin + 0x0c
            or u(pin + 0x4c) != pin + 0x30):
        raise ValueError("current pin not verified by Rev1 constructor invariants")
    pin_vec = audit._read_triplet(u, pin + 0x30)
    srcvec = src["triplets"]
    return {
        "selected_index": src["selected_index"], "hole": src["hole"],
        "roots": {
            "field_manager": field,
            "golf_config": config,
            "player_manager": pm,
            "selected_record": rec,
            "selected_ball": ball,
            "selected_start": start,
            "selected_pin": pin,
        },
        "pin_firstword": u(pin),
        "pin_selfrefs_verified": True,
        "triplets": {
            "selected_ball": srcvec["ball_object_0x030"],
            "start": srcvec["source_current_start"],
            "pin": pin_vec,
            "cache_cc": srcvec["ball_cache_0x0cc"],
            "cache_f0": srcvec["ball_cache_0x0f0"],
            "cache_fc": srcvec["ball_cache_0x0fc"],
        },
    }


def compare(b0: dict, flight: dict) -> dict:
    if (b0["hole"] != flight["hole"]
            or b0["selected_index"] != flight["selected_index"]
            or set(b0["roots"]) != set(OBJECT_KEYS)
            or set(flight["roots"]) != set(OBJECT_KEYS)
            or set(b0["triplets"]) != set(VEC_NAMES)
            or set(flight["triplets"]) != set(VEC_NAMES)
            or b0["pin_selfrefs_verified"] is not True
            or flight["pin_selfrefs_verified"] is not True):
        raise ValueError("source owner/slot/hole not comparable")
    a = {k: _vec(b0["triplets"][k]) for k in VEC_NAMES}
    b = {k: _vec(flight["triplets"][k]) for k in VEC_NAMES}
    pin_delta = [b["pin"][i] - a["pin"][i] for i in range(3)]
    ball_delta = [b["selected_ball"][i] - a["selected_ball"][i] for i in range(3)]
    near_pin_vs_ball = [
        _near(pin_delta[i], ball_delta[i]) for i in range(3)]
    pin_changed = [
        not _near(a["pin"][i], b["pin"][i]) for i in range(3)]
    tee_changed = [
        not _near(a["start"][i], b["start"][i]) for i in range(3)]
    def distance(vec1, vec2, *, horizontal):
        axes = (0, 2) if horizontal else (0, 1, 2)
        return math.sqrt(sum((vec1[i] - vec2[i]) ** 2 for i in axes))

    base_horizontal = distance(a["pin"], a["start"], horizontal=True)
    flight_horizontal = distance(b["pin"], b["start"], horizontal=True)
    base_3d = distance(a["pin"], a["start"], horizontal=False)
    flight_3d = distance(b["pin"], b["start"], horizontal=False)
    caches = {}
    for key in ("cache_cc", "cache_f0", "cache_fc"):
        caches[key] = {
            "B0_cache_vs_ball_words_equal": sum(
                x == y for x, y in zip(b0["triplets"][key], b0["triplets"]["selected_ball"])),
            "flight_cache_vs_ball_words_equal": sum(
                x == y for x, y in zip(flight["triplets"][key], flight["triplets"]["selected_ball"])),
            "B0_to_flight_cache_changed_words": sum(
                x != y for x, y in zip(b0["triplets"][key], flight["triplets"][key])),
        }

    pin_changes_words = sum(x != y for x, y in zip(b0["triplets"]["pin"], flight["triplets"]["pin"]))
    return {
        "kind": "S002-B0-AIRBORNE-PIN-CONTROL-CONFOUND",
        "schema_version": 1,
        "game_id": "RSPE01",
        "disc_revision": 1,
        "mode": 4,
        "source_gated_both_snapshots": True,
        "source_selected_slot_and_hole_stable": True,
        "pin_constructor_invariants_pass_both": True,
        "same_dynamic_pointer_values_across_captures": {
            key: b0["roots"][key] == flight["roots"][key] for key in OBJECT_KEYS
        },
        "pin_object_first_word_equal_across_captures":
            b0["pin_firstword"] == flight["pin_firstword"],
        "pin_changed_bitwise_components_out_of_three": pin_changes_words,
        "pin_changed_beyond_float_roundoff_by_axis": {
            key: changed for key, changed in zip(("x", "y", "z"), pin_changed)
        },
        "start_changed_beyond_float_roundoff_by_axis": {
            key: changed for key, changed in zip(("x", "y", "z"), tee_changed)
        },
        "pin_tee_horizontal_distance_stable_within_tolerance": _near(
            base_horizontal, flight_horizontal),
        "pin_tee_3d_distance_stable_within_tolerance": _near(
            base_3d, flight_3d),
        "ball_and_pin_displacement_agree_by_axis": {
            key: agreed for key, agreed in zip(("x", "y", "z"), near_pin_vs_ball)
        },
        "ball_and_pin_displacement_agree_all_axes": all(near_pin_vs_ball),
        "ball_position_candidate_change_component_count": sum(
            x != y for x, y in zip(
                b0["triplets"]["selected_ball"], flight["triplets"]["selected_ball"])),
        "ball_current_vs_cache_word_equality": caches,
        "pin_control_passed": not any(pin_changed) and pin_changes_words == 0,
        "pin_control_confounded": any(pin_changed) or pin_changes_words != 0,
        "independent_same_boot_proven": False,
        "same_guest_frame_verified": False,
        "actual_ball_world_xyz_verified": False,
        "ball_velocity_verified": False,
        "power_ram_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
        "warning": ("Pointer equality is not proof of one boot; displacement or distance "
                    "agreement is not world-frame validation. Non-atomic GUI bank exports "
                    "and an unsteady pin prevent promotion of candidate motion to physics."),
    }


def run_local(baseline: Path, flight: Path) -> dict:
    # Mandatory: independent #223 original and airborne source gate first.
    prior = audit.run_local(baseline, flight)
    if (prior.get("source_gated_both_snapshots") is not True
            or prior.get("selected_slot_and_hole_match") is not True):
        raise ValueError("base source comparison did not qualify")
    private_root = audit.selected.DATA_ROOT.resolve(strict=True)
    base = audit._under_data(baseline, private_root)
    airborne = audit._under_data(flight, private_root)
    with ExitStack() as stack:
        samples = []
        for folder, names in (
            (base, (("B0-MEM1.bin", roster.MEM1_SIZE),
                    ("B0-MEM2.bin", roster.MEM2_SIZE))),
            (airborne, (("mem1.raw", roster.MEM1_SIZE),
                        ("mem2.raw", roster.MEM2_SIZE)))):
            maps = []
            for name, size in names:
                f = stack.enter_context(audit._file(folder, name, size).open("rb"))
                maps.append(stack.enter_context(mmap.mmap(
                    f.fileno(), 0, access=mmap.ACCESS_READ)))
            samples.append(_snap(roster.TwoBankReader(*maps)))
        return compare(*samples)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--flight", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = run_local(args.baseline, args.flight)
    except (OSError, ValueError, KeyError, TypeError, OverflowError, struct.error):
        print("P0 pin-control source/manifest comparison ABSTAIN; no private values emitted.",
              file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
