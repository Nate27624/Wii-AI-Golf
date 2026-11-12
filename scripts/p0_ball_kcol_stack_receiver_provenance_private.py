#!/usr/bin/env python3
"""Original Rev1 Ball KCol main-query stack +0x4C/50/54 and r23 source audit.

Previous SHA-gated original PPC source confirms KCol prism class 7/12
CR0 EQ branches skip the Ball+0x1508/+0x1510/+0x1518 float copy.
Those stores get f0 from r1+0x4C/+0x50/+0x54 and write into r23
+0xAC/+0xB0/+0xB4. This tool inventories bounded caller-side
stack-slot stores, stack-pointer argument formations, r23 syntactic
definitions and KCol query-entry source syntax without mistaking a
coincidental stack offset or a lexical definition for reaching CFG SSA.

Original seven-pair SHA/94-tree/scene/GolfKCol prism/branch gates required,
read-only. Outputs no native PPC words, ROM bytes, raw RAM, heap pointers,
private paths/XYZ/assets. No Dolphin/video/new shots/guest writes/training.
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
import p0_ball_kcol_cr0_float_sources_private as old
import p0_ball_global_5c_zero_witness_private as gprs
import p0_ball_global_byte_writer_context_private as syntax
import p0_ball_cache_cfg_reachability_private as cfg
import audit_p0_seven_numbered_source_pairs_private as seven

MEM1=old.MEM1
BALL=old.BALL
KCOL=old.previous.KCOL
KCOL_UNIT=old.previous.units.UNITS["GolfKCol"]
CALL=0x14D0
STACK_SLOTS=(0x4C,0x50,0x54)
BALL_CONTEXT_START=0x1400
BALL_CONTEXT_END=0x1520
ARG_START=0x1490
ARG_END=0x14D0
KCOL_START=0
KCOL_END=0x0140
RECEIVER_LOOKBACK_START=0x1380
LIMIT=24


def ball(off):
    return old.site(off)


def kcol(off):
    if off%4 or not 0<=off<KCOL_UNIT[1]-KCOL:
        raise ValueError("Original KCol site outside public code unit")
    return f"GolfKCol+0x{off:04X}"


def mem(w):
    op=w>>26
    if op not in (32,33,34,35,36,37,38,39,40,41,42,43,44,45,
                  46,47,48,49,50,51,52,53,54,55):
        return None
    return {
        "opcode_number":op,
        "mnemonic":{
            32:"lwz",33:"lwzu",34:"lbz",35:"lbzu",36:"stw",37:"stwu",
            38:"stb",39:"stbu",40:"lhz",41:"lhzu",42:"lha",
            43:"lhau",44:"sth",45:"sthu",46:"lmw",47:"stmw",
            48:"lfs",49:"lfsu",50:"lfd",51:"lfdu",52:"stfs",
            53:"stfsu",54:"stfd",55:"stfdu",
        }[op],
        "register_T_or_FPR":(w>>21)&31,
        "base_GPR":(w>>16)&31,
        "numeric_displacement":cfg.signed(w&65535,16),
    }


def original_anchors(read):
    before=old.inspect(read)
    f=before["main_query_classification_source_flow"]
    if not (f["main_query_source_class_7_or_12_beq_skips_three_stores"]
            and f["all_three_float_source_load_to_store_pairs_qualified"]
            and all(p["exact_adjacent_cmp_to_beq_CR0_EQ_source_verified"]
                    for p in before["original_source_comparison_to_beq_CR_checks"])):
        raise ValueError("Earlier original KCol CR0 EQ and FP source gates failed")
    fp=before["original_three_FP_member_load_store_pairs"]
    offsets=[x["source_preceding_FP_instruction"]["signed_displacement"] for x in fp]
    receivers=[x["source_preceding_FP_instruction"]["base_GPR"] for x in fp]
    if offsets!=list(STACK_SLOTS) or receivers!=[1,1,1]:
        raise ValueError("Original 3 component stack load slots changed")
    c=cfg.decode_transfer(BALL+CALL,read(BALL+CALL))
    if (c["kind"],c["target"])!=("direct_bl_call",KCOL):
        raise ValueError("Original Ball KCol direct BL changed")
    return {
        "source_main_KCol_query_BL":ball(CALL),
        "source_direct_callee":"GolfKCol+0x0000",
        "original_three_stack_component_load_offsets":list(STACK_SLOTS),
        "original_three_component_destination_offsets":[0xAC,0xB0,0xB4],
        "source_compares_class_7_12_and_skips_triad":True,
        "same_stack_slot_is_proven_written_by_KCol_query":False,
        "selected_active_ball_or_velocity_semantics_proven":False,
    }


def caller_stack_accesses(read):
    rows=[]
    totals=Counter()
    before_call=Counter()
    after_call=Counter()
    arg_forms=[]
    for off in range(BALL_CONTEXT_START,BALL_CONTEXT_END,4):
        pc=BALL+off
        w=read(pc)
        op=w>>26
        if ARG_START<=off<ARG_END and op==14:
            rt=(w>>21)&31
            ra=(w>>16)&31
            disp=cfg.signed(w&65535,16)
            if ra==1:
                arg_forms.append({
                    "source_site":ball(off),
                    "operation":"addi_register_from_stack_pointer",
                    "destination_GPR":rt,
                    "source_stack_relative_immediate":disp,
                    "actual_query_parameter_role_proven":False,
                })
        x=mem(w)
        if not x or x["base_GPR"]!=1 or x["numeric_displacement"] not in STACK_SLOTS:
            continue
        k=x["mnemonic"]
        totals[k]+=1
        (before_call if off<CALL else after_call)[k]+=1
        if len(rows)<LIMIT:
            rows.append({
                "source_site":ball(off),
                **x,
                "temporal_lexical_relation_to_KCol_call":
                    "before" if off<CALL else ("callsite" if off==CALL else "after"),
                "same_runtime_stack_frame_or_executed_path_proven":False,
            })
    return {
        "source_bounded_span":"Ball+0x1400..Ball+0x151C",
        "recognized_r1_stack_slot_4C_50_54_access_counts":dict(totals),
        "recognized_precall_stack_slot_access_counts":dict(before_call),
        "recognized_postcall_stack_slot_access_counts":dict(after_call),
        "bounded_source_numeric_slot_accesses":rows,
        "unshown_source_access_count":max(0,sum(totals.values())-len(rows)),
        "original_precall_addi_stack_address_formations":arg_forms[:LIMIT],
        "precise_KCol_output_pointer_arg_proven":False,
        "all_writer_aliases_of_stack_slots_exhausted":False,
    }


def r23_context(read):
    defs=[]
    unknown=[]
    branches=[]
    for off in range(RECEIVER_LOOKBACK_START,CALL,4):
        pc=BALL+off
        w=read(pc)
        qualifies,writers=gprs.gpr_writes_qualified(w)
        if 23 in writers and qualifies:
            defs.append({
                "source_site":ball(off),
                "source_primary_opcode_number":w>>26,
                "source_syntax":syntax.typed_instruction(pc,w),
                "is_actual_reaching_r23_definition_proven":False,
            })
        if not qualifies:
            unknown.append({
                "source_site":ball(off),
                "primary_opcode_number":w>>26,
                "X_form_opcode_number":(w>>1)&1023 if w>>26==31 else None,
            })
        t=cfg.decode_transfer(pc,w)
        if t["kind"]!="linear_not_decoded_control":
            branches.append({
                "source_site":ball(off),
                "transfer_category":t["kind"],
            })
    return {
        "bounded_source_interval":"Ball+0x1380..Ball+0x14CC",
        "source_r23_definition_candidates":defs[-LIMIT:],
        "source_unsupported_GPR_effect_sites":unknown[:LIMIT],
        "source_control_transfer_sites":branches[:LIMIT],
        "more_unknown_sites_not_displayed":max(0,len(unknown)-LIMIT),
        "complete_function_entry_to_r23_SSA_proven":False,
        "receiver_r23_is_selected_active_ball_proven":False,
    }


def kcol_entry(read):
    rows=[]
    counts=Counter()
    for off in range(KCOL_START,KCOL_END,4):
        w=read(KCOL+off)
        x=mem(w)
        if x is not None:
            counts[x["mnemonic"]]+=1
            if (x["base_GPR"] in (3,4,5,6,7,8,9,10,22,23,27,28)
                    and x["numeric_displacement"]<=96
                    and len(rows)<LIMIT):
                rows.append({"source_site":kcol(off),**x,
                    "is_the_caller_stack_component_buffer_proven":False})
        elif w>>26==18:
            counts["direct_branch_or_call"]+=1
        elif w>>26==16:
            counts["conditional_branch"]+=1
    return {
        "source_KCol_bounded_main_query_entry_span":"GolfKCol+0x0000..+0x013C",
        "recognized_memory_and_branch_opcode_counts":dict(counts),
        "bounded_potential_parameter_based_memory_accesses":rows,
        "direct_KCol_write_to_Ball_stack_4C_50_54_proven":False,
        "native_argument_receiver_runtime_identity_proven":False,
    }


def inspect(read):
    anchors=original_anchors(read)
    return {
        "kind":"P0_ORIGINAL_BALL_KCOL_STACK_COMPONENT_AND_R23_PROVENANCE_V1",
        "status":"SHA_QUALIFIED_BALL_KCOL_STACK_COMPONENT_SOURCE_CENSUS",
        "prior_original_CR0_class_and_FP_stack_copy_anchors":anchors,
        "bounded_Ball_caller_stack_access_inventory":caller_stack_accesses(read),
        "bounded_Ball_r23_receiver_definition_syntax":r23_context(read),
        "bounded_main_KCol_callee_entry_syntax":kcol_entry(read),
        "query_wrote_three_stack_floats_verified":False,
        "class_7_or_12_is_tree_trunk_or_foliage_proven":False,
        "receiver_is_selected_live_Ball_or_velocity_proven":False,
        "native_tree_contact_impact_impulse_restitution_proven":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    prev=old.run(archive,capture)
    if not (prev.get("original_source_SHA_scene_and_prism_gates_verified")
            and prev.get("original_capture")==capture):
        raise ValueError("Earlier original seven pair SHA scene or prism gates failed")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for index,size in enumerate(seven.SIZE,1):
            p=seven.src._file(roots[capture],f"{capture}.{index}.raw",size)
            h=stack.enter_context(p.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(h.fileno(),0,access=mmap.ACCESS_READ)))
        def read(pc):
            if pc%4 or pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Original native PPC source outside SHA-qualified MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        out=inspect(read)
    seven._check_archive(archive)
    return {**out,"original_SHA_scene_and_native_CR0_FP_gates_verified":True,
            "original_capture":capture}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",required=True,type=Path)
    parser.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=parser.parse_args(argv)
    try:
        print(json.dumps(run(args.archive,args.capture),
                         sort_keys=True,separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,KeyError,TypeError,IndexError,
            OverflowError,AttributeError,struct.error) as exc:
        print(json.dumps({
            "kind":"P0_ORIGINAL_BALL_KCOL_STACK_COMPONENT_AND_R23_PROVENANCE_V1",
            "status":"ABSTAIN_ORIGINAL_SHA_OR_SOURCE_STACK",
            "failure_exception_class":type(exc).__name__,
            "private_error_message_or_native_words_exposed":False,
            "training_approved":False},sort_keys=True))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
