#!/usr/bin/env python3
"""Read-only original Wii Golf tree processing loop, camera math and field origin.

This is a continuation of source-qualified 94-tree study. It follows the
*real* FieldManager+0x230C->Tree+0x047C loop and the known
FieldManager+0x2BB4->Tree+0x000C flag-writer loop, identifies source
arguments, and examines the two callee helpers at MapObjBase/Camera.

SHA+scene+94x84 source loop and exact original PPC receiver instructions
must match. The names of compiled source units are NOT method identity.
No native memory coordinates, resources or ROM words committed; --detail
prints bounded original PPC source words only in operator's local terminal.
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
import audit_p0_seven_numbered_source_pairs_private as seven
import p0_tree_hitbox_source_callgraph_private as native
import p0_tree_hitbox_five_calls_private as ppc
import p0_tree_flag_receiver_disambiguation_private as prior

FIELD=native.UNITS["FieldManager"][0]
TREE=native.UNITS["Tree"][0]
CAMERA=0x8029BBB4
BASE=0x8028F9FC
MEM1=0x80000000
COUNT=94
STRIDE=84

WINDOWS=(
    ("fieldmanager_method_prologue","FieldManager",0x2130,0x2160),
    ("tree_loop_with_second_argument","FieldManager",0x22EC,0x2328),
    ("tree_distance_writer_loop","FieldManager",0x2BA0,0x2BD0),
    ("tree_update_and_flag_branch","Tree",0x047C,0x0624),
    ("camera_math_callee","Camera",0x028C,0x031C),
    ("base_model_handle_callee","MapObjBase",0x0B84,0x0BF4),
)
UNIT_RANGES={
    "FieldManager":native.UNITS["FieldManager"],
    "Tree":native.UNITS["Tree"],
    "Camera":(CAMERA,0x8029C2F8),
    "MapObjBase":(BASE,0x80290B44),
}
assert sum((hi-lo)//4 for _,__,lo,hi in WINDOWS)==209
ANCHORS={
    FIELD+0x214C:0x7C7F1B78, # mr r31,r3, same caller frame as 94-array loop
    # Reader: source-owned FieldManager-like r31 +0x20 array, r29 argument,
    # 84-byte element stride, count +0x1C.
    FIELD+0x2300:0x801F0020,
    FIELD+0x2304:0x7FA4EB78,
    FIELD+0x2308:0x7C60D214,
    FIELD+0x2310:0x3B5A0054,
    FIELD+0x2314:0x3BDE0001,
    FIELD+0x2318:0x801F001C,
    FIELD+0x231C:0x7C1E0000,
    # Known writer, same array member offsets, separate register.
    FIELD+0x2BAC:0x801C0020,
    FIELD+0x2BB0:0x7C60FA14,
    FIELD+0x2BB8:0x3BFF0054,
    FIELD+0x2BBC:0x3BDE0001,
    FIELD+0x2BC0:0x801C001C,
    # Second argument origin is shared global pointer+0x0C.
    FIELD+0x22EC:0x806DA4E0,
    FIELD+0x22F8:0x83A3000C,
    TREE+0x049C:0x7C7E1B78,
    TREE+0x04C8:0x389E0030,
    TREE+0x04D8:0xD03E004C,
    TREE+0x04F0:0xD03E0050,
    TREE+0x0504:0x881E0048,
}
LINKS={
    FIELD+0x230C:TREE+0x047C,
    FIELD+0x2BB4:TREE+0x000C,
    TREE+0x04B0:0x80290580,
    TREE+0x04B8:0x80290580,
    TREE+0x04C0:0x80290580,
    TREE+0x04CC:0x8029BE40,
    TREE+0x04EC:0x8029BE40,
}


def source_owner(pc):
    for key,(lo,hi) in UNIT_RANGES.items():
        if lo<=pc<hi:
            return key+"+0x"+format(pc-lo,"04X")
    return "external_source"


def preamble_candidates(read):
    """Only *candidate* r31 origin sites, never assert function ownership."""
    low=FIELD+0x1C00
    high=FIELD+0x22F0
    mr_r31_r3=[]
    stwu_frames=[]
    writes_r31=[]
    for pc in range(low,high,4):
        w=read(pc)
        off=pc-FIELD
        # Exact PPC mr r31,r3 requires OR r31,r3,r3.
        if w==0x7C7F1B78:
            mr_r31_r3.append(f"+0x{off:04X}")
        if w>>26==37 and ((w>>21)&31)==1 and ((w>>16)&31)==1:
            stwu_frames.append(f"+0x{off:04X}")
        # Avoid claiming complete reaching definition / caller's register.
    return {
        "scan_relative_range":"+0x1C00..+0x22EC",
        "candidate_mr_r31_r3_sites":mr_r31_r3[:12],
        "candidate_mr_r31_r3_count":len(mr_r31_r3),
        "candidate_stack_prologue_sites":stwu_frames[-12:],
        "candidate_stack_prologue_count":len(stwu_frames),
        "reader_r31_source_fieldmanager_proven":False,
    }


def inspect(read, detail=False):
    prior.validate_source(read)
    for pc,word in ANCHORS.items():
        if read(pc)!=word:
            raise ValueError("Native tree array loop/camera math anchor mismatch")
    # +0x2138 is a PowerPC stack frame prologue (exact size source-specific).
    frame=read(FIELD+0x2138)
    if not (frame>>26==37 and ((frame>>21)&31)==1 and ((frame>>16)&31)==1):
        raise ValueError("FieldManager second-loop method entry changed")
    # No subsequent stack-frame prologue before the +0x230C loop:
    # supports r31=receiver provenance, not a full CFG/call-site proof.
    for pc in range(FIELD+0x213C,FIELD+0x230C,4):
        w=read(pc)
        if w>>26==37 and ((w>>21)&31)==1 and ((w>>16)&31)==1:
            raise ValueError("Unexpected new function entry before second loop")
    for pc,target in LINKS.items():
        if native.direct_b(pc,read(pc))!=(target,True):
            raise ValueError("Native direct call target mismatch")
    out=[]
    for name,unit,start,end in WINDOWS:
        lo,hi=UNIT_RANGES[unit]
        if not (0<=start<end and start%4==0 and end%4==0 and lo+end<=hi):
            raise ValueError("Source code window outside owner")
        calls=[]
        float_accesses=[]
        op_counts={}
        instructions=[]
        for offset in range(start,end,4):
            pc=lo+offset
            w=read(pc)
            b=native.direct_b(pc,w)
            if b:
                if len(calls)<24:
                    calls.append({
                        "site":f"+0x{offset:04X}",
                        "link":b[1],
                        "target":source_owner(b[0])})
            d=native.dform(w)
            if d and d[0] in ("lfs","lfsu","stfs","stfsu") and len(float_accesses)<22:
                float_accesses.append({
                    "site":f"+0x{offset:04X}",
                    "op":d[0],
                    "base":"r"+str(d[2]),
                    "offset":d[3]})
            if detail:
                instructions.append(
                    f"{unit}+0x{offset:04X} {w:08X} {ppc.ppc(pc,w)}")
        row={
            "name":name,
            "public_source_owner":unit,
            "public_relative_range":f"+0x{start:04X}..+0x{end-4:04X}",
            "words":(end-start)//4,
            "direct_branches":calls,
            "float_field_accesses":float_accesses,
            "tree_collision_geometry_verified":False,
        }
        if detail:
            row["code"]=instructions
        out.append(row)
    return {"read_loop_and_flag_writer_use_same_plus_0x20_array_field":True,
            "both_loops_use_84_byte_element_stride":True,
            "read_loop_uses_plus_0x1c_element_count":True,
            "read_loop_additional_argument_global_plus_0x0c":True,
            "native_r31_is_fieldmanager_verified":False,
            "r31_assigned_from_method_r3_at_source_relative":"+0x214C",
            "second_loop_within_same_native_method_frame":True,
            "tree_plus_0x047c_receiver_identity_verified":False,
            "candidate_reader_function_semantics_verified":False,
            "tree_hitbox_geometry_verified":False,
            "ball_contact_response_verified":False,
            "r31_preamble_search":preamble_candidates(read),
            "windows":out,
            "training_approved":False}


def run(archive:Path,capture:int,detail=False):
    if capture not in range(1,8):
        raise ValueError("Invalid capture")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            p=seven.src._file(folders[capture],f"{capture}.{i}.raw",size)
            h=stack.enter_context(p.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(h.fileno(),0,access=mmap.ACCESS_READ)))
        rd=seven.roster.TwoBankReader(*banks)
        owner=seven._get(rd)["field"]
        count=rd.u32(owner+0x1C)
        base=rd.u32(owner+0x20)
        if count!=COUNT or seven.roster._bank(base,STRIDE*COUNT)!="MEM2":
            raise ValueError("Original source tree array/count invalid")
        def code(pc):
            if pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Out of native MEM1 code bounds")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        result=inspect(code,detail=detail)
    seven._check_archive(archive)
    return {
        "kind":"P0_TREE_94_ARRAY_SECOND_RECEIVER_AND_GEOMETRY",
        "status":"SOURCE_QUALIFIED_DUAL_94_TREE_LOOP_CONTEXT",
        "capture":capture,
        "source_tree_count":count,
        "original_sha_and_scene_gated":True,
        **result,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",required=True,type=Path)
    parser.add_argument("--capture",choices=range(1,8),type=int,default=7)
    parser.add_argument("--detail",action="store_true")
    args=parser.parse_args(argv)
    try:
        r=run(args.archive,args.capture,args.detail)
        if args.detail:
            print(json.dumps({k:v for k,v in r.items() if k!="windows"},
                             sort_keys=True,separators=(",",":")))
            for w in r["windows"]:
                print(f"===== {w['name']} {w['public_relative_range']} =====")
                print("\n".join(w["code"]))
            print("===== END TREE SECOND LOOP / CALLEE WINDOWS =====")
        else:
            print(json.dumps(r,sort_keys=True,separators=(",",":")))
        return 0
    except (OSError,ValueError,KeyError,IndexError,OverflowError,
            TypeError,AttributeError,struct.error):
        print('{"status":"ABSTAIN_SOURCE_DUAL_TREE_LOOPS","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
