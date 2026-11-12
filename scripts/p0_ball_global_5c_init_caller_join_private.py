#!/usr/bin/env python3
"""Rev1 original source join: global registration and +0x5C initializer callsites.

The independently source-qualified pathways are:
  Ball+0x3080  bl Ball+0x3BA0
  Ball+0x3084  stw r3,-23304(r13)
  Ball+0x314C  stb r5,+0x5C(r3)  (prior li r5,1)
and, conditionally, a separate path clears global object's +0x5C.
This audit inventories the actual PPC source instructions around the
+0x3BA0 callee and the initializer, and static direct BL inbound edges
to the *candidate initializer region* (not a proven function entry).
It reports whether the +0x3BA0 bounded snippet itself directly calls
that region; it does NOT infer selected live Ball identity, aliasing,
allocator/constructor semantics, guest execution, or tree physics.

Read-only private SHA-gated seven-pair USA Rev1 source/scene data.
No ROM instructions, native raw words, heap addresses, user XYZ,
private file paths/assets, Dolphin, videos, new swings, guest writes,
or training in output.
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
import p0_ball_global_5c_zero_witness_private as prior
import p0_ball_global_byte_writer_context_private as syntax
import p0_ball_cache_cfg_reachability_private as cfg
import p0_ball_global_5c_initializer_r26_private as init
import audit_p0_seven_numbered_source_pairs_private as seven

BALL=prior.BALL
MEM1=prior.MEM1
LO,HI=init.source.UNITS["Ball"]
CALL=BALL+0x3080
GLOBAL_STORE=BALL+0x3084
LOCAL_TARGET=BALL+0x3BA0
INIT_STORE=BALL+0x314C
INIT_CANDIDATE_LO=BALL+0x30E0
INIT_CANDIDATE_HI=BALL+0x3120
TARGET_INSNS=32
INIT_CONTEXT_START=BALL+0x30E0
INIT_CONTEXT_END=BALL+0x3158
MAX_INBOUND=40
MAX_CALLEE_CONTEXT=8


def label(pc):
    if pc%4 or not LO<=pc<HI:
        raise ValueError("Source Ball site outside published code unit")
    return f"Ball+0x{pc-BALL:04X}"


def qualified(read):
    init.global_constructor(read)
    init.init(read)
    prior.exact_source(read)
    callee=cfg.decode_transfer(CALL,read(CALL))
    if callee["kind"]!="direct_bl_call" or callee["target"]!=LOCAL_TARGET:
        raise ValueError("Original local direct BL target changed")
    w=read(GLOBAL_STORE)
    if (w>>26,(w>>21)&31,(w>>16)&31,cfg.signed(w&65535,16))!=(
            36,3,13,init.source.GLOBAL_SLOT):
        raise ValueError("Original immediate postcall global store changed")
    if INIT_CANDIDATE_HI>=INIT_STORE or not LO<=LOCAL_TARGET<HI:
        raise ValueError("Incorrect source bounds")
    return {
        "source_direct_call":"Ball+0x3080",
        "source_direct_call_target":"Ball+0x3BA0",
        "source_next_instruction_global_pointer_slot_store":"Ball+0x3084",
        "original_call_result_GPR3_stored_after_call_syntactically":True,
        "callee_returns_a_valid_constructed_object_proven":False,
        "callee_returned_pointer_matches_initializer_receiver_proven":False,
    }


def source_window(read,start,end):
    if not LO<=start<end<=HI or (start|end)&3 or end-start>320:
        raise ValueError("Source context window not safely bounded")
    return [syntax.typed_instruction(pc,read(pc)) for pc in range(start,end,4)]


def inbound(read):
    all_inbound=[]
    callee_calls=[]
    for pc in range(LO,HI,4):
        t=cfg.decode_transfer(pc,read(pc))
        if t["kind"]!="direct_bl_call":
            continue
        target=t["target"]
        if INIT_CANDIDATE_LO<=target<INIT_CANDIDATE_HI:
            all_inbound.append({
                "direct_BL_source_site":label(pc),
                "source_target_within_initializer_candidate_region":label(target),
                "callee_is_initializer_function_entry_proven":False,
                "source_caller_receiver_is_global_object_proven":False,
            })
        if LOCAL_TARGET<=pc<LOCAL_TARGET+TARGET_INSNS*4:
            callee_calls.append({
                "local_helper_callsite":label(pc),
                "source_target_within_published_Ball_if_known":
                    label(target) if LO<=target<HI else None,
                "source_target_is_in_candidate_initializer_region":
                    INIT_CANDIDATE_LO<=target<INIT_CANDIDATE_HI,
                "original_external_target_symbol_qualified":False,
            })
    return {
        "candidate_initializer_region_first_site":label(INIT_CANDIDATE_LO),
        "candidate_initializer_region_last_included_site":
            label(INIT_CANDIDATE_HI-4),
        "total_direct_BL_to_candidate_region_in_public_Ball_unit":
            len(all_inbound),
        "bounded_direct_BL_callers":all_inbound[:MAX_INBOUND],
        "additional_Ball_direct_BL_callers_not_displayed":
            max(0,len(all_inbound)-MAX_INBOUND),
        "bounded_local_target_first_32_instruction_direct_BLs":
            callee_calls[:MAX_CALLEE_CONTEXT],
        "target_scan_region_is_confirmed_function_boundary":False,
        "whole_game_callers_or_indirect_dispatch_exhausted":False,
    }


def inspect(read):
    exact=qualified(read)
    callsites=inbound(read)
    return {
        "kind":"P0_ORIGINAL_BALL_GLOBAL_5C_INIT_CALLER_JOIN_V1",
        "status":"SOURCE_QUALIFIED_REGISTRATION_INITIALIZER_CALLSITE_CENSUS",
        "source_original_global_store_and_initializer_anchors":exact,
        "local_global_registration_target_first_32_instructions":
            source_window(read,LOCAL_TARGET,LOCAL_TARGET+TARGET_INSNS*4),
        "initializer_candidate_nearby_instructions":
            source_window(read,INIT_CONTEXT_START,INIT_CONTEXT_END),
        "source_direct_callsite_census":callsites,
        "previous_source_global_zero_write_is_conditionally_possible":True,
        "initializer_receiver_aliases_r13_global_pointer_proven":False,
        "source_direct_3BA0_call_to_initializer_candidate_present":
            any(x["source_target_is_in_candidate_initializer_region"]
                for x in callsites["bounded_local_target_first_32_instruction_direct_BLs"]),
        "object_identity_selected_live_Ball_proven":False,
        "native_wood_foliage_collision_branch_proven":False,
        "guest_impact_execution_velocity_restitution_proven":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    old=prior.run(archive,capture)
    if not(old.get("original_SHA_archive_scene_and_native_source_verified")
           and old.get("original_capture")==capture):
        raise ValueError("Original Rev1 source and SHA gates failed")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        bank=[]
        for i,size in enumerate(seven.SIZE,1):
            p=seven.src._file(roots[capture],f"{capture}.{i}.raw",size)
            h=stack.enter_context(p.open("rb"))
            bank.append(stack.enter_context(
                mmap.mmap(h.fileno(),0,access=mmap.ACCESS_READ)))
        def read(pc):
            if pc%4 or pc<MEM1 or pc+4>MEM1+len(bank[0]):
                raise ValueError("Original native source outside SHA-qualified bank")
            return struct.unpack_from(">I",bank[0],pc-MEM1)[0]
        report=inspect(read)
    seven._check_archive(archive)
    return {**report,"original_SHA_scene_native_source_verified":True,
            "original_capture":capture}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",type=Path,required=True)
    parser.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=parser.parse_args(argv)
    try:
        print(json.dumps(run(args.archive,args.capture),
                         sort_keys=True,separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,
            OverflowError,AttributeError,struct.error) as exc:
        print(json.dumps({
            "kind":"P0_ORIGINAL_BALL_GLOBAL_5C_INIT_CALLER_JOIN_V1",
            "status":"ABSTAIN_ORIGINAL_SHA_OR_SOURCE_CALLSITE_GATES",
            "failure_exception_class":type(exc).__name__,
            "exception_message_or_private_data_emitted":False,
            "training_approved":False},sort_keys=True))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
