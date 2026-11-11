#!/usr/bin/env python3
"""Bounded Rev1 Golf controller-status consumer disassembly, read-only.

Intentionally source/function-qualified. It does not assert that observing a
controller getter means a D-pad press or club-selection write. Uses the
canonical SHA-checked original seven-pair archive, not a live Dolphin link.
No raw PPC words or absolute native instructions in reports.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import mmap
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_p0_club_controller_callgraph_private as graph
import audit_p0_club_player_byte_source_private as decode
import audit_p0_club_selection_code_private as base

# Bounded, source-backed target function *starts*. These are published
# identifiers from ogws RSPE01 Rev1 function symbols, not guessed pointers.
TARGETS = {
    "scene-status": (0x802B4794, 0x802B439C, 0x802B4474),
    "player-controller": (0x8029EC30,),
}
STATUS_NAME_HINTS = ("getExCoreStatus", "getAccel", "getNthController",
                     "getCoreStatus", "getFSStickButton")
MAX_INSTRUCTIONS = 180
BEFORE = 8
AFTER = 18


def _branch_target(pc, word):
    if base.op(word) == 16:
        bd = word & 0xFFFC
        if bd & 0x8000:
            bd -= 0x10000
        return (bd + (0 if word & 2 else pc)) & 0xFFFFFFFF
    edge = base.decode_branch(pc, word)
    return edge["target"] if edge else None


def _simple_instruction(pc, word, unit_lo, unit_hi):
    """A conservative decoder: unknown opcodes stay explicitly unknown."""
    a = decode.access(word)
    if a is not None:
        return decode.decode(pc,word,unit_lo,unit_hi)
    op = base.op(word)
    if op in (14,15,10,11,28,29,21):
        return decode.decode(pc,word,unit_lo,unit_hi)
    if op == 16:
        return decode.decode(pc,word,unit_lo,unit_hi)
    if op == 18:
        return decode.decode(pc,word,unit_lo,unit_hi)
    if op == 19:
        xo=(word>>1)&1023
        if word==0x4e800020:
            return "blr"
        if xo==528 and (word & 1):
            return "bctrl (indirect link; target unresolved)"
        if xo==16 and (word & 1):
            return "bclrl (indirect link; target unresolved)"
        return "op19 xo=%d (not decoded)" % xo
    if op == 31:
        xo=(word>>1)&1023
        rd,ra,rb=(word>>21)&31,(word>>16)&31,(word>>11)&31
        # PPC logical instructions have RA as destination and RS as input.
        if xo==28:
            return "and%s r%d,r%d,r%d" % (
                "." if word & 1 else "",ra,rd,rb)
        if xo==444:
            return ("mr r%d,r%d" % (ra,rd) if rd==rb
                    else "or r%d,r%d,r%d" % (ra,rd,rb))
        if xo==316:
            return "xor r%d,r%d,r%d" % (ra,rd,rb)
        if xo in (0,32):
            return "%s (register compare; operands omitted)" % (
                "cmp" if xo==0 else "cmpl")
        if xo in (266,40):
            return "%s r%d,r%d,r%d" % (
                "add" if xo==266 else "subf",rd,ra,rb)
        return "op31 xo=%d (not decoded)" % xo
    return "opcode=%d (not decoded)" % op


def review_function(bank, function, funcs, units, limit=5):
    start,end,label,unit=function
    base.require(start%4==0 and end%4==0 and 0<end-start<=0x5000,
                 "SOURCE_FUNCTION_UNQUALIFIED")
    base.require(1<=limit<=12, "SOURCE_REPORT_LIMIT_INVALID")
    offset=start-base.MEM1
    base.require(0<=offset<offset+(end-start)<=len(bank),
                 "SOURCE_NOT_IN_ORIGINAL_MEM1")
    words=struct.unpack_from(">"+("I"*((end-start)//4)),bank,offset)
    starts=[f[0] for f in funcs]
    calls=[]
    indirect=[]
    for j,word in enumerate(words):
        pc=start+j*4
        branch=base.decode_branch(pc,word)
        if branch is not None and branch["link"]:
            callee=graph.function_at(branch["target"],funcs,starts)
            if callee:
                calls.append((j,callee))
        elif base.op(word)==19 and ((word>>1)&1023)==528 and word&1:
            indirect.append(j)

    relevant=[(j,f) for j,f in calls
              if any(name in f[2] for name in STATUS_NAME_HINTS)]
    write_sites=[]
    for j,w in enumerate(words):
        a=decode.access(w)
        if (a and a["op"] in decode.ALL_STORE and a["base"] not in (0,1)
                and 0<=a["disp"]<=0x240):
            write_sites.append({
                "source_relative_pc":graph.format_site(start+4*j,units),
                "within_function_relative_pc":"+0x%03X"%(4*j),
                "operation":a["op"],
                "register":"%s%d"%("f" if a["op"] in decode.FP.values() else "r",a["reg"]),
                "base":"r%d"%a["base"],
                "object_displacement":"+0x%03X"%a["disp"],
                "receiver_not_verified":True,
            })
    windows=[]
    for index,(j,callee) in enumerate(relevant[:limit]):
        lo=max(0,j-BEFORE)
        hi=min(len(words),j+AFTER+1)
        # Stop at the current exact enclosing function, and never interpret
        # an instruction outside a public text/function boundary.
        instructions=[]
        for k in range(lo,hi):
            pc=start+4*k
            line=_simple_instruction(pc,words[k],units[unit][0],units[unit][1])
            mark=("STATUS_CALL" if k==j else "CONTEXT")
            instructions.append({
                "within_function_pc":"+0x%03X"%(4*k),
                "mnemonic":line,
                "role":mark,
            })
        windows.append({
            "callsite_in_unit":graph.format_site(start+4*j,units),
            "callsite_in_function":"+0x%03X"%(4*j),
            "target_public_function":callee[2],
            "target_public_source":callee[3],
            "disassembly_window":instructions,
            "return_value_flow_proven":False,
            "specific_button_mask_verified":False,
            "club_selector_write_verified":False
        })
    other=[{
        "callee":f[2],
        "callee_source":f[3],
        "callsite_in_function":"+0x%03X"%(4*j),
    } for j,f in calls if not any(q in f[2] for q in STATUS_NAME_HINTS)]
    return {
        "function":label,
        "source_unit":unit,
        "source_relative_start":graph.format_site(start,units)["source_offset"],
        "function_size_bytes":end-start,
        "status_getter_call_count":len(relevant),
        "status_getter_windows":windows,
        "other_resolved_direct_calls":other[:18],
        "indirect_bctrl_function_relative_sites":
            ["+0x%03X"%(4*j) for j in indirect[:18]],
        "nonstack_store_site_count":len(write_sites),
        "nonstack_store_site_examples":write_sites[:18],
        "unprinted_status_windows":max(0,len(relevant)-limit),
        "unprinted_nonstack_store_sites":max(0,len(write_sites)-18),
        "status_pointer_and_owner_unproven":True,
        "dpad_semantics_verified":False,
    }


def scan_original(archive,capture,focus,limit):
    fname=base.sealed_bank(archive,capture)
    units=base.source_units(json.loads(base.INDEX.read_text("utf-8")))
    funcs=graph.parse_public_functions(
        json.loads(graph.FUNCS.read_text("utf-8")),units)
    roots=TARGETS["scene-status"]+TARGETS["player-controller"] if focus=="all" else TARGETS[focus]
    f_by_start={f[0]:f for f in funcs}
    base.require(all(p in f_by_start for p in roots),"PUBLIC_REVIEW_FUNCTION_MISSING")
    with fname.open("rb") as fd, closing(
            mmap.mmap(fd.fileno(),0,access=mmap.ACCESS_READ)) as bank:
        results=[review_function(bank,f_by_start[root],funcs,units,limit)
                 for root in roots]
    return {
        "status":"P0_CLUB_CONTROLLER_STATUS_FUNCTION_REVIEW",
        "disc":"RSPE01","revision":1,
        "original_archive_sha_preflight_passed":True,
        "reviewed_functions":results,
        "all_reviewed_functions_public_source_qualified":True,
        "direct_status_getters_not_equivalent_to_dpad":True,
        "bounded_context_is_not_control_flow_proof":True,
        "runtime_dpad_semantics_verified":False,
        "club_selection_field_verified":False,
        "training_approved":False,
    }


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive",type=Path)
    ap.add_argument("--capture",type=int,default=5,choices=range(1,8))
    ap.add_argument("--focus",choices=("scene-status","player-controller","all"),
                    default="scene-status")
    ap.add_argument("--limit",type=int,default=4)
    ap.add_argument("--selftest",action="store_true")
    a=ap.parse_args(argv)
    if a.selftest:
        b=0x802B4794
        # make one native-layout synthetic function with one direct call.
        dest=0x8019BAE8
        code=struct.pack(">5I",0x60000000,
                         ((18<<26)|((dest-(b+4))&0x03fffffc)|1),
                         (32<<26)|(3<<21)|(3<<16)|0x20,
                         (28<<26)|(3<<21)|(3<<16)|0x400,
                         0x4e800020)
        bank=bytearray(b-base.MEM1+len(code))
        bank[b-base.MEM1:]=code
        unit="Pack/RPSports/RPGolScene/RPGolScene_unsplit.o"
        funcs=[(dest,dest+24,"getExCoreStatus__synthetic",
                "Pack/RPKernel/RPSysController.cpp"),
               (b,b+len(code),"fn_synthetic",unit)]
        units={unit:(b,b+0x1000)}
        r=review_function(bank,funcs[1],funcs,units)
        base.require(r["status_getter_call_count"]==1
                     and len(r["status_getter_windows"])==1,
                     "SELFTEST_FAILURE")
        print(json.dumps({"status":"SELFTEST_PASS",
                          "original_ram_read":False}))
        return 0
    if a.archive is None or not 1<=a.limit<=12:
        print(json.dumps({"status":"ABSTAIN_ARGUMENTS",
                          "training_approved":False}))
        return 2
    try:
        print(json.dumps(scan_original(a.archive,a.capture,a.focus,a.limit),
                         indent=2,sort_keys=True))
        return 0
    except (base.Abstain,ValueError,TypeError,KeyError,IndexError,
            struct.error,ImportError,OSError,OverflowError):
        print(json.dumps({"status":"ABSTAIN_UNQUALIFIED_SOURCE_OR_ARCHIVE",
                          "training_approved":False}))
        return 3


if __name__=="__main__":
    raise SystemExit(main())
