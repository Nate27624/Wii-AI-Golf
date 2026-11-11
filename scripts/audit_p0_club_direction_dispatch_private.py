#!/usr/bin/env python3
"""Read-only static Rev1 Golf Up/Down dispatch and receiver-store investigation.

Original seven-pair archive SHA-qualified via canonical P0 verifier; exact
public RSPE01 Rev1 source function bounds. No Dolphin contact, memory edits,
private RAM bytes, native absolute code addresses or training promotion.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import json
import mmap
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import audit_p0_club_selection_code_private as source
import audit_p0_club_controller_callgraph_private as graph
import audit_p0_club_player_byte_source_private as player
import audit_p0_club_dpad_handler_flow_private as flow

DISPATCH=0x802A9BC8
RELATED=0x802A8850
MANAGER=0x802A28DC
PUBLIC_TARGETS={
    "direction-dispatch":DISPATCH,
    "post-direction":RELATED,
}
MAX_LINES=150

def r4_activity(word):
    """Record *syntactic* r4 operations, never invent register dataflow."""
    op=source.op(word)
    if op in (10,11):
        ra=(word>>16)&31
        if ra==4:
            return {"operation":"compare_r4_immediate",
                    "immediate":source.signed16(word)}
    if op in (14,15):
        rd=(word>>21)&31
        ra=(word>>16)&31
        if ra==4 or rd==4:
            return {"operation":"addi_or_addis_uses_r4",
                    "destination":"r%d"%rd,
                    "base":"r%d"%ra,
                    "immediate":source.signed16(word)}
    if op==21:
        rs=(word>>21)&31
        ra=(word>>16)&31
        if rs==4 or ra==4:
            return {"operation":"rlwinm_uses_r4",
                    "source":"r%d"%rs,
                    "destination":"r%d"%ra}
    if op in (28,29):
        rs=(word>>21)&31
        ra=(word>>16)&31
        if rs==4 or ra==4:
            return {"operation":"andi_uses_r4",
                    "source":"r%d"%rs,
                    "destination":"r%d"%ra,
                    "mask":word&0xffff}
    if op==31:
        ra=(word>>16)&31
        rs=(word>>21)&31
        rb=(word>>11)&31
        if 4 in (rs,ra,rb):
            return {"operation":"op31_uses_r4",
                    "xo":(word>>1)&1023,
                    "registers":["r%d"%v for v in (rs,ra,rb)]}
    a=player.access(word)
    if a and (a["reg"]==4 or a["base"]==4):
        return {"operation":"memory_access_r4",
                "kind":a["op"],"base":"r%d"%a["base"],
                "register":("f" if a["op"] in player.FP.values() else "r")+str(a["reg"]),
                "displacement":a["disp"]}
    return None

def audit_function(code, target, funcs, units, lines=120):
    start,end,label,unit=target
    source.require(len(code)==end-start and len(code)%4==0
                   and 0<len(code)<=0x5000,
                   "UNQUALIFIED_FUNCTION_BYTE_WINDOW")
    source.require(type(lines) is int and 24<=lines<=MAX_LINES,
                   "UNQUALIFIED_OUTPUT_BOUND")
    words=struct.unpack(">"+"I"*(len(code)//4),code)
    events=[]
    calls=[]
    stores=[]
    for j,word in enumerate(words):
        pc=start+4*j
        b=source.decode_branch(pc,word)
        if b and b["link"]:
            f=graph.function_at(b["target"],funcs)
            calls.append({
                "within_function_site":"+0x%03X"%(4*j),
                "public_unit_relative_site":graph.format_site(pc,units)["source_offset"],
                "callee_public_name":f[2] if f else "UNMAPPED_FUNCTION",
                "callee_source_unit":f[3] if f else graph.source_owner(b["target"],units),
                "argument_proven_interprocedural":False})
        a=player.access(word)
        if a and a["op"] in player.ALL_STORE and a["base"] not in (0,1):
            stores.append({
                "within_function_site":"+0x%03X"%(4*j),
                "op":a["op"],
                "base_register":"r%d"%a["base"],
                "field_displacement":a["disp"],
                "source_value_register":("f" if a["op"] in player.FP.values() else "r")+str(a["reg"]),
                "selected_club_owner_verified":False})
        ra=r4_activity(word)
        if ra:
            events.append({"within_function_site":"+0x%03X"%(4*j),**ra})
    # Context windows: beginning is crucial for arg registers, plus any
    # r4 comparisons/operations and nearby direct calls or stores.
    priorities=set(range(min(len(words),28)))
    for event in events:
        i=int(event["within_function_site"],16)//4
        if event["operation"] in ("compare_r4_immediate","addi_or_addis_uses_r4",
                                  "andi_uses_r4","rlwinm_uses_r4"):
            priorities.update(range(max(0,i-6),min(len(words),i+13)))
    for st in stores[:10]:
        i=int(st["within_function_site"],16)//4
        priorities.update(range(max(0,i-4),min(len(words),i+6)))
    indices=sorted(priorities)
    if len(indices)>lines:
        # Keep prologue and primary argument uses before lower-priority stores.
        first=list(range(min(28,len(words))))
        later=[j for j in indices if j not in first]
        indices=(first+later)[:lines]
    context=[]
    for j in indices:
        pc=start+4*j
        context.append(flow.decode_site(pc,words[j],target,funcs,units))
    return {
        "status":"P0_CLUB_DIRECTION_DISPATCH_STATIC_SOURCE_REVIEW",
        "function":label,
        "source_unit":unit,
        "source_relative_function_start":graph.format_site(start,units)["source_offset"],
        "function_size_bytes":len(code),
        "incoming_direction_arg_r4_from_manager_is_static_callsite_witness":start==DISPATCH,
        "r4_uses_are_syntactic_only":events[:40],
        "direct_calls":calls[:28],
        "direct_call_count":len(calls),
        "nonstack_store_sites":stores[:28],
        "nonstack_store_count":len(stores),
        "decoded_context":context,
        "decoded_context_truncated":len(priorities)>lines,
        "indirect_dispatch_and_register_provenance_unresolved":True,
        "dpad_to_selected_club_value_proven":False,
        "selected_club_field_verified":False,
        "training_approved":False,
    }

def audit_original(archive,capture,focus,lines):
    archive_bank=source.sealed_bank(archive,capture)
    units=source.source_units(json.loads(source.INDEX.read_text("utf-8")))
    funcs=graph.parse_public_functions(json.loads(graph.FUNCS.read_text("utf-8")),units)
    start=PUBLIC_TARGETS[focus]
    f=graph.function_at(start,funcs)
    source.require(f is not None and f[0]==start
                   and f[3].startswith(graph.GOLF_PREFIX),
                   "PUBLIC_GOLF_FUNCTION_MISSING")
    with archive_bank.open("rb") as fh,closing(
            mmap.mmap(fh.fileno(),0,access=mmap.ACCESS_READ)) as mm:
        result=audit_function(bytes(mm[f[0]-source.MEM1:f[1]-source.MEM1]),
                              f,funcs,units,lines)
    result["original_archive_sha_preflight_passed"]=True
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path)
    p.add_argument("--capture",type=int,choices=range(1,8),default=5)
    p.add_argument("--focus",choices=tuple(PUBLIC_TARGETS),
                   default="direction-dispatch")
    p.add_argument("--max-lines",type=int,default=120)
    p.add_argument("--selftest",action="store_true")
    a=p.parse_args(argv)
    if a.selftest:
        pc=DISPATCH
        f=(pc,pc+20,"test_direction_dispatch",
           "Pack/RPSports/RPGolScene/RPGolScene_unsplit.o")
        instructions=[
            (11<<26)|(4<<16)|1,
            (16<<26)|(12<<21)|(2<<16)|8,
            (32<<26)|(3<<21)|(4<<16)|0x20,
            (36<<26)|(3<<21)|(29<<16)|0x340,
            0x4e800020]
        code=struct.pack(">5I",*instructions)
        z=audit_function(code,f,[f],{f[3]:(pc,pc+0x1000)},40)
        source.require(z["nonstack_store_count"]==1
                       and z["r4_uses_are_syntactic_only"]
                       and z["selected_club_field_verified"] is False,
                       "SELFTEST_SOURCE_FAILED")
        print(json.dumps({"status":"SELFTEST_PASS","native_archive_opened":False}))
        return 0
    if a.archive is None or not 24<=a.max_lines<=MAX_LINES:
        print(json.dumps({"status":"ABSTAIN_INVALID_ARGS",
                          "training_approved":False}))
        return 2
    try:
        print(json.dumps(audit_original(a.archive,a.capture,a.focus,a.max_lines),
                         sort_keys=True,indent=2))
        return 0
    except (source.Abstain,ValueError,TypeError,KeyError,IndexError,
            OSError,ImportError,OverflowError,struct.error):
        print(json.dumps({"status":"ABSTAIN_SOURCE_OR_ARCHIVE",
                          "training_approved":False}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
