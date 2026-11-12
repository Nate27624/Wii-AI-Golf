#!/usr/bin/env python3
"""Original Rev1 three initializer BLs: GPR3 receiver provenance source census.

Operator's SHA-gated original report confirms exactly three Ball direct
BL callers at +0x2B60, +0x320C, +0x3248 to +0x3108, the native routine
containing 'stb r5,+0x5C(r3)' preceded by 'li r5,1'. Global registration
is separately at +0x3080 'bl Ball+0x3BA0', immediately followed by
+0x3084 'stw r3,-23304(r13)'. This audit reads only the original
seven-pair SHA-qualified native bank, checks all four source anchors
and characterizes the three r3 arguments without asserting object
alias or executing a guest instruction.

Only source-relative sites, opcode classes, GPR indices and integer
displacements are reported. Lexical backward provenance, even with
no local branch, is not complete CFG/SSA or runtime identity evidence.
No native PPC words, private ROM/RAM, heap addresses, XYZ, paths,
Dolphin, video, new captures, guest writes or training.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import p0_ball_global_5c_init_caller_join_private as old
import p0_ball_global_5c_zero_witness_private as register
import p0_ball_cache_cfg_reachability_private as cfg
import p0_ball_global_byte_writer_context_private as native
import p0_ball_global_5c_initializer_r26_private as initializer
import audit_p0_seven_numbered_source_pairs_private as seven

BALL=old.BALL
LO,HI=old.LO,old.HI
MEM1=old.MEM1
TARGET=BALL+0x3108
CALLERS=(BALL+0x2B60,BALL+0x320C,BALL+0x3248)
GLOBAL_SLOT=initializer.source.GLOBAL_SLOT
LOOKBACK=28
CONTEXT_BEFORE=12
CONTEXT_AFTER=3
DETAIL_LIMIT=10


def label(pc):
    return old.label(pc)


def direct_calls(read):
    found=[]
    for pc in range(LO,HI,4):
        t=cfg.decode_transfer(pc,read(pc))
        if t["kind"]=="direct_bl_call" and t["target"]==TARGET:
            found.append(pc)
    if tuple(found)!=CALLERS:
        raise ValueError("Exact original three native initializer direct BL sites changed")
    g=cfg.decode_transfer(old.CALL,read(old.CALL))
    if g["kind"]!="direct_bl_call" or g["target"]!=old.LOCAL_TARGET:
        raise ValueError("Separate original global registration direct BL changed")
    return {
        "original_exact_initializer_target":label(TARGET),
        "original_exact_direct_initializer_BL_sites":[label(x) for x in found],
        "global_registration_direct_BL_site":label(old.CALL),
        "global_registration_callee_site":label(old.LOCAL_TARGET),
        "registration_is_one_of_three_direct_initializer_BLs":False,
        "all_direct_Ball_unit_initializer_BL_sites_counted":True,
        "whole_game_indirect_and_external_callers_exhausted":False,
        "initializer_object_matches_r13_global_proven":False,
    }


def receiver(read,call,reg=3):
    """Nearest syntactic GPR writer; preserve control/unknown ambiguity."""
    if call not in CALLERS:
        raise ValueError("Unverified source caller")
    defs=[]
    controls=[]
    unknown=[]
    stop=max(LO,call-LOOKBACK*4)
    for pc in range(call-4,stop-4,-4):
        w=read(pc)
        desc=cfg.decode_transfer(pc,w)
        if desc["kind"]!="linear_not_decoded_control":
            controls.append({
                "source_site":label(pc),
                "transfer_category":desc["kind"],
                "source_preceding_call_may_be_a_path_barrier":True,
            })
        known,writers=register.gpr_writes_qualified(w)
        if not known:
            unknown.append({
                "source_site":label(pc),
                "source_primary_opcode_number":w>>26,
                "source_X_form_opcode_number":((w>>1)&1023)
                    if w>>26==31 else None,
            })
        if known and reg in writers:
            i=native.typed_instruction(pc,w)
            mem=initializer.source.form(w)
            is_global=bool(
                mem and (mem["op"],mem["rT"],mem["rA"],mem["disp"])
                ==(32,reg,13,GLOBAL_SLOT))
            defs.append({
                "source_site":label(pc),
                "syntactic_instruction_category":i,
                "is_direct_lwz_from_exact_r13_global_slot":is_global,
                "intervening_control_site_count":len(controls),
                "intervening_unknown_opcode_count":len(unknown),
                "nearest_lexical_GPR_writer_is_reaching_on_actual_path_proven":False,
            })
            break
    # Distinguish "none found" from "definitely receives entry r3".
    result={
        "caller_BL_site":label(call),
        "argument_GPR":reg,
        "nearest_syntactic_definition":defs[0] if defs else None,
        "bounded_preceding_control_sites":controls[:DETAIL_LIMIT],
        "bounded_unknown_semantics_sites":unknown[:DETAIL_LIMIT],
        "additional_control_sites_not_displayed":max(0,len(controls)-DETAIL_LIMIT),
        "additional_unknown_sites_not_displayed":max(0,len(unknown)-DETAIL_LIMIT),
        "source_immediate_global_slot_load_before_call_no_barriers":
            bool(defs and defs[0]["is_direct_lwz_from_exact_r13_global_slot"]
                 and not controls and not unknown),
        "actual_receiver_same_object_as_global_registration_proven":False,
        "function_boundary_and_all_predecessors_qualified":False,
    }
    return result


def context(read,call):
    lo=max(LO,call-CONTEXT_BEFORE*4)
    hi=min(HI,call+(CONTEXT_AFTER+1)*4)
    return {
        "source_call_site":label(call),
        "original_bounded_lexical_instruction_categories":[
            native.typed_instruction(pc,read(pc))
            for pc in range(lo,hi,4)],
        "lexical_window_is_complete_runtime_execution_path":False,
    }


def inspect(read):
    old.qualified(read)
    inbound=direct_calls(read)
    # Confirm the exact initializer source already SHA-gated by old.
    initializer.init(read)
    return {
        "kind":"P0_ORIGINAL_BALL_GLOBAL_5C_INIT_THREE_CALLER_R3_V1",
        "status":"SHA_QUALIFIED_NATIVE_INITIALIZER_R3_SOURCE_CONTEXT",
        "exact_native_source_caller_targets":inbound,
        "initializer_callsite_source_r3_ancestry":[receiver(read,pc) for pc in CALLERS],
        "initializer_callsite_bounded_contexts":[context(read,pc) for pc in CALLERS],
        "global_slot_value_aliases_initializer_receiver_proven":False,
        "initialization_and_zero_clear_same_object_verified":False,
        "selected_live_Ball_object_or_native_impact_verified":False,
        "wood_versus_foliage_material_physics_verified":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    prior=old.run(archive,capture)
    if not (prior.get("original_SHA_scene_native_source_verified")
            and prior.get("original_capture")==capture):
        raise ValueError("Original SHA and native source qualification failed")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            p=seven.src._file(roots[capture],f"{capture}.{i}.raw",size)
            f=stack.enter_context(p.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)))
        def read(pc):
            if pc%4 or pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Original source outside SHA-gated MEM1 bank")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        result=inspect(read)
    seven._check_archive(archive)
    return {**result,"original_archive_and_scene_SHA_gates_verified":True,
            "original_capture":capture}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",type=Path,required=True)
    parser.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=parser.parse_args(argv)
    try:
        print(json.dumps(run(args.archive,args.capture),
                         sort_keys=True,separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,
            OverflowError,AttributeError,struct.error) as exc:
        print(json.dumps({
            "kind":"P0_ORIGINAL_BALL_GLOBAL_5C_INIT_THREE_CALLER_R3_V1",
            "status":"ABSTAIN_ORIGINAL_SHA_OR_NATIVE_SOURCE",
            "failure_exception_class":type(exc).__name__,
            "exception_message_or_original_data_emitted":False,
            "training_approved":False},sort_keys=True))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
