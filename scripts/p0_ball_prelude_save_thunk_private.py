#!/usr/bin/env python3
"""Rev1 original PPC Ball entry save-helper: resolve r4 volatility conservatively.

Original Ball+0x2CB0 is a direct BL immediately before the incoming r3/r4
are saved to callee r27/r28. Although PPC EABI treats r4 as volatile,
a *specific* compiler-generated register-save thunk may leave r4 intact.
This audit inspects the actual target in the SHA-verified ORIGINAL MEM1
bank, not a guessed ABI behavior. It promotes r4 preservation only if
the complete bounded helper path is a sequence of ordinary non-updating
PPC stw stores of saved nonvolatile GPRs r27..r31 followed by ordinary
unconditional blr, without any other instructions/branches/calls.

The tool re-checks original SHA, source, scene/94-tree and Ball-KCol
gates through the prior signed backedge audit, verifies the exact two
caller r4 setup instructions and all intermediates before their BLs,
and reports source-relative code sites and helper instruction categories.
It NEVER emits original native instruction words, executable code bytes,
native absolute target addresses, user XYZ, private paths or captures.
No Dolphin, video, new swings, runtime memory reads/writes or training.
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
import p0_ball_backedge_postcall_arg_private as prior
import p0_ball_cache_cfg_reachability_private as cfg
import p0_ball_cache_r27_lineage_private as lineage
import audit_p0_seven_numbered_source_pairs_private as seven

BASE=cfg.BASE
MEM1=cfg.MEM1
PRELUDE=BASE+prior.PRELUDE_CALL
MAX_THUNK_INSNS=16
MIN_EXEC_SOURCE_ADDR=MEM1+0x3000
# Literal original source archive MEM1 bank remains authoritative.
CALLER_SETUPS=(
    (0x2B84,0x2B8C,4,4,1),     # addi r4,r4,+1
    (0x2C78,0x2C80,4,0,-1),    # li r4,-1 (addi r4,0,-1)
)


def is_blr(word):
    return (word>>26==19
            and ((word>>1)&1023)==16
            and ((word>>21)&31)==20
            and ((word>>16)&31)==0
            and (word&1)==0)


def stw(word):
    if word>>26!=36:
        return None
    off=cfg.signed(word&65535,16)
    return {"stored_gpr":(word>>21)&31,
            "base_gpr":(word>>16)&31,
            "signed_stack_relative_disp":off}


def thunk(read,bank_limit):
    site=PRELUDE
    desc=cfg.decode_transfer(site,read(site))
    if desc["kind"]!="direct_bl_call" or not (desc["target"]%4==0):
        raise ValueError("Original prelude call is not exact PPC BL")
    target=desc["target"]
    if not MIN_EXEC_SOURCE_ADDR<=target<bank_limit-MAX_THUNK_INSNS*4:
        return {
            "source_call_site":cfg.src(site),
            "target_inside_original_MEM1_source_code_candidate_range":False,
            "callee_is_store_only_GPR_save_thunk_verified":False,
            "r4_is_preserved_by_exact_callee_source_verified":False,
            "reason":"source_target_outside_bounded_original_exec_window",
        }
    items=[]
    terminal=None
    blocked_reason=None
    for i in range(MAX_THUNK_INSNS):
        w=read(target+4*i)
        if is_blr(w):
            terminal=i
            break
        q=stw(w)
        if not q or q["stored_gpr"] not in range(27,32) or q[
                "base_gpr"] not in (1,11):
            blocked_reason="instruction_not_plain_nonvolatile_GPR_store"
            break
        items.append({
            "callee_entry_relative_instruction_index":i,
            "native_instruction_class":"plain_stw_nonvolatile_GPR",
            **q,
        })
    if terminal is None and blocked_reason is None:
        blocked_reason="bounded_helper_has_no_terminal_blr"
    valid=terminal is not None and len(items)>=1
    return {
        "source_call_site":cfg.src(site),
        "original_callee_target_inside_original_MEM1_executable_candidate_range":True,
        "callee_source_first_instructions":items,
        "callee_verified_plain_stw_count":len(items),
        "callee_terminal_blr_at_instruction_index":terminal,
        "callee_non_save_instruction_or_unbounded_reason":blocked_reason,
        "callee_is_store_only_GPR_save_thunk_verified":valid,
        "r4_is_preserved_by_exact_callee_source_verified":valid,
        "callee_named_symbol_or_complete_external_callgraph_proven":False,
        "source_full_game_guest_execution_proven":False,
    }


def exact_caller_r4(read):
    report=[]
    for setup,call,rt,ra,disp in CALLER_SETUPS:
        pc=BASE+setup
        w=read(pc)
        op=(w>>26)
        got=(op,(w>>21)&31,(w>>16)&31,cfg.signed(w&0xFFFF,16))
        if got!=(14,rt,ra,disp):
            raise ValueError("Exact original caller r4 addi/li source changed")
        direct=cfg.decode_transfer(BASE+call,read(BASE+call))
        if direct["kind"]!="direct_bl_call" or direct["target"]!=cfg.ENTRY:
            raise ValueError("Original native Ball cache caller BL changed")
        blocked=[]
        for p in range(pc+4,BASE+call,4):
            word=read(p)
            dec=cfg.decode_transfer(p,word)
            if dec["kind"]!="linear_not_decoded_control":
                blocked.append("intervening_control_transfer")
            if any(dst==4 for dst,*_ in lineage.gpr_writers(word)):
                blocked.append("recognized_r4_reassignment")
            if word>>26 in (33,35,37,39,41,43,45,47):
                blocked.append("PPC_memory_update_form_unqualified")
            if word>>26==31:
                blocked.append("PPC_X_form_unqualified")
        report.append({
            "caller_BL_relative_site":cfg.src(BASE+call),
            "last_r4_setup_site":cfg.src(pc),
            "last_r4_setup_syntax":"addi r4,r4,+1" if ra==4 else "li r4,-1",
            "unrecognized_intervening_source_effects":blocked,
            "r4_literal_minus_one_at_entry_on_straight_line_if_called":
                ra==0 and not blocked,
            "caller_entry_r4_statically_fixed_proven":ra==0 and not blocked,
            "actual_game_runtime_call_executed_proven":False,
        })
    return report


def inspect(read,bank_limit):
    preceding=prior.inspect(read)
    if preceding["source_input_r4_preserved_across_prelude_BL_proven"]:
        raise ValueError("Prior source gate unexpectedly promoted r4")
    exact=thunk(read,bank_limit)
    args=exact_caller_r4(read)
    can_prove=exact["r4_is_preserved_by_exact_callee_source_verified"]
    return {
        "kind":"P0_ORIGINAL_BALL_ENTRY_SAVE_THUNK_R4_PRESERVATION_V1",
        "status":"SOURCE_QUALIFIED_ORIGINAL_CALLEE_R4_PATH_AUDIT",
        "original_prelude_linked_callee_structure":exact,
        "original_two_cache_caller_r4_exact_input_syntax":args,
        "backedge_r28_equals_function_entry_r4_via_source_verified":
            can_prove,
        "second_caller_negative_r28_on_proven_straight_line_if_executed":
            can_prove and args[1][
                "r4_literal_minus_one_at_entry_on_straight_line_if_called"],
        "first_caller_r4_sign_resolved":False,
        "byte_flag_r3_plus_0x5C_runtime_value_proven":False,
        "selected_live_ball_object_receiver_proven":False,
        "guest_backedge_dynamically_executed_proven":False,
        "wood_vs_foliage_collision_handler_verified":False,
        "native_collision_impulse_or_velocity_verified":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    old=prior.run(archive,capture)
    if not old["original_source_SHA_and_scene_gates_verified"] or old[
            "original_verified_capture"]!=capture:
        raise ValueError("Original Rev1 source SHA/scene gates failed")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for index,size in enumerate(seven.SIZE,1):
            p=seven.src._file(roots[capture],f"{capture}.{index}.raw",size)
            h=stack.enter_context(p.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(h.fileno(),0,access=mmap.ACCESS_READ)))
        limit=MEM1+len(banks[0])
        def read(pc):
            if pc%4 or pc<MEM1 or pc+4>limit:
                raise ValueError("Native source site outside original MEM1 bank")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        report=inspect(read,limit)
    seven._check_archive(archive)
    return {**report,
            "original_seven_pair_SHA_and_native_scene_qualified":True,
            "original_source_capture":capture}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=p.parse_args(argv)
    try:
        print(json.dumps(run(args.archive,args.capture),
                         sort_keys=True,separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,
            AttributeError,OverflowError,struct.error):
        print(json.dumps({"kind":"P0_ORIGINAL_BALL_ENTRY_SAVE_THUNK_R4_PRESERVATION_V1",
                          "status":"ABSTAIN_ORIGINAL_SHA_OR_SAVE_THUNK_GATES",
                          "training_approved":False}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
