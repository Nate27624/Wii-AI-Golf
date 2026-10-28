"""Offline source-scope r29 register provenance triage, no runtime side effects.

Find PPC source-literal candidates for assigning r29 in RPGolPlayerManager.cpp
before two already-verified calls to selected golfer angle updater.
Print bounded nearby instructions for operator/source owner review. This is NOT
a control-flow proof of manager-this identity.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_start_link_private as selected
import audit_selected_ball_four_phase_private as four
import audit_golf_selected_aim_callers_private as caller
import audit_golf_aim_ppc_context_private as context

SOURCE_START = 0x802A2210
SOURCE_END = 0x802A3560
MAX_NEARBY = 4
OUTPUT_RADIUS_WORDS = 12

def r29_candidate(word: int) -> str | None:
    """Conservative mnemonic class, never assert ownership or dynamic execution."""
    if type(word) is not int or not 0 <= word < 2**32:
        raise ValueError("Invalid PPC instruction")
    if word == 0x7C7D1B78:
        return "mr_r29_from_r3"
    opcode = word >> 26
    rt=(word >> 21)&31
    ra=(word >> 16)&31
    if opcode in (14,15,32,33,34,35,40,41,42,43,46) and rt==29:
        return "GPR_r29_destination_candidate"
    if opcode in (20,21,23,24,25,26,27,28,29) and ra==29:
        return "GPR_r29_destination_candidate"
    if opcode==31 and ra==29 and ((word>>1)&0x3ff)==444:
        return "or_r29_destination"
    return None

def summarize(get_word) -> dict:
    # The prior verifier already checked both caller/callee signatures.
    verified=caller.check_source(get_word)
    candidates=[]
    for pc in range(SOURCE_START,SOURCE_END,4):
        kind=r29_candidate(get_word(pc))
        if kind:
            candidates.append({"pc":pc,"kind":kind})
    blocks=[]
    for load_pc,_,call_pc,_ in caller.CALLS:
        earlier=[x for x in candidates if x["pc"] < load_pc]
        near=earlier[-MAX_NEARBY:]
        pc_spans=[(x["pc"], max(SOURCE_START,x["pc"]-4*OUTPUT_RADIUS_WORDS),
                    min(SOURCE_END,x["pc"]+4*(OUTPUT_RADIUS_WORDS+1)))
                  for x in near]
        lines=[]
        for anchor,start,end in pc_spans:
            lines.append({
                "r29_candidate_pc":f"0x{anchor:08X}",
                "instructions":[
                    f"0x{pc:08X} 0x{get_word(pc):08X} {context.decode(get_word(pc),pc)}"
                    for pc in range(start,end,4)
                ]
            })
        blocks.append({
            "selected_record_load_pc":f"0x{load_pc:08X}",
            "selected_record_call_pc":f"0x{call_pc:08X}",
            "nearest_r29_definitions": [
                {"pc":f"0x{x['pc']:08X}","kind":x["kind"]} for x in near],
            "source_instruction_context":lines
        })
    return {
        "kind":"PRIVATE-Rev1-PlayerManager-r29-register-source-triage",
        "source_unit":"RPGolPlayerManager.cpp",
        "checked_direct_calls":verified["source_direct_calls_verified"],
        "caller_chains":blocks,
        "static_candidate_count_all_manager_source":len(candidates),
        "manager_this_register_proven":False,
        "dynamic_execution_proven":False,
        "absolute_shot_heading_verified":False,
        "ball_motion_verified":False,
        "training_allowed":False,
        "allowed_to_publish":False,
        "interpretation_note":"r29 matches are static register-def candidates; function entry, CFG and full register dataflow still require review."
    }

def run_local(folder:Path)->dict:
    root=selected.DATA_ROOT.resolve(strict=True)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Missing private source folder")
    folder=folder.resolve(strict=True)
    if folder==root or not folder.is_relative_to(root):
        raise ValueError("Source outside private data root")
    manifest=four._validate_manifest(folder)
    paths={key:four._approved_bank(folder,f"B0-{key}.bin",
              roster.MEM1_SIZE if key=="MEM1" else roster.MEM2_SIZE)
              for key in ("MEM1","MEM2")}
    if any(four._hash(p)!=manifest["B0"]["sha256"][key]
           for key,p in paths.items()):
        raise ValueError("Private source bank SHA mismatch")
    with ExitStack() as stack:
        maps=[]
        for p in paths.values():
            handle=stack.enter_context(p.open("rb"))
            maps.append(stack.enter_context(
                mmap.mmap(handle.fileno(),0,access=mmap.ACCESS_READ)))
        reader=roster.TwoBankReader(*maps)
        safe,_=selected.analyze_one(reader.u32,reader.header())
        if safe.get("selected_record_pointer_matches_code_defined_stride") is not True:
            raise ValueError("Selected player source gate failed")
        return summarize(reader.u32)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root",required=True,type=Path)
    args=p.parse_args(argv)
    try:
        print(json.dumps(run_local(args.private_root),indent=2,sort_keys=True))
    except (OSError,ValueError,TypeError,KeyError,OverflowError) as e:
        print("PPC manager r29 source triage failed closed:",e,file=sys.stderr)
        return 1
    return 0

if __name__=="__main__":
    raise SystemExit(main())
