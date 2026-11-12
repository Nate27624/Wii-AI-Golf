#!/usr/bin/env python3
"""Original Rev1 Ball-KCol exact CR0 EQ dispatch and three FP store sources.

Earlier SHA-qualified source audit proves KCol prism classification copied
to a result halfword; Ball then compares returned codes 13,7,7,12 and
conditionally may reach three stfs f0,+0xAC/B0/B4(r23).
This audit checks exact adjacent PPC cmpwi/cmplwi -> beq CR bit identity
and the immediately preceding floating-point load to each store.
On the main source route, codes 7 and 12 branch around those stores;
this is STATIC source control, not executed collision/material mapping.
A float written to a Ball object offset is not automatically a velocity
or restitution coefficient; the exact receiver/active Ball is unresolved.

Source-gated original seven-capture USA Rev1 private read-only archive
only. No ROM/PPC instruction words, raw RAM, heap pointers, XYZ, assets,
private file paths, new swings/Dolphin/video, guest writes or training.
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
import p0_ball_kcol_material_vector_edges_private as previous
import p0_ball_cache_cfg_reachability_private as cfg
import audit_p0_seven_numbered_source_pairs_private as seven

MEM1=previous.MEM1
BALL=previous.BALL
COMPARE_PAIRS=(
    (0x0B84,0x0B88,11,3,13,0x0BF4),
    (0x0B90,0x0B94,11,3,7,0x0B9C),
    (0x14F4,0x14F8,10,0,7,0x152C),
    (0x14FC,0x1500,10,0,12,0x152C),
)
FLOAT_PAIRS=(
    (0x1504,0x1508,172),
    (0x150C,0x1510,176),
    (0x1514,0x1518,180),
)


def site(off):
    if off<0 or off>=previous.units.UNITS["Ball"][1]-BALL or off&3:
        raise ValueError("Outside public original Ball source code unit")
    return f"Ball+0x{off:04X}"


def compare_word(w):
    op=w>>26
    if op not in (10,11):
        raise ValueError("Not immediate PPC integer comparison")
    return {
        "opcode":"cmplwi" if op==10 else "cmpwi",
        "CR_field":(w>>23)&7,
        "L_bit":(w>>21)&1,
        "compared_GPR":(w>>16)&31,
        "immediate_unsigned":w&0xffff,
        "immediate_signed":cfg.signed(w&0xffff,16),
    }


def pairs(read):
    rows=[]
    for compare_off,branch_off,expect_op,reg,immediate,target_off in COMPARE_PAIRS:
        cm=compare_word(read(BALL+compare_off))
        word=read(BALL+compare_off)
        b=cfg.decode_transfer(BALL+branch_off,read(BALL+branch_off))
        if ((word>>26),cm["compared_GPR"],word&0xffff)!=(expect_op,reg,immediate):
            raise ValueError("Original native comparison class changed")
        if (b["kind"],b["target"])!=(
                "conditional_bc",BALL+target_off):
            raise ValueError("Original direct native conditional branch changed")
        cr0=(cm["CR_field"]==0 and cm["L_bit"]==0)
        eq_bit=b["BI"]==cm["CR_field"]*4+2
        beq=b["BO"]==12
        proven=cr0 and eq_bit and beq and branch_off==compare_off+4
        rows.append({
            "source_compare_site":site(compare_off),
            "source_branch_site":site(branch_off),
            "compared_literal_class":immediate,
            "signed_compare":expect_op==11,
            "compared_GPR":reg,
            "comparison_CR_field":cm["CR_field"],
            "comparison_L_bit":cm["L_bit"],
            "branch_BO":b["BO"],
            "branch_BI":b["BI"],
            "source_beq_target":site(target_off),
            "exact_adjacent_cmp_to_beq_CR0_EQ_source_verified":proven,
            "branch_taken_when_class_equal_if_compare_input_valid":proven,
            "native_collision_event_or_wood_foliage_material_verified":False,
        })
    return rows


def float_source(w):
    op=w>>26
    if op in (48,49,50,51,52,53,54,55,60,61):
        return {
            "source_opcode_number":op,
            "source_floating_operation":{
                48:"lfs",49:"lfsu",50:"lfd",51:"lfdu",
                52:"stfs",53:"stfsu",54:"stfd",55:"stfdu",
                60:"psq_st",61:"psq_stu",
            }[op],
            "FPR":(w>>21)&31,
            "base_GPR":(w>>16)&31,
            "signed_displacement":cfg.signed(w&65535,16),
        }
    return {
        "source_opcode_number":op,
        "source_floating_operation":"unrecognized_non_D_form_FP_source",
        "FPR":None,
        "base_GPR":None,
        "signed_displacement":None,
    }


def float_pairs(read):
    results=[]
    for load_off,store_off,displacement in FLOAT_PAIRS:
        load=float_source(read(BALL+load_off))
        store=float_source(read(BALL+store_off))
        if (store["source_opcode_number"],store["FPR"],
            store["base_GPR"],store["signed_displacement"])!=(
                52,0,23,displacement):
            raise ValueError("Exact original Ball f0 state store changed")
        is_immediate_load=(
            store_off==load_off+4
            and load["source_opcode_number"]==48
            and load["FPR"]==0)
        results.append({
            "source_immediately_preceding_site":site(load_off),
            "source_preceding_FP_instruction":load,
            "source_Ball_member_store_site":site(store_off),
            "member_receiver_GPR":23,
            "member_byte_displacement":displacement,
            "stored_FPR":0,
            "adjacent_lfs_f0_to_stfs_f0_same_register_verified":is_immediate_load,
            "source_writes_ball_member_from_FP_load_if_executed":is_immediate_load,
            "source_FP_load_is_KCol_query_output_proven":False,
            "ball_member_is_velocity_or_restitution_proven":False,
            "receiver_is_selected_live_ball_proven":False,
        })
    return results


def main_class_flow(read,pairrows,storerows):
    # All relevant original instructions between class read and final
    # stores must be recognized; branch outcomes are still UNOBSERVED.
    lhz=read(BALL+0x14F0)
    load=(
        (lhz>>26,(lhz>>21)&31,(lhz>>16)&31,
         cfg.signed(lhz&65535,16))==(40,0,1,8)
    )
    class_reg_not_reassigned=True
    unknown=[]
    for off in (0x14F4,0x14F8,0x14FC,0x1500):
        w=read(BALL+off)
        if w>>26 not in (10,16):
            class_reg_not_reassigned=False
            unknown.append(site(off))
    direct_source=(
        load and class_reg_not_reassigned
        and all(x["exact_adjacent_cmp_to_beq_CR0_EQ_source_verified"]
                for x in pairrows[2:])
    )
    no_internal_branch=True
    for off in range(0x1504,0x151C,4):
        if cfg.decode_transfer(BALL+off,read(BALL+off))[
                "kind"]!="linear_not_decoded_control":
            no_internal_branch=False
    return {
        "original_query_stack_halfword_to_GPR0_source_site":site(0x14F0),
        "query_class_GPR0_stays_unchanged_across_two_class_compares":
            class_reg_not_reassigned,
        "unclassified_GPR0_or_control_sites":unknown,
        "main_query_source_class_7_or_12_beq_skips_three_stores":
            direct_source,
        "two_beq_source_targets_bypass_float_triad":
            all(x["source_beq_target"]=="Ball+0x152C" for x in pairrows[2:]),
        "fallthrough_from_both_beq_source_has_no_intervening_branch_in_triad":
            no_internal_branch,
        "all_three_float_source_load_to_store_pairs_qualified":
            all(x["adjacent_lfs_f0_to_stfs_f0_same_register_verified"]
                for x in storerows),
        "actual_main_query_return_success_and_flags_executed_proven":False,
        "class_7_is_trunk_or_foliage_proven":False,
        "class_12_is_trunk_or_foliage_proven":False,
        "stored_float_fields_are_ball_velocity_proven":False,
    }


def inspect(read):
    old=previous.inspect(read)
    if old["status"]!="ORIGINAL_BALL_KCOL_CLASSIFICATION_EDGE_SOURCE_CENSUS":
        raise ValueError("Original KCol source qualification incomplete")
    cs=pairs(read)
    fp=float_pairs(read)
    flow=main_class_flow(read,cs,fp)
    return {
        "kind":"P0_ORIGINAL_BALL_KCOL_CR0_EQ_FLOAT_SOURCE_V1",
        "status":"SHA_QUALIFIED_KCOL_CLASS_CR0_BRANCH_AND_FLOAT_SOURCE",
        "original_source_comparison_to_beq_CR_checks":cs,
        "original_three_FP_member_load_store_pairs":fp,
        "main_query_classification_source_flow":flow,
        "native_selected_Ball_collision_response_proven":False,
        "prism_code_7_12_13_trunk_or_foliage_identity_proven":False,
        "native_spin_impulse_restitution_semantics_proven":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    prev=previous.run(archive,capture)
    if not(prev.get("original_SHA_native_scene_and_prism_source_verified") is True
           and prev.get("original_capture")==capture):
        raise ValueError("Original seven-pair SHA and native source gates failed")
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
                raise ValueError("Outside original SHA-qualified PPC source bank")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        report=inspect(read)
    seven._check_archive(archive)
    return {**report,"original_source_SHA_scene_and_prism_gates_verified":True,
            "original_capture":capture}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=p.parse_args(argv)
    try:
        print(json.dumps(run(args.archive,args.capture),
                         sort_keys=True,separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,
            OverflowError,AttributeError,struct.error) as exc:
        print(json.dumps({
            "kind":"P0_ORIGINAL_BALL_KCOL_CR0_EQ_FLOAT_SOURCE_V1",
            "status":"ABSTAIN_ORIGINAL_SHA_PRISM_OR_NATIVE_SOURCE",
            "failure_exception_class":type(exc).__name__,
            "private_exception_message_exposed":False,
            "training_approved":False},sort_keys=True))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
