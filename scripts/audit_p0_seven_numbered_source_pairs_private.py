"""Read-only P0 numbered seven-pair cohort using existing Rev1 source gates.

Never emits raw RAM, source pointers, numeric vectors, file paths or hashes.
Use only original SHA-verified copies in ignored Data/captures.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import hashlib
import json
import mmap
import math
import struct
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_inflight_vs_b0_private as src
import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_four_phase_private as four

SIZE = (roster.MEM1_SIZE, roster.MEM2_SIZE)
OFFSETS = (0x34, 0x38, 0x74)
EDGES = ((1, 2), (3, 4), (5, 6), (6, 7), (5, 7))
PHASE_HINTS = (
    "driver_airborne_rising", "driver_stationary",
    "putter_back_A_off", "driver_back_A_on",
    "wedge_airborne_rising", "wedge_airborne_descending",
    "wedge_flag_contact_settled"
)

def _check_archive(archive: Path) -> dict:
    root = src.selected.DATA_ROOT.resolve(strict=True)
    where = src._under_data(archive, root)
    if where.parent != (root / "captures"):
        raise ValueError("Only archived private captures permitted")
    p = where / "manifest-PRIVATE.json"
    if p.is_symlink() or not p.is_file() or p.stat().st_size > 65536:
        raise ValueError("Invalid archive manifest")
    m = json.loads(p.read_text(encoding="utf-8-sig"))
    if (m.get("kind") != "p0-private-numbered-capture-inventory"
            or m.get("training_approved") is not False
            or m.get("human_phase_file_mapping_verified") is not False
            or m.get("capture_count") != 7
            or m.get("capture_numbers") != list(range(1, 8))
            or not isinstance(m.get("captures"), list)
            or len(m["captures"]) != 7):
        raise ValueError("Unexpected archived cohort identity or training claim")
    seen = set()
    for item in m["captures"]:
        n = item.get("capture_number")
        if type(n) is not int or n not in range(1, 8) or n in seen:
            raise ValueError("Duplicate/missing capture number")
        seen.add(n)
        banks = item.get("banks")
        if not isinstance(banks, list) or len(banks) != 2:
            raise ValueError("Incomplete paired native snapshot")
        for i, desc in enumerate(banks):
            filename = f"{n}.{i+1}.raw"
            if (desc.get("file") != filename
                    or desc.get("bank") != ("MEM1", "MEM2")[i]
                    or desc.get("bytes") != SIZE[i]
                    or desc.get("copy_verified") is not True):
                raise ValueError("Unexpected native pair metadata")
            sha = desc.get("sha256")
            if not isinstance(sha, str) or len(sha) != 64:
                raise ValueError("Invalid hash provenance")
            if src._hash_file(src._file(where, filename, SIZE[i])) != sha.lower():
                raise ValueError("Archived bank SHA mismatch")
    return {n: where for n in sorted(seen)}

def _get(rd):
    result = src._sample(rd)
    u = rd.u32
    field = u(roster.GOLF_FIELD_STATIC)
    config = u(roster.GOLF_CONFIG_STATIC)
    pin = u(field + 0x44)
    start_obj = u(field + 0x50)
    pm = u(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    rec = pm + 4 + result["selected_index"] * roster.ROSTER_STRIDE
    ball = u(rec + 0x88)
    if (roster._bank(ball, 0x108) != "MEM2"
            or u(ball + 0x4C) != ball + 0x30):
        raise ValueError("Source-selected ball object/selfref invalid")
    if (roster._bank(pin, 0x50) != "MEM2"
            or roster._bank(config, 0xC8) != "MEM2"
            or roster._bank(start_obj, 0x50) != "MEM2"
            or u(pin + 0x4C) != pin + 0x30):
        raise ValueError("Source pin/start/config incomplete")
    result["pin"] = tuple(u(pin + 0x30 + 4*i) for i in range(3))
    # Private identity only; the sanitized report never prints heap pointers.
    result["selected_ball_obj"] = ball
    result["pin_obj"] = pin
    result["start_obj"] = start_obj
    result["field"] = field
    result["cfg_bc"] = u(config+0xBC)
    result["cfg_c0"] = u(config+0xC0)
    result["cfg_c4"] = u(config+0xC4)
    return result

def _diff(a, b):
    if len(a) != len(b):
        raise ValueError("Incompatible source vectors")
    return sum(x != y for x, y in zip(a,b))

def _f32_numeric_middle(word: int) -> float:
    """Decode one source-backed, BE float32 component; never expose its value."""
    if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
        raise ValueError("Invalid private middle-component float32 word")
    value = struct.unpack(">f", struct.pack(">I", word))[0]
    if not math.isfinite(value):
        raise ValueError("Nonfinite middle-component source value")
    return value


def _middle_direction(a: int, b: int) -> str:
    before, after = _f32_numeric_middle(a), _f32_numeric_middle(b)
    return "increasing" if after > before else ("decreasing" if after < before else "unchanged")


def middle_component_study(samples: dict[int, dict]) -> dict:
    """One source-selected 0x34 scalar, with explicit negative controls.

    Input source pointers/float words remain in RAM-only local structures.
    A human filename/phase hint is not a machine-verified physics clock.
    """
    if set(samples) != set(range(1, 8)):
        raise ValueError("Exactly seven source-gated samples required")
    edges = []
    for before, after in ((5, 6), (6, 7), (5, 7)):
        a, b = samples[before], samples[after]
        if (a["selected_index"] != b["selected_index"]
                or a["hole"] != b["hole"]
                or any(a[k] != b[k] for k in
                       ("selected_ball_obj", "pin_obj", "start_obj", "field"))):
            raise ValueError("Wedge source owner or object identity changed")
        if any(a[k] != b[k] for k in ("cfg_bc", "cfg_c0", "cfg_c4")):
            raise ValueError("Wedge Config selector changed")
        ta, tb = a["triplets"], b["triplets"]
        for key in ("ball_object_0x030", "ball_cache_0x0cc",
                    "source_current_start"):
            if len(ta[key]) != 3 or len(tb[key]) != 3:
                raise ValueError("Incomplete source selected triplet")
        if len(a["pin"]) != 3 or len(b["pin"]) != 3:
            raise ValueError("Incomplete source pin vector")
        if (ta["source_current_start"] != tb["source_current_start"]
                or a["pin"] != b["pin"]):
            raise ValueError("Wedge tee or pin changed; cannot isolate ball scalar")
        edges.append({
            "transition": f"{before}_to_{after}",
            "selected_ball_plus_0x34_direction": _middle_direction(
                ta["ball_object_0x030"][1], tb["ball_object_0x030"][1]),
            "selected_cache_plus_0xD0_direction": _middle_direction(
                ta["ball_cache_0x0cc"][1], tb["ball_cache_0x0cc"][1]),
            "start_middle_direction": _middle_direction(
                ta["source_current_start"][1], tb["source_current_start"][1]),
            "pin_middle_direction": _middle_direction(a["pin"][1], b["pin"][1]),
            "source_ball_pointer_unchanged": True,
            "source_owner_hole_config_and_geometry_stable": True,
        })
    return {
        "kind": "P0-SANITIZED-SOURCE-SELECTED-BALL-MIDDLE-F32-DIRECTION",
        "relative_ball_object_offset": "+0x34",
        "component_index_zero_based": 1,
        "candidate_role": "unverified_vertical_height_hypothesis",
        "human_phase_order_independently_verified": False,
        "original_banks_integrity_gate_inherited": True,
        "source_global_control_measured_in_this_reader": False,
        "source_global_owner_crosscheck_required": True,
        "middle_axis_as_world_y_verified": False,
        "actual_ball_world_xyz_verified": False,
        "same_guest_physics_frame_verified": False,
        "velocity_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
        "wedge_edges": edges,
    }


def summarize(samples: dict[int, dict]) -> dict:
    if set(samples) != set(range(1,8)):
        raise ValueError("Exactly seven numbered samples required")
    records = []
    for n in range(1,8):
        s = samples[n]
        x = s["triplets"]
        ball = x["ball_object_0x030"]
        records.append({
            "number":n,
            "prior_operator_phase_note_UNVERIFIED_MAPPING": PHASE_HINTS[n-1],
            "source_selected_index":s["selected_index"],
            "source_hole":s["hole"],
            "ball_equal_own_start_components":3-_diff(ball,x["source_current_start"]),
            "ball_equal_cache_CC_components":3-_diff(ball,x["ball_cache_0x0cc"]),
            "ball_equal_cache_F0_components":3-_diff(ball,x["ball_cache_0x0f0"]),
            "ball_equal_cache_FC_components":3-_diff(ball,x["ball_cache_0x0fc"]),
            "record_34_38_74_vs_capture_1_changed": [
                s["whole_record"][i//4] != samples[1]["whole_record"][i//4]
                for i in OFFSETS
            ],
        })
    comparisons=[]
    for a,b in EDGES:
        x,y=samples[a],samples[b]
        same=x["selected_index"]==y["selected_index"] and x["hole"]==y["hole"]
        f=x["triplets"]; t=y["triplets"]
        comparisons.append({
            "transition":f"{a}_to_{b}",
            "same_source_selected_slot_and_hole":same,
            "ball_changed_components": _diff(f["ball_object_0x030"],t["ball_object_0x030"]) if same else None,
            "ball_cache_CC_changed":_diff(f["ball_cache_0x0cc"],t["ball_cache_0x0cc"]) if same else None,
            "ball_cache_F0_changed":_diff(f["ball_cache_0x0f0"],t["ball_cache_0x0f0"]) if same else None,
            "ball_cache_FC_changed":_diff(f["ball_cache_0x0fc"],t["ball_cache_0x0fc"]) if same else None,
            "start_changed_components":_diff(f["source_current_start"],t["source_current_start"]) if same else None,
            "pin_changed_components":_diff(x["pin"],y["pin"]) if same else None,
            "pin_object_pointer_identical":x["pin_obj"]==y["pin_obj"],
            "start_object_pointer_identical":x["start_obj"]==y["start_obj"],
            "field_manager_pointer_identical":x["field"]==y["field"],
            "config_BC_identical":x["cfg_bc"]==y["cfg_bc"],
            "config_C0_identical":x["cfg_c0"]==y["cfg_c0"],
            "config_C4_identical":x["cfg_c4"]==y["cfg_c4"],
            "record_34_changed":x["whole_record"][0x34//4]!=y["whole_record"][0x34//4] if same else None,
            "record_38_changed":x["whole_record"][0x38//4]!=y["whole_record"][0x38//4] if same else None,
            "record_74_changed":x["whole_record"][0x74//4]!=y["whole_record"][0x74//4] if same else None,
        })
    try:
        middle_candidate = middle_component_study(samples)
    except ValueError:
        # Preserve the original seven-phase diagnostic when this stricter
        # *optional* scalar study abstains on confounded controls/data.
        middle_candidate = {
            "kind": "P0-SANITIZED-SOURCE-SELECTED-BALL-MIDDLE-F32-DIRECTION",
            "status": "abstained",
            "reason_code": "wedge_identity_controls_or_f32_unqualified",
            "relative_ball_object_offset": "+0x34",
            "middle_axis_as_world_y_verified": False,
            "source_global_control_measured_in_this_reader": False,
            "training_approved": False,
            "allowed_to_publish": False,
            "wedge_edges": [],
        }
    return {
        "kind":"P0-SANITIZED-SEVEN-NUMBERED-SOURCE-PAIR-AUDIT",
        "capture_count":7,
        "archive_sha_verified":True,
        "source_selection_gate_every_capture":True,
        "number_to_human_phase_mapping_independently_verified":False,
        "same_guest_frame_per_pair_machine_verified":False,
        "same_boot_across_pairs_verified":False,
        "actual_ball_world_xyz_verified":False,
        "ball_velocity_verified":False,
        "game_power_ram_verified":False,
        "impact_frame_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
        "samples":records,
        "comparisons":comparisons,
        "ball_middle_component_hypothesis":middle_candidate
    }

def analyze(archive:Path):
    folders=_check_archive(archive)
    with ExitStack() as stack:
        snapshots={}
        for n in range(1,8):
            mm=[]
            for i,size in enumerate(SIZE):
                p=src._file(folders[n],f"{n}.{i+1}.raw",size)
                f=stack.enter_context(p.open("rb"))
                mm.append(stack.enter_context(mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)))
            snapshots[n]=_get(roster.TwoBankReader(*mm))
        report = summarize(snapshots)
    # Re-check ORIGINAL archived bank SHA after read, not only before mmap.
    # This catches a file changed during the audit without exposing a digest.
    _check_archive(archive)
    return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    args=p.parse_args(argv)
    try:
        report=analyze(args.archive)
    except (ValueError, OSError, TypeError, KeyError, OverflowError):
        print("P0 seven-pair source audit ABSTAINED: invalid native pairing, SHA, source scene/ball/pin, or private archive",file=sys.stderr)
        return 2
    print(json.dumps(report,indent=2,sort_keys=True,allow_nan=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
