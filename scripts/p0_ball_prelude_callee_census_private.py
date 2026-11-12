#!/usr/bin/env python3
"""Source-qualified native prelude callee census, including PPC stmw save form.

The first source audit at original Rev1 capture 7 ruled OUT only a
strict stw-only save helper at the native target of Ball+0x2CB0. It did
NOT prove an r4 clobber. A conventional PowerPC compiler save helper
could instead begin with stmw, stwu, or an X-form operation.

Read exact target from SHA-qualified original seven-pair Rev1 source
archive. Report bounded *instruction categories* and GPR destination
syntax, without PPC words or native absolute addresses. Establish
r4 preservation ONLY on a complete, straight-line, store-only
stw/stmw/ordinary nop + unconditional blr path; all other patterns
explicitly abstain. Cross-check original two caller r4 setups and
original source/94-tree/KCol gates via predecessor script.

This is static source code evidence, NOT executed tree contact,
active selected Ball object, guest-frame physics or wood/foliage branch.
No Dolphin/video/new shots/live RAM/guest writes/training. No game
ROM bytes, raw code words, source asset data or heap addresses exported.
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
import p0_ball_prelude_save_thunk_private as old
import audit_p0_seven_numbered_source_pairs_private as seven

MEM1=old.MEM1
MAX_SITE_CENSUS=24
MAX_PROOF_PATH=24
NONEXEC_MIN=old.MIN_EXEC_SOURCE_ADDR


def syntax(w):
    """One bounded PPC instruction *category*, NOT a full disassembler."""
    op=w>>26
    rt=(w>>21)&31
    ra=(w>>16)&31
    disp=((w&0xFFFF)^0x8000)-0x8000
    if old.is_blr(w):
        return {"kind":"blr","proven_r4_unchanged":True,
                "terminal_unconditional_return":True}
    if op==36:
        return {"kind":"stw","stored_register":rt,"base_register":ra,
                "signed_displacement":disp,
                "proven_r4_unchanged":True}
    if op==47:
        return {"kind":"stmw","first_stored_register":rt,
                "last_stored_register":31,"base_register":ra,
                "signed_displacement":disp,
                "proven_r4_unchanged":True}
    if w==0x60000000:
        return {"kind":"nop","proven_r4_unchanged":True}
    if op==37:
        return {"kind":"stwu","stored_register":rt,"updated_base_register":ra,
                "signed_displacement":disp,
                "proven_r4_unchanged":ra!=4}
    if op==14:
        return {"kind":"addi","destination_register":rt,
                "source_register":ra,"signed_immediate":disp,
                "proven_r4_unchanged":rt!=4}
    if op in (16,18,19):
        return {"kind":"control_transfer_or_indirect","primary_opcode":op,
                "branch_kind":"conditional" if op==16 else
                              "direct" if op==18 else "XL_unknown",
                "proven_r4_unchanged":False}
    if op==31:
        xo=(w>>1)&1023
        if xo==339:
            # mfspr writes the instruction's rD, not necessarily r4.
            return {"kind":"mfspr","destination_register":rt,
                    "proven_r4_unchanged":rt!=4}
        if xo==467:
            # mtspr writes SPR, not source GPR. Conservatively still
            # exclude helper proof because LR/CTR etc can change.
            return {"kind":"mtspr","source_register":rt,
                    "proven_r4_unchanged":True}
        return {"kind":"X_form_other","X_form_opcode":xo,
                "proven_r4_unchanged":False}
    return {"kind":"unclassified","primary_opcode":op,
            "proven_r4_unchanged":False}


def classify_original_target(read,bank_limit):
    initial=old.thunk(read,bank_limit)
    desc=old.cfg.decode_transfer(old.PRELUDE,read(old.PRELUDE))
    if desc["kind"]!="direct_bl_call":
        raise ValueError("Original source BL missing")
    target=desc["target"]
    if not NONEXEC_MIN<=target<bank_limit-MAX_SITE_CENSUS*4 or target%4:
        return {
            "target_in_original_source_MEM1_bounded_window":False,
            "exact_original_r26_through_r31_six_store_then_blr_shape_verified":False,
            "original_previous_plain_stw_only_helper_verified":
                initial["r4_is_preserved_by_exact_callee_source_verified"],
            "bounded_native_callee_instruction_categories":[],
            "exact_register_r4_preservation_proven":False,
            "recognized_complete_store_only_helper_proven":False,
            "unclassified_or_control_paths_exhausted":False,
        }
    decoded=[syntax(read(target+4*i)) for i in range(MAX_SITE_CENSUS)]
    witness=[]
    return_index=None
    all_store_only=True
    for i,ins in enumerate(decoded[:MAX_PROOF_PATH]):
        witness.append({"callee_entry_instruction_index":i,**ins})
        if ins["kind"]=="blr":
            return_index=i
            break
        if ins["kind"]=="nop":
            continue
        # The actual Rev1 source target saves r26 through r31, not
        # r27 through r31. Stores of nonvolatile r26 are also safe.
        if ins["kind"]=="stw" and ins["stored_register"] in range(26,32):
            continue
        if ins["kind"]=="stmw" and ins["first_stored_register"]>=26:
            continue
        all_store_only=False
        break
    verified=(return_index is not None and return_index>0 and all_store_only)
    # Stronger positive control for the exact six instruction stores
    # in original operator report; excludes unrelated save thunks.
    original_six_store_shape=(
        return_index==6
        and all(
            decoded[i]["kind"]=="stw"
            and decoded[i]["stored_register"]==26+i
            and decoded[i]["base_register"]==11
            and decoded[i]["signed_displacement"]==-24+4*i
            for i in range(6))
    )
    return {
        "target_in_original_source_MEM1_bounded_window":True,
        "original_previous_plain_stw_only_helper_verified":
            initial["r4_is_preserved_by_exact_callee_source_verified"],
        "bounded_native_callee_instruction_categories":[
            {"callee_entry_instruction_index":i,**ins}
            for i,ins in enumerate(decoded)],
        "recognized_store_only_path_prefix":witness,
        "store_only_complete_ordinary_blr_index":return_index,
        "exact_original_r26_through_r31_six_store_then_blr_shape_verified":
            original_six_store_shape,
        "exact_register_r4_preservation_proven":verified,
        "recognized_complete_store_only_helper_proven":verified,
        "unclassified_or_control_paths_exhausted":False,
        "native_guest_call_executed_in_tree_shots_proven":False,
    }


def postcall_r4_register_gate(read):
    """Check exact 2-instruction local interval after BL and before r28<-r4.

    The previous audit found *no recognized* r4 assignments there, but
    that is insufficient if an unrecognized PPC instruction changes r4.
    Allow only known non-control, non-update opcodes and recognized X-form
    register operations with a GPR destination other than r4.
    """
    records=[]
    safe=True
    for pc in range(old.PRELUDE+4,old.BASE+old.prior.R28_BIND,4):
        word=read(pc)
        op=word>>26
        control=old.cfg.decode_transfer(pc,word)["kind"]!="linear_not_decoded_control"
        xo=(word>>1)&1023 if op==31 else None
        recognized=(op in (14,15,24,25,26,27,28,29,32,34,36,48,52)
                    or (op==31 and xo in (444,339))
                    or word==0x60000000)
        writes_r4=any(
            dst==4 for dst,*_ in old.lineage.gpr_writers(word))
        ok=recognized and not control and not writes_r4
        records.append({
            "callee_return_relative_instruction_index":
                (pc-(old.PRELUDE+4))//4,
            "source_noncontrol_opcode_qualified":recognized and not control,
            "known_destination_r4_write":writes_r4,
            "r4_preserved_by_this_instruction_source_gate":ok,
        })
        safe &= ok
    if len(records)!=2:
        raise ValueError("Unexpected native return-to-r28-bind gap")
    return {
        "bounded_intervening_register_gate_sites":records,
        "r4_preserved_between_return_and_r28_binding_source_verified":bool(safe),
        "whole_game_runtime_path_or_external_entry_proven":False,
    }


def inspect(read,bank_limit):
    earlier=old.inspect(read,bank_limit)
    callee=classify_original_target(read,bank_limit)
    # Preserve original result: a failed strict stw-only pattern is
    # NOT proof that the original callee writes r4.
    result=bool(callee["exact_register_r4_preservation_proven"])
    postcall=postcall_r4_register_gate(read)
    args=earlier["original_two_cache_caller_r4_exact_input_syntax"]
    return {
        "kind":"P0_ORIGINAL_BALL_PRELUDE_CALLEE_INSTRUCTION_CENSUS_V2",
        "status":"ORIGINAL_SHA_QUALIFIED_NATIVE_CALLEE_SOURCE_SYNTAX",
        "previous_stw_only_helper_result_was_not_r4_clobber_proof":True,
        "callee_first_24_source_instruction_syntax":callee,
        "exact_callee_preserves_r4_if_stw_stmw_only_plus_blr":result,
        "source_postcall_to_r28_r4_register_preservation":postcall,
        "original_callee_and_following_instructions_preserve_r4_verified":
            result and postcall[
                "r4_preserved_between_return_and_r28_binding_source_verified"],
        "native_original_r26_r31_save_thunk_source_verified":
            callee.get("exact_original_r26_through_r31_six_store_then_blr_shape_verified",False),
        "second_caller_minus_one_can_feed_r28_if_executed_and_path_reached":
            result and postcall[
                "r4_preserved_between_return_and_r28_binding_source_verified"]
            and args[1]["caller_entry_r4_statically_fixed_proven"],
        "original_r13_global_flag_object_identity_proven":False,
        "selected_active_Ball_cache_receiver_proven":False,
        "actual_native_collision_branch_proven":False,
        "wood_vs_foliage_material_implementation_verified":False,
        "guest_ball_velocity_or_impulse_proven":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    prev=old.run(archive,capture)
    if not (prev["original_seven_pair_SHA_and_native_scene_qualified"] and
            prev["original_source_capture"]==capture):
        raise ValueError("Previous source gate failed")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            path=seven.src._file(roots[capture],f"{capture}.{i}.raw",size)
            f=stack.enter_context(path.open("rb"))
            banks.append(stack.enter_context(mmap.mmap(
                f.fileno(),0,access=mmap.ACCESS_READ)))
        limit=MEM1+len(banks[0])
        def read(pc):
            if pc%4 or pc<MEM1 or pc+4>limit:
                raise ValueError("Native word outside original qualified MEM1 bank")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        report=inspect(read,limit)
    seven._check_archive(archive)
    return {**report,"original_seven_pair_SHA_and_source_verified":True,
            "original_source_capture":capture}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=p.parse_args(argv)
    try:
        print(json.dumps(run(args.archive,args.capture),
                         sort_keys=True,separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,
            OverflowError,AttributeError,struct.error):
        print(json.dumps({"kind":"P0_ORIGINAL_BALL_PRELUDE_CALLEE_INSTRUCTION_CENSUS_V2",
                          "status":"ABSTAIN_ORIGINAL_SHA_OR_NATIVE_SOURCE",
                          "training_approved":False}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
