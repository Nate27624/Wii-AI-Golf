#!/usr/bin/env python3
"""Original source-only PPC Ball cache backedge operand lineage.

Last original SHA-verified audit proved static CFG may-reach of CC/FC
copy writers. Original exact adjacent comparisons and branches imply:
Ball+2FC0: signed cmpwi r0,0; +2FC4: beq elsewhere, so FALLTHROUGH
requires r0 != 0.
Ball+2FC8: signed cmpwi r28,0; +2FCC: blt back to Ball+2CD0,
so TAKEN BACKEDGE requires signed r28 < 0.
The second branch is LT (CR0[0]), NOT EQ (CR0[2]).

Check original source encoding, the exact bounded static path witness,
source-syntax register definitions along that witness, and local native
r0/r28 writers. Unknown instructions, indirect transfers and calls are
conservatively unresolved; there is no runtime predicate proof,
selected Ball identity, physics velocity, wood/foliage native branch
or training qualification. Original raw PPC words, heap pointers,
game XYZ, file paths and assets are NEVER reported.
No Dolphin, video, new swings, guest RAM read/write or network access.
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
import p0_ball_cache_backedge_condition_private as branches
import p0_ball_cache_cfg_reachability_private as cfg
import p0_ball_cache_r27_lineage_private as lineage
import audit_p0_seven_numbered_source_pairs_private as seven

BASE=cfg.BASE
MEM1=cfg.MEM1
CMP_R0=0x2FC0
BEQ=0x2FC4
CMP_R28=0x2FC8
BLT=0x2FCC
BACKEDGE_TARGET=0x2CD0
COPY_TARGET=0x2D04
MAX_SITES=32


def cmpwi(read,offset,register):
    w=read(BASE+offset)
    op=w>>26
    bf=(w>>23)&7
    l=(w>>21)&1
    ra=(w>>16)&31
    imm=cfg.signed(w&0xFFFF,16)
    if (op,bf,l,ra,imm)!=(11,0,0,register,0):
        raise ValueError("Original signed cmpwi register or source gate changed")
    return {
        "source_site":cfg.src(BASE+offset),
        "source_operand_register":register,
        "signed_immediate_comparison_to_zero":True,
        "CR_field_index":0,
        "signed_register_value_known_from_static_code":False,
    }


def bc_gate(read,offset,bi,dest):
    dec=cfg.decode_transfer(BASE+offset,read(BASE+offset))
    if (dec["kind"],dec["BO"],dec["BI"],dec["target"])!=(
            "conditional_bc",12,bi,BASE+dest):
        raise ValueError("Original conditional PPC branch semantics changed")
    return {
        "source_site":cfg.src(BASE+offset),
        "CR_bit_index":bi,
        "branch_target":cfg.src(BASE+dest),
        "fallthrough":cfg.src(BASE+offset+4),
    }


def witness(read):
    graph=cfg.explore(read)
    path=cfg.route(graph["parent"],BASE+COPY_TARGET)
    if not path:
        raise ValueError("Original source CC store no longer statically reachable")
    source_pc=[BASE+x for x in (CMP_R0,BEQ,CMP_R28,BLT,BACKEDGE_TARGET)]
    if any(pc not in path for pc in source_pc):
        raise ValueError("Original shortest CC copy witness no longer uses backedge")
    for at,nxt in ((BEQ,CMP_R28),(BLT,BACKEDGE_TARGET)):
        index=path.index(BASE+at)
        if path[index+1]!=BASE+nxt:
            raise ValueError("Original witness changed conditional edge")
    return path


def kind_and_source(word,reg):
    matches=[]
    for dest,kind,src,disp in lineage.gpr_writers(word):
        if dest!=reg:
            continue
        item={
            "GPR_writer_class":kind,
            "source_GPR_if_decoded":src,
            "source_offset_if_decoded":disp,
            "known_immediate_constant_if_li":None,
        }
        # PPC li is alias of addi rD,r0,imm, where rA=0 denotes zero,
        # not the contents of r0. This is a syntactic immediate ONLY.
        if kind=="addi" and src==0:
            item["known_immediate_constant_if_li"]=disp
        matches.append(item)
    return matches


def trace_register(read,path,through_offset,reg):
    pc_limit=BASE+through_offset
    if pc_limit not in path:
        raise ValueError("Original static source witness missing comparison")
    prefix=path[:path.index(pc_limit)]
    recognized=[]
    unknown_calls=[]
    for pc in prefix:
        q=kind_and_source(read(pc),reg)
        for entry in q:
            recognized.append({
                "public_source_site":cfg.src(pc),**entry})
        dec=cfg.decode_transfer(pc,read(pc))
        if dec["kind"]=="direct_bl_call" and reg in (0,3,4,5,6,7,8,9,10,11,12):
            unknown_calls.append(cfg.src(pc))
    recent=recognized[-1] if recognized else None
    # The X-form writer inventory is intentionally non-exhaustive;
    # an unrecognized instruction may alter this register. No exact
    # value or path-specific SSA proof is promoted.
    return {
        "operand_GPR":reg,
        "comparison_public_site":cfg.src(pc_limit),
        "original_static_witness_instructions_before_cmp":len(prefix),
        "recognized_writer_sites_on_static_witness":recognized[-MAX_SITES:],
        "additional_earlier_writers_not_displayed":
            max(0,len(recognized)-MAX_SITES),
        "nearest_recognized_writer_on_static_witness":recent,
        "prior_calls_that_may_clobber_volatile_operand":unknown_calls[-MAX_SITES:],
        "unknown_source_instruction_register_effects_exhausted":False,
        "register_runtime_value_proven":False,
    }


def local_defs(read,begin,end,reg):
    findings=[]
    for off in range(begin,end,4):
        if off==end:
            break
        for q in kind_and_source(read(BASE+off),reg):
            findings.append({
                "public_source_site":cfg.src(BASE+off),**q})
    return {
        "source_scan_start":cfg.src(BASE+begin),
        "source_scan_end_inclusive":cfg.src(BASE+end-4),
        "recognized_GPR_writer_count":len(findings),
        "bounded_native_writer_sites":findings[-MAX_SITES:],
        "complete_GPR_producer_decode_proven":False,
    }


def inspect(read):
    left=cmpwi(read,CMP_R0,0)
    right=cmpwi(read,CMP_R28,28)
    eq=bc_gate(read,BEQ,2,0x2FDC)
    lt=bc_gate(read,BLT,0,BACKEDGE_TARGET)
    static=witness(read)
    if not (branches.cr_predicate(cfg.decode_transfer(
            BASE+BEQ,read(BASE+BEQ)))["CR_bit_within_field_index"]==2
            and branches.cr_predicate(cfg.decode_transfer(
            BASE+BLT,read(BASE+BLT)))["CR_bit_within_field_index"]==0):
        raise ValueError("Original CR EQ/LT branch bits changed")
    return {
        "kind":"P0_ORIGINAL_BALL_CC_BACKEDGE_SIGNED_OPERAND_LINEAGE_V1",
        "status":"ORIGINAL_SHA_QUALIFIED_SIGNED_BRANCH_PREDICATES",
        "original_adjacent_cmpwi_source": [left,right],
        "original_exact_branch_sites":[eq,lt],
        "CC_writer_backedge_necessary_source_predicates":[
            "r0_not_equal_to_0_for_Ball+0x2FC4_fallthrough",
            "signed_r28_less_than_0_for_Ball+0x2FCC_taken"],
        "same_static_witness_constraints_formally_contradictory":False,
        "bounded_original_copy_witness_instructions":len(static)-1,
        "source_witness_operand_reaching_writer_syntax":{
            "r0":trace_register(read,static,CMP_R0,0),
            "r28":trace_register(read,static,CMP_R28,28),
        },
        "nearby_native_branch_operand_writer_census":{
            "r0":local_defs(read,0x2FB8,CMP_R0,0),
            "r28":local_defs(read,0x2FB8,CMP_R28,28),
        },
        "branch_witness_path_condition_feasible_at_runtime_proven":False,
        "guest_CR_values_or_register_values_observed":False,
        "selected_Ball_or_r13_global_object_identity_proven":False,
        "wood_vs_foliage_collision_handler_verified":False,
        "native_velocity_or_restitution_verified":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    prior=branches.run(archive,capture)
    if (prior.get("original_source_archive_sha_and_scene_qualified") is not True
        or prior.get("original_source_capture")!=capture):
        raise ValueError("Earlier original native source gates failed")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for n,size in enumerate(seven.SIZE,1):
            file=seven.src._file(folders[capture],f"{capture}.{n}.raw",size)
            h=stack.enter_context(file.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(h.fileno(),0,access=mmap.ACCESS_READ)))
        def read(pc):
            if pc%4 or pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Original native code outside gated MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        result=inspect(read)
    seven._check_archive(archive)
    return {**result,"original_archive_SHA_and_native_source_gates_verified":True,
            "original_verified_capture":capture}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=p.parse_args(argv)
    try:
        print(json.dumps(run(args.archive,args.capture),
                         sort_keys=True,separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,KeyError,TypeError,IndexError,
            OverflowError,AttributeError,struct.error):
        print(json.dumps({
            "kind":"P0_ORIGINAL_BALL_CC_BACKEDGE_SIGNED_OPERAND_LINEAGE_V1",
            "status":"ABSTAIN_ORIGINAL_SHA_BRANCH_OR_SOURCE",
            "training_approved":False}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
