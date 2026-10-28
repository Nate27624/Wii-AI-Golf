"""S002 offline Rev1 two direct callers of selected-player rotation updater.

Only existing private B0 images; validates source-gated scene/roster snapshot.
Records PC, opcode and bounded call argument dataflow, never game RAM contents.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_golf_aim_ppc_offsets_private as source
import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_four_phase_private as four
import audit_selected_ball_start_link_private as selected

CALLS = (
    (0x802A293C, 0x807D0334, 0x802A2968, 0x4BFFC3C5),
    (0x802A2B00, 0x807D0334, 0x802A2B0C, 0x4BFFC221),
)
CALLEE = 0x8029ED2C
MANAGER_SELECTED_OFFSET = 0x334
CALLEE_TRANSFER_PC = 0x8029ED50
CALLEE_TRANSFER_WORD = 0x7C7D1B78

def decode_bl_target(word: int, pc: int) -> int | None:
    if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
        raise ValueError("Malformed instruction word")
    if (word >> 26) != 18 or not (word & 1):
        return None
    disp = word & 0x03FFFFFC
    if disp & 0x02000000:
        disp -= 0x04000000
    return ((disp if word & 2 else pc + disp) & 0xFFFFFFFF)

def check_source(read_u32) -> dict:
    if read_u32(CALLEE_TRANSFER_PC) != CALLEE_TRANSFER_WORD:
        raise ValueError("Callee does not preserve incoming r3 in r29")
    checks=[]
    for load_pc, load_word, call_pc, call_word in CALLS:
        if not (0x802A2210 <= load_pc < call_pc < 0x802A3560):
            raise ValueError("Caller outside Rev1 PlayerManager source")
        if (read_u32(load_pc) != load_word or
                read_u32(call_pc) != call_word or
                decode_bl_target(call_word, call_pc) != CALLEE):
            raise ValueError("Source-selected pointer / BL call signature mismatch")
        # A fully *bounded* region after lwz r3,+0x334(r29) may include reads
        # through r3 and moves of r4/r5, but must not modify r3 before the call.
        # The two validated sequences are short and have fixed fingerprints.
        expected_between = {
            0x802A293C: {
                0x802A2940: 0xC022C8A0,
                0x802A2944: 0xC0030074,
                0x802A2948: 0xFC010000,
                0x802A294C: 0x7C000026,
                0x802A2950: 0x54001FFE,
                0x802A2954: 0x68000001,
                0x802A2958: 0x2C000000,
                0x802A295C: 0x408200FC,
                0x802A2960: 0x7F84E378,
                0x802A2964: 0x7F65DB78,
            },
            0x802A2B00: {
                0x802A2B04: 0x7F84E378,
                0x802A2B08: 0x7F65DB78,
            },
        }
        if any(read_u32(pc) != word
               for pc, word in expected_between[load_pc].items()):
            raise ValueError("Pointer register provenance region mutated")
        checks.append({
            "source_pc": f"0x{load_pc:08X}",
            "call_pc": f"0x{call_pc:08X}",
            "call_target_pc": f"0x{CALLEE:08X}",
            "caller_source_unit": "RPGolPlayerManager.cpp",
            "argument_r3_loaded_from_r29_plus_0x334": True,
            "r3_preserved_to_direct_call_on_checked_path": True,
        })
    return {
        "kind": "local-private-golf-selected-player-rotation-callers",
        "source_direct_calls_verified": len(checks),
        "callee_preserves_argument_r3_in_r29": True,
        "call_sites": checks,
        "manager_r29_runtime_identity_independently_verified": False,
        "selected_player_pointer_source_contract_verified": False,
        "actual_shot_heading_verified": False,
        "ball_motion_verified": False,
        "training_allowed": False,
        "allowed_to_publish": False,
    }

def run_local(folder: Path):
    root = selected.DATA_ROOT.resolve(strict=True)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Missing private B0 source folder")
    folder=folder.resolve(strict=True)
    if folder == root or not folder.is_relative_to(root):
        raise ValueError("Source folder outside private Data root")
    source_gate=source.run_local(folder)
    if source_gate.get("source_selected_record_snapshot_gated") is not True:
        raise ValueError("Selected-player source gate absent")
    manifest=four._validate_manifest(folder)
    files={key: four._approved_bank(folder,f"B0-{key}.bin",
            roster.MEM1_SIZE if key=="MEM1" else roster.MEM2_SIZE)
            for key in ("MEM1","MEM2")}
    if any(four._hash(file)!=manifest["B0"]["sha256"][key]
            for key,file in files.items()):
        raise ValueError("Source image SHA changed")
    with ExitStack() as stack:
        images=[]
        for file in files.values():
            handle=stack.enter_context(file.open("rb"))
            images.append(stack.enter_context(
                mmap.mmap(handle.fileno(),0,access=mmap.ACCESS_READ)))
        reader=roster.TwoBankReader(*images)
        result=check_source(reader.u32)
        safe, private=selected.analyze_one(reader.u32,reader.header())
        if safe.get("selected_record_pointer_matches_code_defined_stride") is not True:
            raise ValueError("Selected record source pointer gate failed")
        manager=reader.u32(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
        selected_record=manager+4+private["selected_index"]*roster.ROSTER_STRIDE
        if reader.u32(manager+MANAGER_SELECTED_OFFSET)!=selected_record:
            raise ValueError("Manager selected-pointer link mismatch")
        result["selected_player_pointer_source_contract_verified"]=True
        result["game_id"]="RSPE01"
        result["disc_revision"]=1
        return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        print(json.dumps(run_local(args.private_root),indent=2,sort_keys=True))
        return 0
    except (OSError,ValueError,KeyError,TypeError,OverflowError) as e:
        print("Source caller verification FAILED CLOSED:",e,file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
