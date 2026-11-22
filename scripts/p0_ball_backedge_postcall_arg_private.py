#!/usr/bin/env python3
"""Original Rev1 Ball cache predicate: post-call r4 and byte-flag receiver.

Only original seven-pair SHA/source-gated Rev1 archive is read. The
possible CC-copy backedge tests r0 != 0 and signed(r28) < 0; actual
instructions show lbz r0,+0x5C(r3) and mr r28,r4. IMPORTANT: mr r28,r4
follows a linked BL at Ball+0x2CB0, and r4 is volatile under PPC EABI.
Therefore r28 is NOT shown to equal the function-entry r4 and a caller
li r4 value must NOT be used to rule in/out the backedge.

This audit verifies the exact source instructions, reports the
post-call r4 uncertainty, extracts source-relative called-target
class, and bounded syntactic r3 origins before the byte load.
It also inventories source r4 assignments in the two known static
callers without claiming they survive the intervening BL.
No dynamic execution/complete CFG/heap identity/wood-versus-leaves
collision proof, ROM words, private pointers, positions or video.
No Dolphin/game interaction, new swings, memory writes or training.
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
import p0_ball_cc_backedge_signed_operands_private as signed
import p0_ball_cc_global_caller_source_private as caller
import p0_ball_cache_cfg_reachability_private as cfg
import p0_ball_cache_r27_lineage_private as lineage
import audit_p0_seven_numbered_source_pairs_private as seven

BASE=cfg.BASE
MEM1=cfg.MEM1
PRELUDE_CALL=0x2CB0
R28_BIND=0x2CBC
FLAG_LOAD=0x2FBC
MAX_SITES=24


def exact_gpr_sources(read):
    pc=BASE+PRELUDE_CALL
    call=cfg.decode_transfer(pc,read(pc))
    if call["kind"]!="direct_bl_call":
        raise ValueError("Original linked BL before r28 binding missing")
    if not (R28_BIND>PRELUDE_CALL and R28_BIND-PRELUDE_CALL<=16):
        raise ValueError("Unexpected original return-site spacing")
    if (28,"mr",4,None) not in lineage.gpr_writers(read(BASE+R28_BIND)):
        raise ValueError("Original r28 <- postcall r4 changed")
    # Directly after the call, examine only the originally bounded
    # linear instructions (not a dynamic execution trace).
    r4_defs=[]
    for off in range(PRELUDE_CALL+4,R28_BIND,4):
        for dst,typ,src,disp in lineage.gpr_writers(read(BASE+off)):
            if dst==4:
                r4_defs.append({
                    "source_site":cfg.src(BASE+off),"class":typ,
                    "source_gpr_if_decoded":src,"source_offset_if_decoded":disp})
        dec=cfg.decode_transfer(BASE+off,read(BASE+off))
        if dec["kind"]!="linear_not_decoded_control":
            raise ValueError("Additional control transfer between prelude call and r28 binding")
    lo,hi=lineage.inventory.SOURCE_UNITS["Ball"]
    dest=call["target"]
    local=cfg.src(dest) if lo<=dest<hi and dest%4==0 else None
    return {
        "exact_original_source_call_site":cfg.src(pc),
        "exact_source_call_is_linked_BL":True,
        "original_called_target_Ball_unit_relative_if_bounded":local,
        "original_called_target_outside_published_Ball_unit":local is None,
        "r28_bound_from_r4_source_site":cfg.src(BASE+R28_BIND),
        "recognized_intervening_r4_assignments":r4_defs,
        "r4_is_volatile_across_linked_call_under_PPC_ABI":True,
        "r28_equals_original_function_entry_r4_proven":False,
        "r28_runtime_signed_value_proven":False,
        "callee_effect_on_r4_and_returned_state_proven":False,
    }


def exact_flag(read):
    word=read(BASE+FLAG_LOAD)
    # lbz is primary opcode 34, rT=0, rA=3, displacement 92.
    if (word>>26,(word>>21)&31,(word>>16)&31,
        cfg.signed(word&0xFFFF,16))!=(34,0,3,92):
        raise ValueError("Original byte flag load source changed")
    return {
        "source_site":cfg.src(BASE+FLAG_LOAD),
        "operation":"unsigned_load_byte_lbz",
        "destination_register":0,
        "source_base_register":3,
        "source_relative_byte_offset":"+0x05C",
        "possible_unsigned_byte_range":[0,255],
        "fallthrough_condition":"loaded_byte_is_nonzero",
        "source_object_is_selected_live_Ball_proven":False,
        "native_byte_field_semantics_proven":False,
    }


def caller_r4(read):
    out=[]
    for info in caller.CALLERS:
        start,end,call=info["bind"],info["arg"],info["bl"]
        # The earlier source proof checked exact r31/r3 and BL.
        region=caller.caller_receiver_lifetime(read)
        if len(region)!=len(caller.CALLERS):
            raise ValueError("Original callers changed")
        writers=[]
        controls=[]
        # Include caller argument setup after the r3 <- r31 move,
        # ending immediately before the exact BL to the cache routine.
        for off in range(start,call,4):
            word=read(BASE+off)
            for dest,typ,src,disp in lineage.gpr_writers(word):
                if dest==4:
                    item={"source_site":cfg.src(BASE+off),
                          "syntactic_class":typ,
                          "source_GPR_if_decoded":src,
                          "source_displacement_if_decoded":disp}
                    if typ=="addi" and src==0:
                        item["li_signed_immediate_if_literal"]=disp
                    writers.append(item)
            t=cfg.decode_transfer(BASE+off,word)
            if t["kind"]!="linear_not_decoded_control":
                controls.append(cfg.src(BASE+off))
        out.append({
            "caller_direct_BL_site":cfg.src(BASE+call),
            "source_nearby_r4_writer_count":len(writers),
            "closest_bounded_syntactic_r4_definition":
                writers[-1] if writers else None,
            "other_r4_definitions":writers[-MAX_SITES:-1] if len(writers)>1 else [],
            "bounded_caller_control_sites":controls[:MAX_SITES],
            "r4_at_callee_after_intervening_prelude_call_proven":False,
            "r4_original_caller_value_at_actual_execution_proven":False,
        })
    return out


def byte_base_path(read):
    route=signed.witness(read)
    if BASE+FLAG_LOAD not in route:
        raise ValueError("Original backedge witness misses flag load")
    prefix=route[:route.index(BASE+FLAG_LOAD)]
    recognized=[]
    calls=[]
    for pc in prefix:
        for dst,typ,src,disp in lineage.gpr_writers(read(pc)):
            if dst==3:
                recognized.append({
                    "source_site":cfg.src(pc),
                    "GPR_writer_class":typ,
                    "source_reg_if_decoded":src,
                    "source_offset_if_decoded":disp})
        t=cfg.decode_transfer(pc,read(pc))
        if t["kind"]=="direct_bl_call":
            calls.append(cfg.src(pc))
    return {
        "recognized_writers_to_r3_along_static_witness":recognized[-MAX_SITES:],
        "nearest_recognized_r3_writer":recognized[-1] if recognized else None,
        "source_BL_calls_that_can_clobber_r3":calls[-MAX_SITES:],
        "complete_r3_object_identity_qualified":False,
        "original_guest_flag_value_observed":False,
    }


def inspect(read):
    prior=signed.inspect(read)
    if prior["CC_writer_backedge_necessary_source_predicates"] != [
            "r0_not_equal_to_0_for_Ball+0x2FC4_fallthrough",
            "signed_r28_less_than_0_for_Ball+0x2FCC_taken"]:
        raise ValueError("Original PPC EQ/LT source predicates changed")
    return {
        "kind":"P0_ORIGINAL_BALL_BACKEDGE_POSTCALL_R4_AND_FLAG_V1",
        "status":"ORIGINAL_REV1_SHA_QUALIFIED_ARG_AND_FLAG_SYNTAX",
        "native_r28_source_after_prelude_call":exact_gpr_sources(read),
        "native_nonzero_byte_flag_source":exact_flag(read),
        "original_two_callers_r4_source_context":caller_r4(read),
        "source_byte_flag_r3_owner_candidates":byte_base_path(read),
        "backedge_effective_conditions":[
            "byte_at_current_r3_plus_0x5C_nonzero",
            "signed_postcall_r4_copied_to_r28_less_than_zero"],
        "source_input_r4_preserved_across_prelude_BL_proven":False,
        "static_may_reachability_of_CC_copy_proven":True,
        "native_guest_backedge_taken_proven":False,
        "source_selected_Ball_receiver_proven":False,
        "wood_vs_foliage_collision_branch_proven":False,
        "velocity_or_restitution_proven":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    prev=signed.run(archive,capture)
    if not prev.get("original_archive_SHA_and_native_source_gates_verified") or (
            prev.get("original_verified_capture")!=capture):
        raise ValueError("Prior original native source SHA gates failed")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            p=seven.src._file(roots[capture],f"{capture}.{i}.raw",size)
            h=stack.enter_context(p.open("rb"))
            banks.append(stack.enter_context(mmap.mmap(
                h.fileno(),0,access=mmap.ACCESS_READ)))
        def read(pc):
            if pc%4 or pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Original native source out of SHA-qualified MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        result=inspect(read)
    seven._check_archive(archive)
    return {**result,"original_source_SHA_and_scene_gates_verified":True,
            "original_verified_capture":capture}


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
            OverflowError,AttributeError,struct.error):
        print(json.dumps({"kind":"P0_ORIGINAL_BALL_BACKEDGE_POSTCALL_R4_AND_FLAG_V1",
                          "status":"ABSTAIN_ORIGINAL_SOURCE_SHA_OR_ARG_GATE",
                          "training_approved":False}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
