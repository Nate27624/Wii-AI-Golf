#!/usr/bin/env python3
"""P0 Golf original-Rev1 cache r27 source/argument provenance audit.

Use original SHA-gated 7-pair native source capture only; NO Dolphin,
new shot, video, live RPC, memory modification, private asset export.
Prior reports found three complete Ball-unit stfs triplets at
Ball+0x2D04,+0x2F6C,+0x2FA8 all using r27 as base, and two static
BL callers to 0x80299C70. This audit inspects how r27 is *written*
in the bounded function window, the actual near-CC FP load offsets
and how r3 is set before each direct caller. The result is typed
register/instruction SYNTAX, not a complete CFG/ABI proof that r27
is the source-selected active Ball, or that a tree hit happened.

The output contains no original PPC instruction words, ROM/asset bytes,
private pointers/addresses/XYZ, personal paths or native source snippets.
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
import p0_tree_ball_writer_register_context_private as prior
import p0_tree_ball_source_store_inventory_private as inventory
import audit_p0_seven_numbered_source_pairs_private as seven

MEM1=0x80000000
FN_START=0x80299C70
FN_END=0x8029A038  # coarse SOURCE WINDOW, not an established full function end
SOURCE_BALL=inventory.SOURCE_UNITS["Ball"][0]
BASE_REG=27
CALLS=(0x2B8C,0x2C80)
GROUPS={
    "CC_D0_D4": (0x2D04,0x2D0C,0x2D14),
    "F0_F4_F8": (0x2F6C,0x2F70,0x2F74),
    "FC_100_104": (0x2FA8,0x2FAC,0x2FB0),
}
MAX_FP_SCAN=24
MAX_CALL_SCAN=24
MAX_DEF_SITES=32


def dform(w):
    op=w>>26
    if op not in (14,15,24,25,26,27,28,29,32,33,34,35,48,49,50,51,52,53):
        return None
    d=w&0xFFFF
    if d&0x8000:
        d-=0x10000
    return {
        "op":op,"rt":(w>>21)&31,"ra":(w>>16)&31,"offset":d
    }


def gpr_writers(w):
    """Non-exhaustive candidates; X-form and update forms handled explicitly."""
    op=w>>26
    rt=(w>>21)&31
    ra=(w>>16)&31
    rb=(w>>11)&31
    if op in (14,15,32,34,35,46):
        if op==46:
            return [(i,"lmw_register_restored_from_memory",None,None)
                    for i in range(rt,32)]
        name={14:"addi",15:"addis",32:"lwz",34:"lbz",35:"lbzu"}[op]
        out=[(rt,name,ra,((w&65535)^32768)-32768)]
        if op==35:
            out.append((ra,"lbzu_update_base",ra,None))
        return out
    if op==33:
        return [(rt,"lwzu",ra,((w&65535)^32768)-32768),
                (ra,"lwzu_update_base",ra,None)]
    if op in (24,25,26,27,28,29):
        return [(ra,{24:"ori",25:"oris",26:"xori",27:"xoris",
                      28:"andi",29:"andis"}[op],rt,None)]
    if op in (20,21,23):
        return [(ra,{20:"rlwimi",21:"rlwinm",23:"rlwnm"}[op],rt,None)]
    if op==31:
        xo=(w>>1)&1023
        if xo==444:
            if rt==rb:
                return [(ra,"mr",rt,None)]
            return [(ra,"or",rt,None)]
        if xo in (339,371):
            return [(rt,"mfspr",None,None)]
        # Partial X-form destination classes, not complete SSA/CFG.
        # Logical operations (and/xor) write rA, whereas
        # arithmetic/load results commonly write rD (word's RT slot).
        if xo in (28,316):
            return [(ra,"X_form_logic_dest_rA",rt,None)]
        if xo in (23,55,87,119,266,40):
            return [(rt,"X_form_register_result",ra,None)]
    return []


def site(pc):
    if pc%4 or not SOURCE_BALL<=pc<inventory.SOURCE_UNITS["Ball"][1]:
        raise ValueError("PPC source site outside public Ball unit")
    return f"Ball+0x{pc-SOURCE_BALL:04X}"


def write_candidates(read,begin,end,reg):
    if begin%4 or end%4 or begin<inventory.SOURCE_UNITS["Ball"][0] or end>FN_END:
        raise ValueError("Unqualified native code scan interval")
    if begin>=end:
        raise ValueError("Empty code interval")
    matches=[]
    for pc in range(begin,end,4):
        writers=[(kind,from_reg,offset)
                 for dst,kind,from_reg,offset in gpr_writers(read(pc))
                 if dst==reg]
        for kind,src,disp in writers:
            matches.append({
                "public_source_site":site(pc),
                "syntactic_writer_class":kind,
                "source_gpr_if_simple":src,
                "source_disp_if_syntactically_decoded":disp,
                "selected_ball_receiver_ownership_proven":False,
            })
    return {
        "recognized_candidate_GPR_definition_count":len(matches),
        "recognized_GPR_definition_sites":matches[:MAX_DEF_SITES],
        "excess_definitions_not_displayed":max(0,len(matches)-MAX_DEF_SITES),
        "unknown_PPC_ops_or_CFG_paths_proven_absent":False,
    }


def scan_fp_origin(read,store_pc):
    q=dform(read(store_pc))
    if not q or q["op"]!=52:
        raise ValueError("Expected stfs source site changed")
    dest_fpr=q["rt"]
    for i in range(1,MAX_FP_SCAN+1):
        pc=store_pc-4*i
        if pc<FN_START:
            break
        instruction=read(pc)
        if prior.is_control(instruction):
            return {
                "classification":"abstain_prior_control_transfer",
                "source_float_producer_is_same_object_proven":False}
        op=instruction>>26
        reg=(instruction>>21)&31
        if reg==dest_fpr and op in (48,49,50,51,59,63):
            f=dform(instruction)
            return {
                "classification":"lfs_or_lfsu" if op in (48,49) else (
                    "other_FP_instruction_or_load"),
                "syntactic_producer_public_source_site":site(pc),
                "source_FP_reg_index":dest_fpr,
                "syntactic_source_base_GPR":f["ra"] if f else None,
                "syntactic_source_displacement":f["offset"] if f else None,
                "instructions_preceding_store":i,
                "source_float_producer_is_same_object_proven":False,
            }
    return {
        "classification":"abstain_no_bounded_linear_producer",
        "source_float_producer_is_same_object_proven":False}


def groups(read):
    report={}
    for name,offsets in GROUPS.items():
        pcs=[SOURCE_BALL+x for x in offsets]
        decoded=[dform(read(pc)) for pc in pcs]
        if any(not x or x["op"]!=52 or x["ra"]!=BASE_REG for x in decoded):
            raise ValueError("Original three cache triplets no longer all use r27")
        predecessor=write_candidates(read,FN_START,pcs[0],BASE_REG)
        report[name]={
            "original_source_triplet_sites":[site(pc) for pc in pcs],
            "source_float_store_base_GPR":BASE_REG,
            "source_cache_field_offsets":[
                f"+0x{d['offset']:03X}" for d in decoded],
            "source_preceding_r27_definitions":predecessor,
            "source_nearest_fpr_producers":[scan_fp_origin(read,pc) for pc in pcs],
            "same_active_selected_Ball_receiver_proven":False,
        }
    return report


def caller_arguments(read):
    out=[]
    for offset in CALLS:
        pc=SOURCE_BALL+offset
        branch=inventory.units.direct_b(pc,read(pc))
        if branch is None or not branch[1] or branch[0]!=FN_START:
            raise ValueError("Qualified exact Ball cache entry caller changed")
        lo=max(inventory.SOURCE_UNITS["Ball"][0],pc-MAX_CALL_SCAN*4)
        prior_defs=[]
        stop=None
        for at in range(pc-4,lo-4,-4):
            w=read(at)
            if prior.is_control(w):
                stop="intervening_call_branch_or_return_unknown"
                break
            for dst,kind,src,disp in gpr_writers(w):
                if dst==3:
                    prior_defs.append({
                        "public_source_site":site(at),
                        "syntactic_writer_class":kind,
                        "source_GPR_if_simple":src,
                        "source_disp_if_syntactically_decoded":disp,
                    })
            if prior_defs:
                break
        out.append({
            "source_direct_BL_site":site(pc),
            "exact_source_entry_is_cache_fn_80299C70":True,
            "nearest_bounded_r3_argument_assignment":prior_defs,
            "bounded_backward_stop_reason":stop or (
                "nearest_assignment_found" if prior_defs else "window_exhausted"),
            "actual_runtime_r3_object_identity_proven":False,
            "source_selected_ball_receiver_proven":False,
        })
    return out


def inspect(read):
    g=groups(read)
    return {
        "kind":"P0_ORIGINAL_BALL_CACHE_R27_LINEAGE_V1",
        "status":"ORIGINAL_REV1_SHA_SOURCE_QUALIFIED_REGISTER_SYNTAX",
        "source_cache_r27_write_ancestry":g,
        "source_direct_call_r3_argument_origins":caller_arguments(read),
        "native_function_range_is_exact_CFG_proven":False,
        "source_store_base_r27_is_live_selected_ball_proven":False,
        "source_0xCC_0xF0_0xFC_semantic_role_proven":False,
        "runtime_wood_vs_leaves_branch_or_impact_proven":False,
        "ball_guest_physics_velocity_proven":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    original=prior.run(archive,capture)
    if not (original["original_sha_scene_tree_and_kcol_gates_verified"] and
            original["original_capture_number"]==capture):
        raise ValueError("Original SHA scene or KCol native validation failed")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for n,size in enumerate(seven.SIZE,1):
            path=seven.src._file(roots[capture],f"{capture}.{n}.raw",size)
            h=stack.enter_context(path.open("rb"))
            banks.append(stack.enter_context(mmap.mmap(
                h.fileno(),0,access=mmap.ACCESS_READ)))
        def word(pc):
            if pc%4 or pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Out-of-bank original native code")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        result=inspect(word)
    seven._check_archive(archive)
    return {**result,
            "original_seven_pair_SHA_and_scene_qualified":True,
            "original_source_verified_capture":capture}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=p.parse_args(argv)
    try:
        result=run(args.archive,args.capture)
        print(json.dumps(result,sort_keys=True,separators=(",",":"),
                         allow_nan=False))
        return 0
    except (ValueError,OSError,TypeError,KeyError,IndexError,
            OverflowError,AttributeError,struct.error):
        print(json.dumps({
            "kind":"P0_ORIGINAL_BALL_CACHE_R27_LINEAGE_V1",
            "status":"ABSTAIN_NATIVE_SHA_REGISTER_DATAFLOW",
            "training_approved":False}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
