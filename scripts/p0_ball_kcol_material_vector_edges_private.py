#!/usr/bin/env python3
"""Original Rev1 direct Ball-GolfKCol material comparisons and vector-write CFG.

Previous original SHA-qualified native source audits have verified:
  GolfKCol+0x0118 prism type lhz r0,+0x0E(r3)
  GolfKCol+0x011C result sth r0,0(r28)
  Ball+0x0B60 KCol wrapper BL, 0B84/0B90 class 13/7 compares
  Ball+0x14D0 direct main KCol BL, 14F0 classification stack read
  Ball+0x14F4/14FC compares code 7/12
  Ball+0x1508/1510/1518 stores three floats +AC/+B0/+B4(r23)

This tool safely scans exact original native PPC conditional branch
destinations adjacent to those material-code comparisons and
overapproximates a bounded static path to the three float stores. It
does NOT assert that any class is a tree/trunk/leaf material, that
those float members are velocity, or that a dynamic guest collision
used these branches.

Original seven-pair SHA/94-tree/scene/prism gates are required.
No private native instruction words, raw ROM, user RAM/XYZ, heap pointers,
original asset bytes, video, Dolphin, new swings, guest writes or training.
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
import p0_ball_kcol_prism_type_origin_private as upstream
import p0_ball_cache_cfg_reachability_private as cfg
import p0_ball_kcol_material_branch_private as material
import p0_tree_hitbox_source_callgraph_private as units
import audit_p0_seven_numbered_source_pairs_private as seven

BALL=units.UNITS["Ball"][0]
KCOL=units.UNITS["GolfKCol"][0]
MEM1=0x80000000
COMPARE_SITES=(
    (0x0B84,3,13,11),
    (0x0B90,3,7,11),
    (0x14F4,0,7,10),
    (0x14FC,0,12,10),
)
MAIN_QUERY=0x14D0
STACK_HALFWORD=0x14F0
STORES=((0x1508,172),(0x1510,176),(0x1518,180))
SOURCE_WINDOWS=((0x0B60,0x0BC0),(0x14D0,0x1530))
MAX_NEXT_BRANCH=3
MAX_EDGES=32
MAX_WITNESS=96


def label(pc):
    if not BALL<=pc<units.UNITS["Ball"][1] or pc&3:
        raise ValueError("Native source address outside Ball code unit")
    return f"Ball+0x{pc-BALL:04X}"


def dform(w):
    return ((w>>26),(w>>21)&31,(w>>16)&31,cfg.signed(w&65535,16))


def source_anchors(read):
    # Exact original prism output gate independently rechecked by
    # upstream.inspect() inside run(), but verify critical syntax here.
    if dform(read(KCOL+0x0118))!=(40,0,3,14):
        raise ValueError("Original KCol prism halfword producer changed")
    if dform(read(KCOL+0x011C))!=(44,0,28,0):
        raise ValueError("Original KCol query halfword output changed")
    for off,reg,value,op in COMPARE_SITES:
        w=read(BALL+off)
        if (w>>26,(w>>16)&31,w&65535)!=(op,reg,value):
            raise ValueError("Original Ball comparison syntax changed")
    if dform(read(BALL+STACK_HALFWORD))!=(40,0,1,8):
        raise ValueError("Original Ball stack returned class changed")
    for off,disp in STORES:
        if dform(read(BALL+off))!=(52,0,23,disp):
            raise ValueError("Original Ball member float store changed")
    wrapper=cfg.decode_transfer(BALL+0x0B60,read(BALL+0x0B60))
    main=cfg.decode_transfer(BALL+MAIN_QUERY,read(BALL+MAIN_QUERY))
    if (wrapper["kind"],wrapper["target"])!=("direct_bl_call",KCOL+0x1AC4):
        raise ValueError("Original KCol wrapper BL target changed")
    if (main["kind"],main["target"])!=("direct_bl_call",KCOL):
        raise ValueError("Original main KCol BL target changed")
    return {
        "verified_prism_classification_source":"GolfKCol+0x0118",
        "verified_prism_classification_result_store":"GolfKCol+0x011C",
        "ball_wrapper_query_direct_BL":"Ball+0x0B60",
        "ball_main_query_direct_BL":"Ball+0x14D0",
        "ball_main_query_stack_class_halfword":"Ball+0x14F0",
        "source_ball_comparisons":[
            {"source_site":f"Ball+0x{off:04X}",
             "comparison_opcode":"cmplwi" if op==10 else "cmpwi",
             "compared_GPR":reg,"literal_class_code":value}
            for off,reg,value,op in COMPARE_SITES
        ],
        "exact_three_float_member_source_stores":[
            {"source_site":f"Ball+0x{off:04X}",
             "value_FPR":0,"receiver_GPR":23,
             "numeric_member_displacement":disp}
            for off,disp in STORES
        ],
        "kcol_code_number_is_wood_or_foliage_proven":False,
    }


def compare_branches(read):
    results=[]
    for off,reg,value,op in COMPARE_SITES:
        pc=BALL+off
        near=[]
        for step in range(1,MAX_NEXT_BRANCH+1):
            at=pc+4*step
            desc=cfg.decode_transfer(at,read(at))
            if desc["kind"] in ("conditional_bc","unconditional_b","direct_bl_call"):
                target=desc.get("target")
                near.append({
                    "source_branch_site":label(at),
                    "source_control_kind":desc["kind"],
                    "direct_target_if_in_Ball":
                        label(target) if target is not None and
                            BALL<=target<units.UNITS["Ball"][1] else None,
                    "branch_BO":desc.get("BO"),"branch_BI":desc.get("BI"),
                    "actual_condition_and_code_producer_proven":False,
                    "actual_tree_material_dispatch_proven":False,
                })
            if desc["kind"]!="linear_not_decoded_control":
                break
        results.append({
            "original_compare_site":label(pc),
            "compared_GPR":reg,"compared_literal":value,
            "bounded_nearby_control_edges":near,
            "compare_CR_to_branch_CR_link_proven":False,
        })
    return results


def local_reachability(read):
    # Only local direct PPC branch edges, no resolving LR/CTR or external
    # module returns. Treat BL as assumed call-return for static MAY reach.
    lo=BALL+0x14D0
    hi=BALL+0x1530
    graph=cfg.explore(read,lo=lo,hi=hi,entry=lo)
    edges=[]
    for pc in sorted(graph["parent"]):
        d=cfg.decode_transfer(pc,read(pc))
        if d["kind"] in ("conditional_bc","unconditional_b","direct_bl_call"):
            edges.append({
                "source_site":label(pc),
                "source_kind":d["kind"],
                "direct_target_in_local_window":
                    label(d["target"]) if d["target"] is not None
                    and lo<=d["target"]<hi else None,
                "actual_execution_or_flags_proven":False,
            })
    rows=[]
    for off,disp in STORES:
        path=cfg.route(graph["parent"],BALL+off)
        if path is not None and len(path)>MAX_WITNESS:
            raise ValueError("Unbounded original Ball local vector path")
        rows.append({
            "source_store_site":f"Ball+0x{off:04X}",
            "numeric_float_field":disp,
            "source_may_reach_from_0x14D0_under_bounded_direct_CFG":
                path is not None,
            "bounded_static_route_instruction_count":
                len(path) if path else None,
            "path_requires_unobserved_branch_or_callee_results":True,
            "receiver_is_active_live_ball_proven":False,
            "is_velocity_impulse_or_restitution_proven":False,
        })
    return {
        "original_ball_main_query_local_source_window":
            "Ball+0x14D0..Ball+0x152C",
        "bounded_control_edges":edges[:MAX_EDGES],
        "source_vector_member_store_static_routes":rows,
        "whole_game_true_CFG_and_guest_outcomes_proven":False,
    }


def inspect(read):
    anchors=source_anchors(read)
    return {
        "kind":"P0_ORIGINAL_BALL_KCOL_MATERIAL_TO_VECTOR_EDGE_V1",
        "status":"ORIGINAL_BALL_KCOL_CLASSIFICATION_EDGE_SOURCE_CENSUS",
        "exact_prism_to_Ball_classification_anchors":anchors,
        "native_comparison_to_nearby_control_syntax":compare_branches(read),
        "native_main_query_to_float_field_cfg":local_reachability(read),
        "class_7_12_13_tree_trunk_foliage_identity_proven":False,
        "actual_wood_or_foliage_collision_handler_proven":False,
        "active_selected_Ball_velocity_update_proven":False,
        "native_impact_restitution_or_spin_proven":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    if capture not in range(1,8):
        raise ValueError("Original seven pair Rev1 capture required")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            p=seven.src._file(roots[capture],f"{capture}.{i}.raw",size)
            h=stack.enter_context(p.open("rb"))
            banks.append(stack.enter_context(mmap.mmap(
                h.fileno(),0,access=mmap.ACCESS_READ)))
        rd=seven.roster.TwoBankReader(*banks)
        scene=seven._get(rd)
        field=scene["field"]
        if rd.u32(field+0x1C)!=94:
            raise ValueError("Original 94 Tree scene count mismatch")
        base=rd.u32(field+0x20)
        if seven.roster._bank(base,94*84)!="MEM2":
            raise ValueError("Original 94x84 Tree source changed")
        def read(pc):
            if pc%4 or pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Original native source beyond SHA-qualified MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        if not units.tree_loop_source_gated(read):
            raise ValueError("Original FieldManager tree source loop changed")
        previous=upstream.inspect(read,detail=False)
        if not previous.get("original_source_gates_passed"):
            raise ValueError("Original prism/query classification source gates failed")
        result=inspect(read)
    seven._check_archive(archive)
    return {**result,"original_SHA_native_scene_and_prism_source_verified":True,
            "original_capture":capture}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    a=p.parse_args(argv)
    try:
        print(json.dumps(run(a.archive,a.capture),sort_keys=True,
                         separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,
            OverflowError,AttributeError,struct.error) as exc:
        print(json.dumps({
            "kind":"P0_ORIGINAL_BALL_KCOL_MATERIAL_TO_VECTOR_EDGE_V1",
            "status":"ABSTAIN_ORIGINAL_SHA_SCENE_OR_NATIVE_SOURCE",
            "exception_class_without_message":type(exc).__name__,
            "original_private_error_message_emitted":False,
            "training_approved":False},sort_keys=True))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
