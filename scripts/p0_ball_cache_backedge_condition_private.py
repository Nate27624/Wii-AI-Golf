#!/usr/bin/env python3
"""Original Rev1 Ball cache backedge predicate and CFG-route audit.

The source-qualified bounded CFG identified a possible path from
0x80299C70 to the CC and FC copy sites via Ball+0x2FC4 and +0x2FCC.
This tool qualifies those exact branch sites and records which branch
edges the static witness uses. It classifies simple PowerPC BO/BI
branch-on-CR predicates and bounded prior compare *syntax*.

It deliberately does NOT assert path feasibility, actual guest branch
outcomes, native wood/leaves impact or selected-Ball receiver identity.
Unknown CR producers, external calls and indirect branches remain
unresolved. No video/new swings/Dolphin/live RAM/writes or original
native bytes/pointers/XYZ in output. Uses original seven-capture SHA,
Golf scene and source-native gates via the existing qualified reader.
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
import p0_ball_cache_cfg_reachability_private as cfg
import audit_p0_seven_numbered_source_pairs_private as seven

MEM1=cfg.MEM1
BASE=cfg.BASE
ENTRY=cfg.ENTRY
BACKEDGE_OFFSETS=(0x2FC4,0x2FCC)
KEY_TARGETS=(0x2CD4,0x2D00,0x2D04,0x2F98,0x2FA8)
MAX_WITNESS_EDGES=64
MAX_COMPARE_LOOKBACK=28


def cr_predicate(dec):
    if dec["kind"]!="conditional_bc":
        return None
    bo=(dec["BO"])
    if bo==12:
        meaning="branch_when_CR_bit_true"
    elif bo==4:
        meaning="branch_when_CR_bit_false"
    elif bo==20:
        meaning="unconditional_BO20"
    else:
        meaning="complex_BO_CTR_or_CR_semantics_not_decoded"
    return {
        "BO":bo,
        "BI":dec["BI"],
        "condition_kind":meaning,
        "CR_field_index":dec["BI"]//4,
        "CR_bit_within_field_index":dec["BI"]%4,
        "condition_is_complete_PPC_proof":bo in (4,12,20),
        "original_dynamic_CR_bit_value_known":False,
    }


def compare_syntax(w):
    op=w>>26
    # PPC cmpi/cmpli: BF in bits 23..25, RA in bits 16..20.
    if op in (10,11):
        return {
            "syntax":"cmpli_unsigned_immediate" if op==10
                     else "cmpi_signed_immediate",
            "CR_field_index":(w>>23)&7,
            "source_gpr_index":(w>>16)&31,
            "immediate_signed_bits":cfg.signed(w&0xFFFF,16) if op==11 else None,
            "immediate_unsigned_bits":w&0xFFFF if op==10 else None,
            "comparison_operands_or_runtime_result_verified":False,
        }
    if op==31 and ((w>>1)&1023) in (0,32):
        return {
            "syntax":"cmp_register_or_cmpl_register",
            "CR_field_index":(w>>23)&7,
            "source_gpr_index":(w>>16)&31,
            "comparison_operands_or_runtime_result_verified":False,
        }
    if op==63 and ((w>>1)&1023) in (0,32):
        return {
            "syntax":"fcmpu_or_fcmpo",
            "CR_field_index":(w>>23)&7,
            "comparison_operands_or_runtime_result_verified":False,
        }
    if op in (28,29):
        return {
            "syntax":"andi_dot_or_andis_dot_affects_CR0",
            "CR_field_index":0,
            "comparison_operands_or_runtime_result_verified":False,
        }
    return None


def prior_compare(read,pc,field,lower):
    for n in range(1,MAX_COMPARE_LOOKBACK+1):
        where=pc-4*n
        if where<lower:
            break
        w=read(where)
        item=compare_syntax(w)
        if item and item["CR_field_index"]==field:
            return {
                "candidate_source_site":cfg.src(where),
                "distance_in_instructions":n,
                "producer":item,
                "last_dynamic_CR_producer_proven":False,
            }
        t=cfg.decode_transfer(where,w)
        if t["kind"]!="linear_not_decoded_control":
            return {
                "candidate_source_site":None,
                "blocked_by_prior_control_transfer_site":cfg.src(where),
                "last_dynamic_CR_producer_proven":False,
            }
    return {
        "candidate_source_site":None,
        "last_dynamic_CR_producer_proven":False,
    }


def branch_edges(read,offs):
    result=[]
    for off in offs:
        at=BASE+off
        w=read(at)
        desc=cfg.decode_transfer(at,w)
        if desc["kind"]!="conditional_bc":
            raise ValueError("Source backedge PPC branch changed")
        p=cr_predicate(desc)
        target=desc["target"]
        result.append({
            "source_site":cfg.src(at),
            "branch_target_relative":cfg.src(target),
            "fallthrough_relative":cfg.src(at+4),
            "branch_predicate":p,
            "bounded_nearest_linear_CR_producer":
                prior_compare(read,at,p["CR_field_index"],cfg.LO),
            "runtime_branch_direction_or_feasibility_proven":False,
        })
    return result


def edge_witness(read,parent,target):
    path=cfg.route(parent,target)
    if path is None:
        return {
            "bounded_may_reach":False,
            "static_witness_available":False,
            "native_unreachable_proven":False,
        }
    events=[]
    for index,at in enumerate(path[:-1]):
        w=read(at)
        dec=cfg.decode_transfer(at,w)
        if dec["kind"]=="linear_not_decoded_control":
            continue
        next_site=path[index+1]
        choice=(
            "taken_direct_target" if dec.get("target")==next_site else
            "call_return_assumed_fallthrough" if dec["kind"]=="direct_bl_call"
            else "conditional_fallthrough" if dec["kind"]=="conditional_bc"
            else "indirect_conditional_fallthrough_unknown_target" if
                dec["kind"]=="indirect_bclr_or_bcctr"
            else "other_overapproximation"
        )
        events.append({
            "original_branch_site":cfg.src(at),
            "target_or_next_site":cfg.src(next_site),
            "branch_kind":dec["kind"],
            "static_witness_edge_choice":choice,
            "conditional_CR_predicate_if_decoded":cr_predicate(dec),
            "branch_condition_satisfiable_on_real_guest_proven":False,
        })
    return {
        "bounded_may_reach":True,
        "static_witness_available":True,
        "static_witness_instruction_count":len(path)-1,
        "witness_control_edges":events[:MAX_WITNESS_EDGES],
        "additional_control_edges_not_displayed":max(0,len(events)-MAX_WITNESS_EDGES),
        "native_guest_execution_of_this_witness_proven":False,
        "native_unreachable_proven":False,
    }


def inspect(read):
    base=cfg.inspect(read)
    if not all(base["original_key_native_source_site_reachability"][
            f"Ball+0x{o:04X}"]["possible_reach_from_published_80299C70_entry_under_bounded_model"]
            for o in KEY_TARGETS):
        raise ValueError("Earlier original bounded source reachability changed")
    graph=cfg.explore(read)
    back=branch_edges(read,BACKEDGE_OFFSETS)
    targets={
        f"Ball+0x{o:04X}":edge_witness(read,graph["parent"],BASE+o)
        for o in KEY_TARGETS
    }
    return {
        "kind":"P0_ORIGINAL_BALL_CACHE_BACKEDGE_CR_WITNESS_V1",
        "status":"SHA_QUALIFIED_SOURCE_BRANCH_SYNTAX_AND_MAY_REACH",
        "original_verified_cache_function_entry":cfg.src(ENTRY),
        "source_control_branches_after_initial_forward_skip":back,
        "source_witnesses_to_CC_and_FC_copy_sites":targets,
        "static_may_reachability_from_published_entry_verified":True,
        "cr_predicate_satisfiability_of_witness_proven":False,
        "whole_native_function_boundary_verified":False,
        "dynamic_guest_cache_execution_proven":False,
        "source_r13_global_is_live_selected_Ball_proven":False,
        "original_wood_or_foliage_collision_branch_verified":False,
        "ball_native_velocity_restitution_or_impulse_proven":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    parent=cfg.run(archive,capture)
    if (parent.get("original_seven_pair_sha_and_scene_gates_passed") is not True
        or parent.get("original_verified_capture_number")!=capture):
        raise ValueError("Original source SHA ownership gates failed")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for index,size in enumerate(seven.SIZE,1):
            file=seven.src._file(roots[capture],f"{capture}.{index}.raw",size)
            h=stack.enter_context(file.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(h.fileno(),0,access=mmap.ACCESS_READ)))
        def read(pc):
            if pc%4 or pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Native original source address outside verified MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        result=inspect(read)
    seven._check_archive(archive)
    return {**result,
            "original_source_archive_sha_and_scene_qualified":True,
            "original_source_capture":capture}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    opts=p.parse_args(argv)
    try:
        print(json.dumps(run(opts.archive,opts.capture),sort_keys=True,
                         separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,
            OverflowError,IndexError,AttributeError,struct.error):
        print(json.dumps({"kind":"P0_ORIGINAL_BALL_CACHE_BACKEDGE_CR_WITNESS_V1",
                          "status":"ABSTAIN_NATIVE_SOURCE_OR_REACHABILITY_GATE",
                          "training_approved":False}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
