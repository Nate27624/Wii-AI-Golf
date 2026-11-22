#!/usr/bin/env python3
"""P0 original Rev1 global Ball pointer and +0x5C candidate writer context.

Follow up successful original-source 7-capture SHA census:
Ball+0x3084 stw r3,-23304(r13) is the sole D-form direct
global-slot write in seven scanned public Golf source units;
Ball+0x2DC0/+0x2DC4 and +0x2FB8/+0x2FBC access global +0x5C;
Ball+0x2D8C, +0x314C and others are numerical +0x5C byte
store candidates with *unverified receiver identities*.

Report bounded original PPC lexical instruction categories and nearest
register definitions around exact global assignment / byte stores,
without assuming linear backward scans form a valid CFG path.
No training/physics/material/active-Ball promotion. Reads original
SHA-qualified private seven-pair archive only. No Dolphin, game
writes, video or new recordings. Only publicly identified Ball
source-relative code sites and syntactic instruction categories,
no original code words, heap pointers, XYZ or archive paths.
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
import p0_ball_global_5c_source_census_private as source
import p0_ball_cache_cfg_reachability_private as cfg
import p0_ball_cache_r27_lineage_private as lineage
import audit_p0_seven_numbered_source_pairs_private as seven

MEM1=source.MEM1
BALL=source.BALL
LO,HI=source.UNITS["Ball"]
SOURCE_ANCHORS={
    "global_pointer_slot_write":(0x3084,36,3,13,source.GLOBAL_SLOT),
    "possible_byte_store_r26":(0x2D8C,38,30,26,0x5C),
    "possible_byte_store_r3":(0x314C,38,5,3,0x5C),
    "direct_global_byte_load_1":(0x2DC4,34,0,4,0x5C),
    "direct_global_byte_load_2":(0x2FBC,34,0,3,0x5C),
}
DIRECT_LOADS=((0x2DC0,4),(0x2FB8,3))
BACKWARD_INSNS=12
FORWARD_INSNS=6
GPR_SEARCH_INSNS=80
MAX_DEFS=8


def site(pc):
    if pc%4 or not LO<=pc<HI:
        raise ValueError("Outside original Ball published source unit")
    return f"Ball+0x{pc-BALL:04X}"


def typed_instruction(pc,w):
    op=w>>26
    rT=(w>>21)&31
    rA=(w>>16)&31
    out={"source_site":site(pc),"primary_opcode_number":op}
    form=source.form(w)
    if form:
        out.update({"operation":form["mnemonic"],
                    "register_T_or_FPR":rT,
                    "base_register":rA,
                    "source_signed_displacement":form["disp"]})
        return out
    if op in (14,15):
        out.update({"operation":"addi" if op==14 else "addis",
                    "destination_register":rT,
                    "source_register":rA,
                    "signed_immediate":((w&65535)^32768)-32768})
        return out
    if op==31:
        xo=(w>>1)&1023
        out.update({"operation":"X_form",
                    "X_form_opcode_number":xo})
        if xo==444 and rT==((w>>11)&31):
            out.update({"operation":"mr",
                        "destination_register":rA,
                        "source_register":rT})
        elif xo in (339,371):
            out.update({"operation":"mfspr",
                        "destination_register":rT})
        return out
    t=cfg.decode_transfer(pc,w)
    if t["kind"]!="linear_not_decoded_control":
        out["operation"]=t["kind"]
        dest=t.get("target")
        if dest is not None:
            out["target_public_Ball_relative_if_bounded"]=(
                site(dest) if LO<=dest<HI and dest%4==0 else None)
            out["target_outside_published_Ball_unit"]=not (
                LO<=dest<HI and dest%4==0)
        return out
    out["operation"]="unclassified_source_opcode"
    return out


def verify_anchors(read):
    report=[]
    for name,(off,op,rt,ra,disp) in SOURCE_ANCHORS.items():
        x=source.form(read(BALL+off))
        if x is None or (x["op"],x["rT"],x["rA"],x["disp"])!=(
                op,rt,ra,disp):
            raise ValueError("Original native global/byte anchor changed")
        report.append({"evidence_name":name,"original_public_site":site(BALL+off),
                       "verified_opcode_name":x["mnemonic"],
                       "base_GPR":ra,
                       "value_or_destination_register":rt,
                       "numeric_displacement":disp,
                       "receiver_is_same_global_object_proven":False})
    for off,reg in DIRECT_LOADS:
        a=source.form(read(BALL+off))
        b=source.form(read(BALL+off+4))
        if not a or (a["op"],a["rT"],a["rA"],a["disp"])!=(
                32,reg,13,source.GLOBAL_SLOT):
            raise ValueError("Original global-pointer-to-byte source changed")
        if not b or (b["op"],b["rA"],b["disp"])!=(34,reg,0x5C):
            raise ValueError("Original byte read no longer follows global")
    return report


def context(read,off):
    at=BALL+off
    start=max(LO,at-4*BACKWARD_INSNS)
    end=min(HI,at+4*(FORWARD_INSNS+1))
    return {
        "anchor_site":site(at),
        "source_window_instructions":[typed_instruction(pc,read(pc))
                                     for pc in range(start,end,4)],
        "raw_native_instruction_words_in_report":False,
        "lexical_context_implies_single_function_or_taken_branch":False,
    }


def prior_defs(read,off,reg):
    at=BALL+off
    result=[]
    barriers=[]
    unknown_op_count=0
    for i in range(1,GPR_SEARCH_INSNS+1):
        pc=at-i*4
        if pc<LO: break
        w=read(pc)
        t=cfg.decode_transfer(pc,w)
        if t["kind"]!="linear_not_decoded_control":
            barriers.append(site(pc))
        defs=[(kind,src,disp) for dest,kind,src,disp
              in lineage.gpr_writers(w) if dest==reg]
        for kind,src,disp in defs:
            result.append({
                "possible_definition_source_site":site(pc),
                "recognized_definition_class":kind,
                "source_GPR_if_known":src,
                "source_displacement_if_known":disp,
                "branch_barriers_between_definition_and_access":
                    len(barriers),
                "definition_is_reaching_on_actual_CFG_path_proven":False})
        if w>>26==31 and ((w>>1)&1023) not in (
                444,339,371,28,316,23,55,87,119,266,40):
            unknown_op_count+=1
    return {
        "receiver_register":reg,
        "nearest_bounded_syntactic_definitions":result[:MAX_DEFS],
        "additional_definitions_not_displayed":max(0,len(result)-MAX_DEFS),
        "bounded_previous_control_transfer_sites":barriers[:MAX_DEFS],
        "unrecognized_X_form_instruction_count":unknown_op_count,
        "complete_CFG_SSA_receiver_identity_proven":False,
        "global_pointer_alias_at_byte_write_proven":False,
    }


def inspect(read):
    verified=verify_anchors(read)
    return {
        "kind":"P0_ORIGINAL_BALL_GLOBAL_POINTER_AND_BYTE_WRITER_CONTEXT_V1",
        "status":"ORIGINAL_NATIVE_GLOBAL_AND_BYTE_SOURCE_CONTEXT",
        "original_exact_native_anchor_sources_verified":verified,
        "original_bounded_source_windows":{
            name:context(read,args[0]) for name,args in SOURCE_ANCHORS.items()},
        "receiver_backwards_syntax_without_CFG_promotion":{
            name:prior_defs(read,off,ra)
            for name,(off,_,_,ra,_) in SOURCE_ANCHORS.items()},
        "r13_global_slot_has_exact_direct_native_writer_in_scanned_units":True,
        "global_pointer_writer_proves_selected_live_Ball_identity":False,
        "byte_stores_proven_same_global_receiver":False,
        "byte_field_nonzero_at_guest_execution_proven":False,
        "native_collision_contact_or_material_branch_proven":False,
        "native_ball_velocity_or_restitution_proven":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    old=source.run(archive,capture)
    if (old.get("status")!="SOURCE_QUALIFIED_GLOBAL_POINTER_BYTE_FIELD_CANDIDATES"
            or old.get("original_archive_and_native_scene_SHA_verified") is not True
            or old.get("original_capture")!=capture):
        raise ValueError("Previous original native source gates failed")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            path=seven.src._file(roots[capture],f"{capture}.{i}.raw",size)
            h=stack.enter_context(path.open("rb"))
            banks.append(stack.enter_context(mmap.mmap(
                h.fileno(),0,access=mmap.ACCESS_READ)))
        def read(pc):
            if pc%4 or pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Outside original SHA-gated MEM1 bank")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        result=inspect(read)
    seven._check_archive(archive)
    return {**result,"original_source_archive_SHA_and_scene_verified":True,
            "original_capture":capture}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    a=p.parse_args(argv)
    try:
        print(json.dumps(run(a.archive,a.capture),
                         sort_keys=True,separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,KeyError,TypeError,IndexError,AttributeError,
            OverflowError,struct.error):
        print(json.dumps({
            "kind":"P0_ORIGINAL_BALL_GLOBAL_POINTER_AND_BYTE_WRITER_CONTEXT_V1",
            "status":"ABSTAIN_ORIGINAL_SHA_OR_NATIVE_ANCHOR_GATE",
            "training_approved":False},sort_keys=True))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
