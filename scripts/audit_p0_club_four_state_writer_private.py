#!/usr/bin/env python3
"""Proof-gated 4-state index writer in Wii Sports Golf Rev1 direction handler.

Offline, canonical SHA-verified original seven-pair MEM1 archive. Uses exact
public OGWS function boundaries. Static PPC dataflow only; does not assert
that index maps to Driver/Iron/Wedge/Putter or approve training.
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
import audit_p0_club_selection_code_private as base
import audit_p0_club_controller_callgraph_private as graph
import audit_p0_club_dpad_handler_flow_private as dec

MANAGER_PC=0x802A28DC
HANDLER_PC=0x802A9BC8
MANAGER_UNIT="Pack/RPSports/RPGolScene/RPGolPlayerManager.cpp"
HANDLER_UNIT="Pack/RPSports/RPGolScene/RPGolScene_unsplit.o"
MANAGER_CALLS=((0x160,0,0x158),(0x178,1,0x170),
               (0x254,0,0x24c),(0x26c,1,0x264))
# (handler_relative increment/decrement addresses), verified as structure,
# NOT user-visible club semantics or ordered club label.
BRANCH_A=0x0e8
INCREMENT=(0x0f0,0x0f4,0x0f8,0x0fc,0x100)
DECREMENT=(0x234,0x238,0x23c,0x240,0x244)

def op_imm(w):
    return base.signed16(w)

def word_at(blob,offset):
    base.require(offset%4==0 and 0<=offset<=len(blob)-4,
                 "FUNCTION_OFFSET_OUTSIDE_PUBLIC_BOUNDARY")
    return struct.unpack_from(">I",blob,offset)[0]

def require_access(w,mnemonic,reg,owner,displacement):
    a=base.decode_access(w)
    base.require(a is not None and a["op"]==mnemonic and a["reg"]==reg
                 and a["base"]==owner and a["disp"]==displacement,
                 "SOURCE_FIELD_ACCESS_WITNESS_MISMATCH")
    return a

def require_cmpwi(w,reg,imm):
    base.require(base.op(w)==11 and (w>>16)&31==reg and
                 op_imm(w)==imm and ((w>>21)&7)==0,
                 "SOURCE_BOUND_COMPARE_WITNESS_MISMATCH")

def require_step(w,source_reg,destination,delta):
    base.require(base.op(w)==14 and (w>>16)&31==source_reg
                 and (w>>21)&31==destination and op_imm(w)==delta,
                 "SOURCE_STEP_WITNESS_MISMATCH")

def branch_target(pc,w):
    base.require(base.op(w)==16,"BRANCH_OPCODE_MISMATCH")
    bd=w & 0xfffc
    if bd&0x8000: bd-=0x10000
    return (bd+(0 if w&2 else pc))&0xffffffff

def require_call(manager_blob,site,expected_arg,setup):
    w=word_at(manager_blob,site)
    b=base.decode_branch(MANAGER_PC+site,w)
    base.require(b is not None and b["link"] and
                 b["target"]==HANDLER_PC,
                 "SOURCE_DIRECTION_CALLSITE_MISMATCH")
    li=word_at(manager_blob,site-4)
    base.require(base.op(li)==14 and (li>>21)&31==4
                 and (li>>16)&31==0 and op_imm(li)==expected_arg,
                 "SOURCE_DIRECTION_ARGUMENT_MISMATCH")
    global_load=word_at(manager_blob,setup)
    require_access(global_load,"lwz",3,13,-0x5A80)
    # Expected r3 setup two instructions before direct call, followed by li.
    base.require(setup==site-8,"SOURCE_DIRECTION_RECEIVER_LOAD_NOT_ADJACENT")
    return {"manager_public_unit_callsite":"+"+format(
                 MANAGER_PC+site-0x802A2210,"#07x").replace("0x","0x"),
            "manager_function_relative_callsite":"+0x%03X"%site,
            "direction_argument_r4":expected_arg,
            "callee_public_function":"fn_802A9BC8",
            "receiver_r3_load_from":"lwz r3,-0x5A80(r13)",
            "receiver_instance_value_verified":False}

def decode_window(blob,start,end,func,funcs,units):
    pc0=func[0]
    base.require(start%4==end%4==0 and 0<=start<end<=len(blob),
                 "INVALID_WINDOW")
    return [dec.decode_site(pc0+i,word_at(blob,i),func,funcs,units)
            for i in range(start,end,4)]

def evidence(manager_blob,handler_blob,funcs,units):
    """Fail closed unless exact symmetric index writes and caller edges match."""
    base.require(len(manager_blob)==984 and len(handler_blob)==1048,
                 "SOURCE_EXACT_FUNCTION_LENGTH_CHANGED")
    # Source branch determines r4=0 path and r4!=0 path.
    require_cmpwi(word_at(handler_blob,BRANCH_A),4,0)
    gate=word_at(handler_blob,BRANCH_A+4)
    base.require(branch_target(HANDLER_PC+BRANCH_A+4,gate)
                 ==HANDLER_PC+DECREMENT[0],
                 "SOURCE_DIRECTION_BRANCH_TARGET_MISMATCH")
    # In first direction branch, integer >=4 no increment, else +1.
    require_access(word_at(handler_blob,INCREMENT[0]),"lwz",4,3,0x1C)
    require_cmpwi(word_at(handler_blob,INCREMENT[1]),4,3)
    base.require(base.op(word_at(handler_blob,INCREMENT[2]))==16,
                 "SOURCE_MAX_GUARD_MISSING")
    require_step(word_at(handler_blob,INCREMENT[3]),4,0,1)
    require_access(word_at(handler_blob,INCREMENT[4]),"stw",0,3,0x1C)
    # In other direction branch, <=0 no decrement, else -1.
    require_access(word_at(handler_blob,DECREMENT[0]),"lwz",4,3,0x1C)
    require_cmpwi(word_at(handler_blob,DECREMENT[1]),4,0)
    base.require(base.op(word_at(handler_blob,DECREMENT[2]))==16,
                 "SOURCE_MIN_GUARD_MISSING")
    require_step(word_at(handler_blob,DECREMENT[3]),4,0,-1)
    require_access(word_at(handler_blob,DECREMENT[4]),"stw",0,3,0x1C)
    caller=[]
    for call_off,arg,setup in MANAGER_CALLS:
        caller.append(require_call(manager_blob,call_off,arg,setup))
    handler=graph.function_at(HANDLER_PC,funcs)
    manager=graph.function_at(MANAGER_PC,funcs)
    base.require(handler is not None and manager is not None
                 and handler[0]==HANDLER_PC and manager[0]==MANAGER_PC
                 and handler[3]==HANDLER_UNIT and manager[3]==MANAGER_UNIT,
                 "PUBLIC_FUNCTION_OWNERSHIP_MISMATCH")
    return {
        "status":"SOURCE_CONFIRMED_FOUR_STATE_INDEX_WRITER_NOT_YET_GAME_CLUB_ID",
        "game":"RSPE01","revision":1,
        "static_direction_calls":caller,
        "source_selected_index_receiver_chain":{
            "caller":"global pointer load from r13-0x5A80",
            "callee":"r3 input argument",
            "writer":"stw r0,+0x01C(r3)",
            "global_r13_base_runtime_value_known":False,
            "current_selected_club_owner_confirmed":False,
        },
        "selector_behavior_source":{
            "r4_eq_0":"load field +0x1C, compare with 3, increment +1, store +0x1C",
            "r4_ne_0":"load field +0x1C, compare with 0, decrement -1, store +0x1C",
            "field_displacement":"+0x01C",
            "element_width_bytes":4,
            "observed_index_bounds":{"minimum":0,"maximum":3},
            "index_to_visible_club_mapping_verified":False,
        },
        "direction_handler_source_unit":HANDLER_UNIT,
        "direction_handler_increment_context":
            decode_window(handler_blob,0x0E8,0x110,handler,funcs,units),
        "direction_handler_decrement_context":
            decode_window(handler_blob,0x22C,0x254,handler,funcs,units),
        "executed_selected_club_writes_verified":False,
        "game_club_id_verified":False,
        "training_approved":False,
    }

def analyze_original(archive,capture):
    file=base.sealed_bank(archive,capture)
    units=base.source_units(json.loads(base.INDEX.read_text("utf-8")))
    funcs=graph.parse_public_functions(json.loads(graph.FUNCS.read_text("utf-8")),units)
    fmanager=graph.function_at(MANAGER_PC,funcs)
    fhandler=graph.function_at(HANDLER_PC,funcs)
    base.require(fmanager is not None and fhandler is not None
                 and fmanager[0]==MANAGER_PC and fhandler[0]==HANDLER_PC,
                 "PUBLIC_FUNCTIONS_NOT_FOUND")
    with file.open("rb") as fh,closing(
            mmap.mmap(fh.fileno(),0,access=mmap.ACCESS_READ)) as mem:
        mgr=bytes(mem[fmanager[0]-base.MEM1:fmanager[1]-base.MEM1])
        callee=bytes(mem[fhandler[0]-base.MEM1:fhandler[1]-base.MEM1])
    result=evidence(mgr,callee,funcs,units)
    result["original_archive_sha_preflight_passed"]=True
    return result

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive",type=Path)
    ap.add_argument("--capture",choices=range(1,8),type=int,default=5)
    ap.add_argument("--selftest",action="store_true")
    args=ap.parse_args(argv)
    if args.selftest:
        # Synthetic offline opcode shape without any native RAM.
        a=(32<<26)|(4<<21)|(3<<16)|0x1c
        b=(36<<26)|(0<<21)|(3<<16)|0x1c
        c=(14<<26)|(0<<21)|(4<<16)|1
        require_access(a,"lwz",4,3,28)
        require_access(b,"stw",0,3,28)
        require_step(c,4,0,1)
        print(json.dumps({"status":"SELFTEST_PASS",
                          "native_archive_opened":False}))
        return 0
    if args.archive is None:
        print(json.dumps({"status":"ABSTAIN_ARGS","training_approved":False}))
        return 2
    try:
        print(json.dumps(analyze_original(args.archive,args.capture),
                         indent=2,sort_keys=True))
        return 0
    except (base.Abstain,ValueError,TypeError,KeyError,IndexError,
            OSError,ImportError,OverflowError,struct.error):
        print(json.dumps({"status":"ABSTAIN_SOURCE_OR_ARCHIVE",
                          "training_approved":False}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
