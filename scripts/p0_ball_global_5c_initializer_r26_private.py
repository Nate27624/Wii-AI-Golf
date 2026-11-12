#!/usr/bin/env python3
"""Original Rev1 Ball global pointer flag initialization and update lineage.

Source-only follow-up to SHA-qualified original seven-pair Ball+0x3084
global pointer assignment and two +0x5C byte-store candidate sites.
Strictly distinguish: (1) source initializer writes literal 1 to an
object's +0x5C via r3, (2) r26 loads the same r13-relative global slot
earlier than a +0x5C store, and (3) whether those two receivers can be
established to alias the active global object. Nothing here proves a
tree impact, collision material, guest execution, or physics coefficient.
Never output raw PPC words, original ROM, raw RAM, heap addresses, XYZ,
private capture paths or assets. No Dolphin/new swings/video/guest writes.
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
import p0_ball_global_byte_writer_context_private as old
import p0_ball_cache_cfg_reachability_private as cfg
import p0_ball_cache_r27_lineage_private as lineage
import p0_ball_global_5c_source_census_private as source
import audit_p0_seven_numbered_source_pairs_private as seven

MEM1=source.MEM1
BALL=source.BALL
SOURCE_LIMIT=source.UNITS["Ball"][1]
INIT_FIELDS=(
    (0x311C,14,6,0,0),    # li r6,0
    (0x3124,14,5,0,1),    # li r5,1
    (0x3134,31,31,3,None), # mr r31,r3 checked separately
    (0x3144,36,6,3,0x54),
    (0x3148,36,6,3,0x58),
    (0x314C,38,5,3,0x5C),
    (0x3150,38,6,3,0x5D),
)
R26_GLOBAL_LOAD=0x2D30
R26_BYTE_STORE=0x2D8C
GLOBAL_SET_CALL=0x3080
GLOBAL_SET_STORE=0x3084
LOCAL_CALL_TARGET=0x3BA0
MAX_NEARBY=16
MAX_GPR_DEFS=14


def check_d(read,at,op,rt,ra,offset):
    word=read(BALL+at)
    d=source.form(word)
    if d is None and op==14:
        value=((word&0xFFFF)^0x8000)-0x8000
        if (word>>26,(word>>21)&31,(word>>16)&31,value)!=(op,rt,ra,offset):
            raise ValueError("Original native immediate source anchor changed")
    elif d is None or (d["op"],d["rT"],d["rA"],d["disp"])!=(
            op,rt,ra,offset):
        raise ValueError("Original native D-form memory anchor changed")
    return True


def init(read):
    exact=[]
    for off,op,rt,ra,disp in INIT_FIELDS:
        if op==31:
            word=read(BALL+off)
            writers=lineage.gpr_writers(word)
            if (rt,"mr",ra,None) not in writers:
                raise ValueError("Original initializer receiver mr changed")
            syntax="mr"
        else:
            check_d(read,off,op,rt,ra,disp)
            syntax="li" if op==14 else source.KINDS[op]
        exact.append({
            "source_site":f"Ball+0x{off:04X}",
            "source_operation":syntax,
            "register_T":rt,"register_A_or_immediate_source":ra,
            "signed_displacement_or_literal":disp,
        })
    relevant={}
    for reg,start in ((5,0x3124),(6,0x311C),(3,0x3134)):
        end=0x314C if reg==5 else (0x3150 if reg==6 else 0x3154)
        writes=[]
        barriers=[]
        unidentified=[]
        for off in range(start+4,end,4):
            word=read(BALL+off)
            control=cfg.decode_transfer(BALL+off,word)
            if control["kind"]!="linear_not_decoded_control":
                barriers.append(f"Ball+0x{off:04X}")
            for dst,kind,s,displacement in lineage.gpr_writers(word):
                if dst==reg:
                    writes.append({"source_site":f"Ball+0x{off:04X}",
                                   "syntactic_writer_class":kind})
            op=word>>26
            # Floating point instructions (op 59,63) cannot write GPRs,
            # and ordinary non-updating D-form FP stores/loads don't.
            if op not in (11,14,15,16,18,19,24,25,26,27,28,29,31,
                          32,34,36,38,40,44,48,50,52,54,59,60,63):
                unidentified.append({"source_site":f"Ball+0x{off:04X}",
                                     "primary_opcode_number":op})
        relevant[f"r{reg}"]={
            "recognized_intervening_writes":writes,
            "intervening_control_sites":barriers,
            "other_unclassified_instruction_types":unidentified,
            "literal_or_receiver_preserved_by_known_syntax":
                not writes and not barriers and not unidentified,
            "complete_instruction_semantics_qualified":False,
        }
    literal_preserved=(
        relevant["r5"]["literal_or_receiver_preserved_by_known_syntax"]
        and relevant["r6"]["literal_or_receiver_preserved_by_known_syntax"]
    )
    return {
        "original_source_initializer_instruction_gates":exact,
        "initializer_local_receiver_register":3,
        "source_uses_r5_literal_1_and_r6_literal_0":True,
        "bounded_intervening_register_checks":relevant,
        "initializer_stores_literal_one_to_receiver_plus_0x5C_if_executed":
            bool(literal_preserved),
        "initializer_stores_literal_zero_to_receiver_plus_0x5D_if_executed":
            bool(literal_preserved),
        "initializer_receiver_is_global_pointer_proven":False,
        "initializer_receiver_is_selected_live_ball_proven":False,
        "native_guest_executed_initializer_proven":False,
    }


def global_constructor(read):
    check_d(read,0x3068,14,3,0,428)
    check_d(read,0x307C,14,4,0,0)
    check_d(read,0x3084,36,3,13,source.GLOBAL_SLOT)
    step=cfg.decode_transfer(BALL+GLOBAL_SET_CALL,read(BALL+GLOBAL_SET_CALL))
    if (step["kind"],step["target"])!=(
            "direct_bl_call",BALL+LOCAL_CALL_TARGET):
        raise ValueError("Original global setter direct source callee changed")
    gate=cfg.decode_transfer(BALL+0x3078,read(BALL+0x3078))
    if gate["kind"]!="conditional_bc" or gate["target"]!=BALL+0x3084:
        raise ValueError("Original global registration control branch changed")
    return {
        "source_size_argument_site":"Ball+0x3068",
        "original_source_size_immediate":428,
        "first_call_site":"Ball+0x3070",
        "first_call_target_name_or_allocator_semantics_proven":False,
        "null_or_nonnull_source_control_site":"Ball+0x3078",
        "control_predicate_meaning_or_runtime_value_proven":False,
        "source_local_callee_site":"Ball+0x3080",
        "source_local_callee_ball_relative_target":"Ball+0x3BA0",
        "global_store_immediately_after_local_callee":"Ball+0x3084",
        "source_global_store_value_GPR":3,
        "callee_return_GPR3_is_allocated_constructed_ball_proven":False,
        "source_global_pointer_matches_initializer_receiver_proven":False,
    }


def global_r26(read):
    check_d(read,R26_GLOBAL_LOAD,32,26,13,source.GLOBAL_SLOT)
    check_d(read,R26_BYTE_STORE,38,30,26,0x5C)
    recognized=[]
    control=[]
    unknown=[]
    for off in range(R26_GLOBAL_LOAD+4,R26_BYTE_STORE,4):
        w=read(BALL+off)
        pc=BALL+off
        t=cfg.decode_transfer(pc,w)
        if t["kind"]!="linear_not_decoded_control":
            control.append({
                "source_site":f"Ball+0x{off:04X}",
                "transfer_class":t["kind"],
                "target_inside_Ball_if_known":
                    f"Ball+0x{t['target']-BALL:04X}"
                    if t.get("target") is not None and BALL<=t["target"]<SOURCE_LIMIT else None})
        for dst,kind,src,disp in lineage.gpr_writers(w):
            if dst==26:
                recognized.append({
                    "source_site":f"Ball+0x{off:04X}",
                    "source_writer_class":kind,"source_register":src,
                    "source_displacement":disp,
                })
        op=w>>26
        if op==31 and ((w>>1)&1023) not in (
                444,339,371,28,316,23,55,87,119,266,40):
            unknown.append({"source_site":f"Ball+0x{off:04X}",
                            "primary_opcode_number":op,
                            "X_form_opcode_number":(w>>1)&1023})
    # Literal region has multiple conditional and BL source sites; no
    # all-path source-SSA proof, even if no recognized r26 definitions.
    return {
        "native_global_load_source":"Ball+0x2D30",
        "native_byte_writer_source":"Ball+0x2D8C",
        "global_slot_signed_displacement":source.GLOBAL_SLOT,
        "byte_field_offset":92,
        "recognized_r26_redefinitions_between_source_and_store":recognized,
        "source_branch_or_call_sites_between_source_and_store":control,
        "unknown_X_form_instruction_categories":unknown,
        "same_global_pointer_value_along_source_path_proven":False,
        "r26_is_callee_saved_GPR_under_PPC_ABI":True,
        "runtime_byte_value_written_proven":False,
        "receiver_is_selected_active_ball_proven":False,
    }


def r30_source(read):
    out=[]
    for off in range(0x2C98,R26_BYTE_STORE,4):
        w=read(BALL+off)
        for dst,kind,src,disp in lineage.gpr_writers(w):
            if dst==30:
                out.append({"site":f"Ball+0x{off:04X}",
                            "source_writer_syntax":kind,
                            "source_GPR":src,
                            "source_displacement":disp})
    return {
        "source_bounded_r30_assignments":out[:MAX_GPR_DEFS],
        "source_r30_is_zero_or_one_proven":False,
        "source_r30_runtime_byte_value_proven":False,
    }


def inspect(read):
    prior=old.verify_anchors(read)
    if len(prior)!=5:
        raise ValueError("Original exact five anchor gates changed")
    return {
        "kind":"P0_ORIGINAL_BALL_GLOBAL_5C_INITIALIZER_AND_R26_SOURCE_V1",
        "status":"SHA_QUALIFIED_NATIVE_INITIALIZER_AND_GLOBAL_R26_CANDIDATES",
        "original_native_global_pointer_registration":global_constructor(read),
        "original_native_initializer_byte_store":init(read),
        "global_r26_byte_store_source_relationship":global_r26(read),
        "candidate_r30_byte_store_value_source":r30_source(read),
        "source_original_five_native_census_anchors_passed":True,
        "global_object_is_selected_live_Ball_proven":False,
        "native_tree_collision_or_wood_vs_foliage_branch_proven":False,
        "native_impact_velocity_or_restitution_proven":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    prior=old.run(archive,capture)
    if not prior.get("original_source_archive_SHA_and_scene_verified"):
        raise ValueError("Previous native and SHA gates failed")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            path=seven.src._file(roots[capture],f"{capture}.{i}.raw",size)
            h=stack.enter_context(path.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(h.fileno(),0,access=mmap.ACCESS_READ)))
        def read(pc):
            if pc%4 or pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Outside original SHA qualified MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        report=inspect(read)
    seven._check_archive(archive)
    return {**report,"original_SHA_7pair_archive_and_scene_gates_verified":True,
            "original_capture":capture}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    a=p.parse_args(argv)
    try:
        print(json.dumps(run(a.archive,a.capture),
                         separators=(",",":"),sort_keys=True,allow_nan=False))
        return 0
    except (OSError,ValueError,KeyError,TypeError,IndexError,
            OverflowError,AttributeError,struct.error) as exc:
        print(json.dumps({
            "kind":"P0_ORIGINAL_BALL_GLOBAL_5C_INITIALIZER_AND_R26_SOURCE_V1",
            "status":"ABSTAIN_SHA_OR_NATIVE_SOURCE_ANCHOR",
            "exception_type":type(exc).__name__,
            "private_error_message_emitted":False,
            "training_approved":False},sort_keys=True))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
