#!/usr/bin/env python3
"""Original Rev1 -23300/-23304 small-data global pointer divergence audit.

The three native direct initializer calls target Ball+0x3108.
Operator SHA-qualified source report found:
 +2B60 passed r3 loaded by +2B50 from -23300(r13),
 NOT the -23304(r13) global whose +0x5C byte may clear;
 +320C and +3248 follow wrapper entry prologues and forward r3.
This audits D-form source references/writers of BOTH distinct slots
within the previously source-qualified seven public Golf code units,
and checks exact wrapper entry r3 preservation to their BL instructions.
This is source-only; two adjacent r13 slots may contain equal pointers,
which has not been established or refuted.

No original PPC executable words, native absolute target addresses,
private memory pointers, world XYZ, paths, guest writes, gameplay,
Dolphin or video. No material/impact/physics training.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import p0_ball_global_5c_init_three_caller_r3_private as before
import p0_ball_global_5c_zero_witness_private as ppc
import p0_ball_global_5c_source_census_private as source
import p0_ball_cache_cfg_reachability_private as cfg
import audit_p0_seven_numbered_source_pairs_private as seven

MEM1=before.MEM1
BALL=before.BALL
SLOTS=(-23300,-23304)
WRAPPERS={
    "initializer_caller_wrapper_A":(0x31F8,0x320C,0x3208,31),
    "initializer_caller_wrapper_B":(0x322C,0x3248,0x3244,30),
}
MAX_SITES=32
ALLOWED_NON_GPR_DEFS={36,38,44,48,50,52,54,59,60,63}


def unit_site(unit,pc):
    lo,hi=source.UNITS[unit]
    if pc%4 or not lo<=pc<hi:
        raise ValueError("Original native site outside public Golf source code unit")
    return f"{unit}+0x{pc-lo:04X}"


def two_slot_census(read):
    records={}
    for slot in SLOTS:
        per_unit={}
        total=Counter()
        for unit,(lo,hi) in source.UNITS.items():
            rows=[]
            counts=Counter()
            for pc in range(lo,hi,4):
                w=read(pc)
                d=source.form(w)
                if not d or d["rA"]!=13 or d["disp"]!=slot:
                    continue
                k="source_load" if d["op"] in (32,34,40,48) else (
                  "source_store" if d["op"] in (36,38,44,52,54,60) else
                  "other_D_form")
                counts[k]+=1
                total[k]+=1
                if len(rows)<MAX_SITES:
                    rows.append({
                        "source_site":unit_site(unit,pc),
                        "PPC_opcode_category":d["mnemonic"],
                        "operation_category":k,
                        "register_T":d["rT"],
                        "same_runtime_pointer_value_across_adjacent_slots_proven":False,
                    })
            per_unit[unit]={
                "total_counts":dict(counts),
                "bounded_exact_slot_accesses":rows,
                "unshown_accesses":max(0,sum(counts.values())-len(rows)),
            }
        records[str(slot)]={
            "original_slot_signed_offset":slot,
            "source_unit_accesses":per_unit,
            "all_scanned_source_unit_access_counts":dict(total),
            "complete_whole_game_writer_inventory_proven":False,
            "other_slot_alias_proven":False,
        }
    return records


def exact_wrapper_source(read):
    old=before.direct_calls(read)
    if old["original_exact_direct_initializer_BL_sites"]!=[
            "Ball+0x2B60","Ball+0x320C","Ball+0x3248"]:
        raise ValueError("Original initializer caller list changed")
    entry=source.form(read(BALL+0x2B50))
    if not entry or (entry["op"],entry["rT"],entry["rA"],entry["disp"])!=(
            32,3,13,-23300):
        raise ValueError("First initializer r3 source no longer from -23300 slot")
    return {
        "first_initializer_caller_source":"Ball+0x2B60",
        "first_initializer_caller_r3_direct_load_site":"Ball+0x2B50",
        "first_initializer_caller_global_slot":-23300,
        "first_caller_reads_exact_minus23304_slot":False,
        "global_minus23300_equals_minus23304_value_proven":False,
    }


def wrappers(read):
    output={}
    for name,(begin_off,call_off,mr_off,saved) in WRAPPERS.items():
        begin=BALL+begin_off
        end=BALL+call_off
        call=cfg.decode_transfer(end,read(end))
        if (call["kind"],call["target"])!=(
                "direct_bl_call",before.TARGET):
            raise ValueError("Original wrapper initializer BL changed")
        w=read(BALL+mr_off)
        if (w>>26,(w>>1)&1023,(w>>21)&31,
            (w>>16)&31,(w>>11)&31)!=(31,444,3,saved,3):
            raise ValueError("Original wrapper saves input r3 in nonvolatile GPR changed")
        src=[]
        unknown=[]
        interfering=[]
        transfers=[]
        for pc in range(begin,end,4):
            word=read(pc)
            op=word>>26
            t=cfg.decode_transfer(pc,word)
            if t["kind"]!="linear_not_decoded_control":
                transfers.append({"source_site":f"Ball+0x{pc-BALL:04X}",
                                  "transfer_kind":t["kind"]})
            qualified,defs=ppc.gpr_writes_qualified(word)
            if not qualified:
                unknown.append({
                    "source_site":f"Ball+0x{pc-BALL:04X}",
                    "primary_opcode":op,
                    "X_form_opcode":((word>>1)&1023) if op==31 else None})
            if qualified and 3 in defs:
                interfering.append({"source_site":f"Ball+0x{pc-BALL:04X}",
                                    "source_primary_opcode":op})
            src.append({"relative_instruction_index":(pc-begin)//4,
                        "source_primary_opcode":op,
                        "recognized_destination_r3_write":qualified and 3 in defs,
                        "source_qualified_GPR_destination_effect":qualified})
        output[name]={
            "entry_source_site":f"Ball+0x{begin_off:04X}",
            "initializer_BL_site":f"Ball+0x{call_off:04X}",
            "entry_GPR3_copy_to_nonvolatile_saved_register_site":
                f"Ball+0x{mr_off:04X}",
            "saved_nonvolatile_register":saved,
            "source_intervening_r3_writer_sites":interfering,
            "source_unclassified_register_effects":unknown,
            "source_intervening_control_transfers":transfers,
            "bounded_prelude_source_instruction_categories":src,
            "entry_r3_preserved_through_initializer_call_source_verified":
                not unknown and not interfering and not transfers,
            "entry_r3_is_minus23304_global_object_proven":False,
            "whole_program_wrapper_entry_ancestry_proven":False,
        }
    return output


def inspect(read):
    first=exact_wrapper_source(read)
    return {
        "kind":"P0_ORIGINAL_BALL_TWO_GLOBAL_SLOTS_INITIALIZER_RECEIVERS_V1",
        "status":"SOURCE_QUALIFIED_TWO_ADJACENT_GLOBAL_SLOTS_AND_WRAPPERS",
        "original_first_initializer_caller_slot":first,
        "source_two_slot_D_form_census":two_slot_census(read),
        "source_two_initializer_wrapper_preludes":wrappers(read),
        "minus23300_and_minus23304_same_pointer_value_proven":False,
        "initializer_one_then_global_clear_zero_same_receiver_proven":False,
        "selected_live_Ball_object_identity_proven":False,
        "original_native_wood_vs_foliage_material_response_proven":False,
        "native_guest_runtime_execution_or_restitution_proven":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    old=before.run(archive,capture)
    if not(old.get("original_archive_and_scene_SHA_gates_verified")
           and old.get("original_capture")==capture):
        raise ValueError("Prior original SHA/native source gates failed")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            path=seven.src._file(roots[capture],f"{capture}.{i}.raw",size)
            h=stack.enter_context(path.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(h.fileno(),0,access=mmap.ACCESS_READ)))
        def read(pc):
            if pc%4 or pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Source outside original SHA-qualified MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        report=inspect(read)
    seven._check_archive(archive)
    return {**report,"original_SHA_scene_and_source_verification_passed":True,
            "original_capture":capture}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    a=p.parse_args(argv)
    try:
        print(json.dumps(run(a.archive,a.capture),sort_keys=True,
                         separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,
            AttributeError,OverflowError,struct.error) as exc:
        print(json.dumps({
            "kind":"P0_ORIGINAL_BALL_TWO_GLOBAL_SLOTS_INITIALIZER_RECEIVERS_V1",
            "status":"ABSTAIN_ORIGINAL_SHA_OR_NATIVE_SOURCE",
            "failure_exception_class":type(exc).__name__,
            "private_exception_message_or_native_bytes_exposed":False,
            "training_approved":False},sort_keys=True))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
