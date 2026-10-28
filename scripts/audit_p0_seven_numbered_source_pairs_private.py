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
    if (roster._bank(pin, 0x50) != "MEM2"
            or roster._bank(config, 0xC8) != "MEM2"
            or roster._bank(start_obj, 0x50) != "MEM2"
            or u(pin + 0x4C) != pin + 0x30):
        raise ValueError("Source pin/start/config incomplete")
    result["pin"] = tuple(u(pin + 0x30 + 4*i) for i in range(3))
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
        "comparisons":comparisons
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
        return summarize(snapshots)

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
