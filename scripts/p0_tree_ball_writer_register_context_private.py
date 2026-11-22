#!/usr/bin/env python3
"""P0 original Rev1 PPC receiver-register triage for Ball field writers.

Source code-only, original SHA/scene/94-tree/KCol qualified MEM1 input.
Unlike the previous broad D-form displacement audit, this one compares
the EXACT store instruction sites in their contiguous triplets, their
base GPRs, FPR sources and nearest bounded syntactic producers. It also
tests the seven 'lwz +0x4C; stfs 0/4/8' candidates against the original
instruction sites, verifies no obvious intervening GPR clobber, and
enumerates STATIC BL callers of two published function entries.

A common register is NOT a proven active Ball 'this' pointer; independent
producer/receiver dataflow, conditional paths and dynamic execution remain
unresolved. No original PPC word values, RAM pointers, game XYZ, source
code bytes or private filenames printed. No Dolphin, gameplay/video,
guest writes, capture, new swings or training.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import p0_tree_ball_source_store_inventory_private as first
import audit_p0_seven_numbered_source_pairs_private as seven

MEM1=0x80000000
# Exact SOURCE-relative public locations returned by original first-pass
# SHA-qualified scan. Grouping names/field roles remain hypotheses.
TRIPLETS={
    "Ball_current_translation_candidate_direct_A":(
        "Ball", (0x3E48,0x3E4C,0x3E50), (0x30,0x34,0x38)),
    "Ball_current_translation_candidate_direct_B":(
        "Ball", (0x3EAC,0x3EB0,0x3EB4), (0x30,0x34,0x38)),
    "Ball_cache_CC_D0_D4_in_fn_80299C70":(
        "Ball", (0x2D04,0x2D0C,0x2D14),(0xCC,0xD0,0xD4)),
    "Ball_cache_F0_F4_F8_in_fn_80299C70":(
        "Ball", (0x2F6C,0x2F70,0x2F74),(0xF0,0xF4,0xF8)),
    "Ball_cache_FC_100_104_in_fn_80299C70":(
        "Ball", (0x2FA8,0x2FAC,0x2FB0),(0xFC,0x100,0x104)),
    "Ball_structural_AC_B0_B4_A":(
        "Ball",(0x0AE4,0x0AE8,0x0AEC),(0xAC,0xB0,0xB4)),
    "Ball_structural_AC_B0_B4_B":(
        "Ball",(0x1508,0x1510,0x1518),(0xAC,0xB0,0xB4)),
    "Ball_structural_AC_B0_B4_C":(
        "Ball",(0x358C,0x3590,0x3594),(0xAC,0xB0,0xB4)),
}
POINTER_WRITERS={
    "Ball_ptr_writer_1788":("Ball",0x1788,(0x179C,0x17AC,0x17BC)),
    "Ball_ptr_writer_1AAC":("Ball",0x1AAC,(0x1ABC,0x1ACC,0x1ADC)),
    "Ball_ptr_writer_38DC":("Ball",0x38DC,(0x38F4,0x3910,0x3918)),
    "Player_ptr_writer_1D88":("Player",0x1D88,(0x1D8C,0x1D94,0x1D9C)),
    "Player_ptr_writer_2200":("Player",0x2200,(0x2204,0x220C,0x2214)),
    "PlayerManager_ptr_writer_0BE0":(
        "PlayerManager",0x0BE0,(0x0BE8,0x0BF0,0x0BF4)),
    "PlayerManager_ptr_writer_0C70":(
        "PlayerManager",0x0C70,(0x0C80,0x0C84,0x0C88)),
}
ENTRY_TARGETS={
    "ball_cache_fn_80299C70":0x80299C70,
    "player_translation_fn_802A0320":0x802A0320,
}
CALLERS={
    "Ball":first.SOURCE_UNITS["Ball"],
    "Simulation":first.SOURCE_UNITS["Simulation"],
    "Player":first.SOURCE_UNITS["Player"],
    "PlayerManager":first.SOURCE_UNITS["PlayerManager"],
    "FieldManager":first.units.UNITS["FieldManager"],
}
MAX_CONTEXT_BACK=20
MAX_EXAMPLE=14


def srcpc(unit,offset):
    a,b=first.SOURCE_UNITS[unit]
    pc=a+offset
    if offset<0 or pc+4>b or pc%4:
        raise ValueError("Source candidate outside qualified public unit")
    return pc


def op_kind(word):
    op=word>>26
    names={32:"lwz",36:"stw",48:"lfs",52:"stfs",49:"lfsu",
           50:"lfd",53:"stfsu",18:"b/bl",16:"bc",
           14:"addi",15:"addis",31:"X-form",59:"FP_single",
           63:"FP_double",19:"XL-form"}
    return names.get(op,"other_op")


def is_control(word):
    op=word>>26
    if op in (16,17,18):
        return True
    if op==19 and ((word>>1)&1023) in (16,50,528):
        return True
    return False


def may_write_gpr(word,reg):
    # Only a bounded, conservative syntactic subset is known.
    # Unknown instructions could overwrite rX: never promote
    # no-clobber to full provenance or receiver type proof.
    return first.gpr_clobber(word,reg)


def nearest_fp_producer(read,pc,fpr,lo):
    # Only a bounded PRECEDING linear-window heuristic: a branch
    # terminates static register provenance. FP arithmetic is treated
    # as an opaque writer, not decoded into physics semantics.
    prior=[]
    for j in range(1,MAX_CONTEXT_BACK+1):
        at=pc-4*j
        if at<lo:
            break
        w=read(at)
        if is_control(w):
            return {
                "classification":"unresolved_prior_control_flow",
                "within_bounded_linear_window":False}
        op=w>>26
        if op in (48,49,50,51,59,63) and (w>>21)&31==fpr:
            return {
                "classification":op_kind(w),
                "source_site_delta_instructions_before_store":j,
                "same_fpr_index":fpr,
                "op_is_definite_last_dynamic_producer":False,
                "within_bounded_linear_window":True,
            }
        if len(prior)>MAX_CONTEXT_BACK:
            break
    return {"classification":"no_linear_FPR_producer_found",
            "within_bounded_linear_window":False}


def direct_triplets(read):
    result={}
    for label,(unit,off,displacements) in TRIPLETS.items():
        pc=[srcpc(unit,i) for i in off]
        ops=[first.form(read(x)) for x in pc]
        if any(not o or o["op"]!=52 for o in ops):
            raise ValueError("Original source PPC float-store triple changed")
        if [o["offset"] for o in ops]!=list(displacements):
            raise ValueError("Original exact PPC triplet offsets changed")
        bases=[o["base"] for o in ops]
        fprs=[o["register"] for o in ops]
        low=first.SOURCE_UNITS[unit][0]
        result[label]={
            "source_unit":unit,
            "triplet_source_instruction_offsets":[f"+0x{x:04X}" for x in off],
            "member_displacements":[f"+0x{x:03X}" for x in displacements],
            "source_store_base_gpr_indices":bases,
            "all_three_stores_use_same_register":len(set(bases))==1,
            "source_fp_register_indices":fprs,
            "nearest_linear_fpr_producer_syntax":[
                nearest_fp_producer(read,s,fpr,low)
                for s,fpr in zip(pc,fprs)],
            "store_receiver_is_selected_active_Ball_proven":False,
            "source_store_executed_during_tree_contact_proven":False,
        }
    return result


def pointer_chains(read):
    result={}
    for label,(unit,load,offs) in POINTER_WRITERS.items():
        pc=srcpc(unit,load)
        first_word=first.form(read(pc))
        if first_word is None or first_word["op"]!=32 or (
                first_word["offset"]!=0x4C):
            raise ValueError("Original candidate pointer load changed")
        ptr=first_word["register"]
        stores=[first.form(read(srcpc(unit,o))) for o in offs]
        if any(not o or o["op"]!=52 for o in stores):
            raise ValueError("Original pointer candidate store changed")
        if [o["offset"] for o in stores]!=[0,4,8]:
            raise ValueError("Original pointer target triplet changed")
        if not all(o["base"]==ptr for o in stores):
            raise ValueError("Original FP pointer register changed between stores")
        intervening=[]
        until=srcpc(unit,offs[-1])
        for at in range(pc+4,until,4):
            word=read(at)
            if is_control(word):
                intervening.append("control_transfer")
            if may_write_gpr(word,ptr):
                intervening.append("known_gpr_destination")
        # Suspected receiver is the GPR used as base of lwz +0x4C,
        # not necessarily the active Ball. No CFG/dataflow identity.
        result[label]={
            "source_unit":unit,
            "source_pointer_load_relative":f"+0x{load:04X}",
            "source_pointer_triplet_stores_relative":[
                f"+0x{o:04X}" for o in offs],
            "source_receiver_gpr_index":first_word["base"],
            "source_pointer_gpr_index":ptr,
            "all_three_component_store_bases_match_loaded_ptr":True,
            "control_or_known_gpr_clobber_between_load_and_last_store":
                bool(intervening),
            "source_receiver_equals_active_live_Ball_proven":False,
            "native_exec_in_original_live_shot_proven":False,
        }
    return result


def entry_callsites(read):
    results={}
    for name,target in ENTRY_TARGETS.items():
        sites=[]
        for unit,(lo,hi) in CALLERS.items():
            for pc in range(lo,hi,4):
                decoded=first.units.direct_b(pc,read(pc))
                if decoded is not None and decoded[1] and decoded[0]==target:
                    sites.append({
                        "caller_source_unit":unit,
                        "caller_unit_relative_offset":f"+0x{pc-lo:04X}",
                        "direct_BL_not_verified_executed":True,
                    })
        results[name]={
            "qualified_direct_bl_to_exact_entry_count":len(sites),
            "bounded_public_source_callsites":sites[:MAX_EXAMPLE],
            "additional_sites_not_displayed":max(0,len(sites)-MAX_EXAMPLE),
            "indirect_caller_paths_proven_exhausted":False,
            "executed_for_current_selected_Ball_proven":False,
        }
    return results


def inspect(read):
    return {
        "kind":"P0_ORIGINAL_TREE_BALL_WRITER_REGISTER_CONTEXT_V1",
        "status":"SOURCE_QUALIFIED_STATIC_RECEIVER_AND_FP_PROVENANCE_CANDIDATES",
        "original_native_triplet_store_gpr_equality":direct_triplets(read),
        "original_nested_pointer_store_receiver_syntax":pointer_chains(read),
        "static_direct_exact_entry_calls":entry_callsites(read),
        "selected_ball_receiver_binding_proven":False,
        "runtime_tree_impact_instruction_executed_proven":False,
        "physical_tree_wood_or_leaves_material_branch_proven":False,
        "guest_ball_velocity_proven":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    if capture not in range(1,8):
        raise ValueError("Invalid original capture")
    # Includes original 94 x 84 native scene/owner gates and 5+7 KCol BLs.
    original=first.run(archive,capture)
    if not (original["original_native_archive_sha_qualified"] and
            original["original_native_94_tree_receiver_loop_qualified"] and
            original["original_5_ball_to_kcol_7_reverse_calls_gated"]):
        raise ValueError("Original native source gates changed")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for n,size in enumerate(seven.SIZE,1):
            path=seven.src._file(folders[capture],f"{capture}.{n}.raw",size)
            h=stack.enter_context(path.open("rb"))
            banks.append(stack.enter_context(mmap.mmap(
                h.fileno(),0,access=mmap.ACCESS_READ)))
        def read(pc):
            if pc%4 or pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Original code pointer out of MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        outcome=inspect(read)
    seven._check_archive(archive)
    return {**outcome,
            "original_sha_scene_tree_and_kcol_gates_verified":True,
            "original_capture_number":capture}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=p.parse_args(argv)
    try:
        print(json.dumps(run(args.archive,args.capture),
                         sort_keys=True,separators=(",",":"),allow_nan=False))
        return 0
    except (ValueError,OSError,KeyError,IndexError,TypeError,
            AttributeError,OverflowError,struct.error) as exc:
        print(json.dumps({"kind":"P0_ORIGINAL_TREE_BALL_WRITER_REGISTER_CONTEXT_V1",
                          "status":"ABSTAIN_SOURCE_GATES_OR_RECEIVER_SYNTAX",
                          "training_approved":False}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
