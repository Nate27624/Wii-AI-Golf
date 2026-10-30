#!/usr/bin/env python3
"""Exact-function PPC control-flow context around Golf D-pad bit masks.

Offline only. Canonical SHA-checked ORIGINAL RSPE01 Rev1 seven-pair MEM1 archive.
Uses public ogws object/function map and public EGG Up/Down masks.
Prints bounded source-relative decoded PPC instructions, branch destinations,
resolved direct callees, and *possible* receiver-field displacements.
Does NOT prove input origin, executed branch, club index, or training validity.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from contextlib import closing
import json
import mmap
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import audit_p0_club_dpad_integer_selector_private as select
import audit_p0_club_controller_callgraph_private as graph
import audit_p0_club_controller_status_consumers_private as asm
import audit_p0_club_player_byte_source_private as access
import audit_p0_club_selection_code_private as base

# Exact published Rev1 function starts from original four-club scan.
TARGETS={
    "player-manager":0x802A28DC,
    "ball-object":0x80298E70,
    "scene-handler":0x802ABD50,
}
MAX_CONTEXT=28
MAX_RENDER=180


def conditional(pc,w):
    """PPC bc: displacement is a 14-bit signed count of 4-byte words."""
    if base.op(w)!=16:
        return None
    bd=w & 0xfffc
    if bd & 0x8000:
        bd-=0x10000
    return {"target":(bd + (0 if w&2 else pc))&0xffffffff,
            "bo":(w>>21)&31,"bi":(w>>16)&31,
            "absolute":bool(w&2),"link":bool(w&1)}


def branch_format(pc,target,f,units):
    start,end,name,unit=f
    if start<=target<end:
        return "fn+0x%03X"%(target-start)
    owner=graph.source_owner(target,units)
    if owner is None:
        return "OUTSIDE_PUBLISHED_TEXT"
    return "%s+0x%05X"%(owner,target-units[owner][0])


def interest(words,start):
    masks=[]
    steps=[]
    for i,w in enumerate(words):
        if m:=select.immediate_button_test(w):
            masks.append((i,m))
        if step:=select.ordinal_step(w):
            steps.append((i,step))
    # Avoid interpreting +/-1 unrelated to D-pad path; stage-one report
    # matched steps within a local 48-instruction window.
    near_steps=[
        (i,s) for i,s in steps if any(abs(i-j)<=48 for j,_ in masks)
    ]
    return masks,near_steps


def coalesce(ranges):
    ranges.sort()
    merged=[]
    for start,end in ranges:
        if merged and start<=merged[-1][1]+2:
            merged[-1]=(merged[-1][0],max(merged[-1][1],end))
        else:
            merged.append((start,end))
    return merged


def decode_site(pc,w,f,funcs,units):
    opcode=base.op(w)
    start,end,_,unit=f
    public=graph.format_site(pc,units)["source_offset"]
    text=asm._simple_instruction(pc,w,units[unit][0],units[unit][1])
    kind="instruction"
    meta={}
    if m:=select.immediate_button_test(w):
        kind="POSSIBLE_DPAD_MASK"
        meta={"source_bitmask":"0x%04X"%m["bits"],
              "masked_source_register":"r%d"%((w>>21)&31),
              "masked_destination_register":"r%d"%((w>>16)&31),
              "mask_operation":m["opcode"],
              "rotated":m["rotated"]}
    if step:=select.ordinal_step(w):
        kind="ORDINAL_STEP"
        meta=step
    if bc:=conditional(pc,w):
        kind="CONDITIONAL_BRANCH"
        text="bc BO=%d BI=%d -> %s"%(
            bc["bo"],bc["bi"],branch_format(pc,bc["target"],f,units))
        meta={"branch_target":branch_format(pc,bc["target"],f,units),
              "condition_code_not_resolved":True}
    b=base.decode_branch(pc,w)
    if b is not None:
        kind="DIRECT_CALL" if b["link"] else "DIRECT_BRANCH"
        dest=graph.function_at(b["target"],funcs)
        text=("bl " if b["link"] else "b ")+branch_format(
            pc,b["target"],f,units)
        if dest:
            meta={"callee_public_function":dest[2],
                  "callee_source_unit":dest[3],
                  "callee_exact_public_start":graph.format_site(dest[0],units)["source_offset"]}
        else:
            meta={"target_source_unit":graph.source_owner(b["target"],units)}
    a=access.access(w)
    if a:
        meta.update({
            "access_kind":a["op"],
            "access_disp":"+0x%03X"%a["disp"] if a["disp"]>=0
                          else "-0x%03X"%(-a["disp"]),
            "receiver_base_not_proven":"r%d"%a["base"],
        })
        if a["op"] in access.ALL_STORE and a["base"] not in (0,1):
            kind="NONSTACK_STORE"
    return {"function_relative_pc":"+0x%03X"%(pc-start),
            "public_unit_relative_pc":public,
            "role":kind,"decoded":text,
            **({"details":meta} if meta else {})}


def trace_bytes(code,f,funcs,units,context=16,max_lines=140):
    start,end,name,unit=f
    base.require(len(code)==end-start and len(code)>0
                 and len(code)%4==0 and len(code)<=0x5000,
                 "PUBLIC_FUNCTION_CODE_SPAN_INVALID")
    base.require(4<=context<=MAX_CONTEXT and
                 20<=max_lines<=MAX_RENDER,"BAD_TRACE_LIMITS")
    words=struct.unpack(">"+"I"*(len(code)//4),code)
    masks,steps=interest(words,start)
    if not masks:
        return {"function":name,"source_unit":unit,"dpad_mask_sites":[],
                "status":"NO_DIRECT_BIT_SHAPE","selector_verified":False}
    anchor_indices=sorted({i for i,_ in masks}|{i for i,_ in steps})
    spans=coalesce([(max(0,i-context),min(len(words),i+context+1))
                    for i in anchor_indices])
    instruction_indices=[]
    for a,b in spans:
        instruction_indices.extend(range(a,b))
    instruction_indices=sorted(set(instruction_indices))
    truncated=len(instruction_indices)>max_lines
    instruction_indices=instruction_indices[:max_lines]
    rows=[decode_site(start+4*i,words[i],f,funcs,units)
          for i in instruction_indices]
    calls=[]
    for i,w in enumerate(words):
        b=base.decode_branch(start+4*i,w)
        if b is None or not b["link"]:
            continue
        callee=graph.function_at(b["target"],funcs)
        calls.append({
            "public_unit_relative_callsite":graph.format_site(start+4*i,units)["source_offset"],
            "within_function_callsite":"+0x%03X"%(4*i),
            "callee_public_function":callee[2] if callee else "UNKNOWN_PUBLIC_FUNCTION",
            "callee_unit":callee[3] if callee else graph.source_owner(b["target"],units),
            "return_value_proven_used_for_club":False,
        })
    stores=[]
    for i,w in enumerate(words):
        a=access.access(w)
        if a and a["op"] in access.ALL_STORE and a["base"] not in (0,1):
            stores.append({
                "unit_relative_store":graph.format_site(start+4*i,units)["source_offset"],
                "kind":a["op"],"base":"r%d"%a["base"],
                "displacement":a["disp"],
                "receiver_chain_verified":False,
            })
    return {
        "status":"SOURCE_QUALIFIED_DPAD_CANDIDATE_FUNCTION_TRACE",
        "function":name,
        "source_unit":unit,
        "public_unit_relative_function_start":graph.format_site(start,units)["source_offset"],
        "function_size_bytes":len(code),
        "dpad_up_mask_sites":[graph.format_site(start+4*i,units)["source_offset"]
                              for i,m in masks if m["bits"]&select.UP],
        "dpad_down_mask_sites":[graph.format_site(start+4*i,units)["source_offset"]
                                for i,m in masks if m["bits"]&select.DOWN],
        "nearby_signed_ordinal_steps":[{
            "public_unit_relative_site":graph.format_site(start+4*i,units)["source_offset"],
            **step} for i,step in steps],
        "all_resolved_direct_calls":calls[:24],
        "direct_call_count":len(calls),
        "all_nonstack_store_sites":stores[:24],
        "nonstack_store_count":len(stores),
        "selected_windows_instruction_count":len(instruction_indices),
        "selected_windows_truncated":truncated,
        "instructions":rows,
        "source_mask_applied_to_live_controller_status_verified":False,
        "club_index_destination_verified":False,
        "runtime_dpad_execution_verified":False,
        "training_approved":False,
    }


def analyze_original(archive,capture,focus,context,max_lines):
    file=base.sealed_bank(archive,capture)
    units=base.source_units(json.loads(base.INDEX.read_text("utf-8")))
    funcs=graph.parse_public_functions(
        json.loads(graph.FUNCS.read_text("utf-8")),units)
    pc=TARGETS[focus]
    found=graph.function_at(pc,funcs)
    base.require(found is not None and found[0]==pc and
                 found[3].startswith(graph.GOLF_PREFIX),
                 "UNQUALIFIED_HANDLER_FUNCTION")
    with file.open("rb") as fh, closing(
            mmap.mmap(fh.fileno(),0,access=mmap.ACCESS_READ)) as bank:
        start,end,_,_=found
        result=trace_bytes(bytes(bank[start-base.MEM1:end-base.MEM1]),
                           found,funcs,units,context,max_lines)
    result["original_archive_sha_preflight_passed"]=True
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path)
    p.add_argument("--capture",type=int,choices=range(1,8),default=5)
    p.add_argument("--focus",choices=tuple(TARGETS),default="player-manager")
    p.add_argument("--context",type=int,default=16)
    p.add_argument("--max-lines",type=int,default=140)
    p.add_argument("--selftest",action="store_true")
    a=p.parse_args(argv)
    if a.selftest:
        pc=0x802A28DC
        f=(pc,pc+20,"fn_synthetic",
           "Pack/RPSports/RPGolScene/RPGolPlayerManager.cpp")
        words=[(28<<26)|(3<<21)|(3<<16)|8,
               (14<<26)|(3<<21)|(3<<16)|0xffff,
               (28<<26)|(3<<21)|(3<<16)|4,
               (14<<26)|(3<<21)|(3<<16)|1,
               0x4e800020]
        b=struct.pack(">5I",*words)
        u={f[3]:(pc,pc+0x100)}
        r=trace_bytes(b,f,[f],u,4,50)
        base.require(len(r["dpad_up_mask_sites"])==1
                     and len(r["dpad_down_mask_sites"])==1
                     and len(r["nearby_signed_ordinal_steps"])==2,
                     "SELFTEST_DPAD_FAILED")
        print(json.dumps({"status":"SELFTEST_PASS","native_ram_used":False}))
        return 0
    if a.archive is None or not 4<=a.context<=MAX_CONTEXT or not 20<=a.max_lines<=MAX_RENDER:
        print(json.dumps({"status":"ABSTAIN_INVALID_ARGUMENTS",
                          "training_approved":False}))
        return 2
    try:
        print(json.dumps(analyze_original(a.archive,a.capture,a.focus,
                                          a.context,a.max_lines),
                         indent=2,sort_keys=True))
        return 0
    except (base.Abstain,TypeError,ValueError,KeyError,IndexError,
            OSError,ImportError,struct.error,OverflowError):
        print(json.dumps({"status":"ABSTAIN_UNQUALIFIED_ORIGINAL_ARCHIVE_OR_SOURCE",
                          "training_approved":False}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
