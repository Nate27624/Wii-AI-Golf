#!/usr/bin/env python3
"""P0 original Rev1 source-only r13 global +0x5C flag writer census.

Original native Ball+0x2FB8/BC loads an object pointer from
-23304(r13), then its byte +0x5C. The signed r28<0 branch input is
now source-qualified for the second caller if its straight-line call
path runs, but the +0x5C byte's *writer* and object identity remain
unknown. This script searches public Golf source-unit code for exact
r13 slot stores, +0x5C byte stores, and bounded possible producer
sequences. A D-form displacement match is NOT proof of object
identity, wood/leaf material, impact or dynamic use.

Original archive: seven-pair SHA/scene/native source-gated through
p0_ball_prelude_callee_census_private.run. No live emulator, video,
new swing, guest RAM write or fitting. Output contains only public
unit-relative source sites, opcode/register/offset categories and
bounded counts. NEVER PPC instruction words, ROM bytes, heap pointers,
XYZ, game assets or private archive paths.
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
import p0_ball_prelude_callee_census_private as before
import p0_tree_ball_source_store_inventory_private as inventory
import p0_tree_hitbox_source_callgraph_private as native
import audit_p0_seven_numbered_source_pairs_private as seven

MEM1=0x80000000
BALL=inventory.SOURCE_UNITS["Ball"][0]
GLOBAL_SLOT=-23304
BYTE_FIELD=0x5C
EXACT_PTR_LOAD=BALL+0x2FB8
EXACT_FLAG_READ=BALL+0x2FBC
UNITS={
    **inventory.SOURCE_UNITS,
    "Tree":native.UNITS["Tree"],
    "FieldManager":native.UNITS["FieldManager"],
    "GolfKCol":native.UNITS["GolfKCol"],
}
WINDOW=24
PER_UNIT_MAX=20
KINDS={32:"lwz",34:"lbz",36:"stw",38:"stb",39:"stbu",
       40:"lhz",44:"sth",45:"sthu",48:"lfs",52:"stfs",
       54:"stfd",60:"psq_st"}


def form(w):
    op=w>>26
    if op not in KINDS:
        return None
    return {"op":op,"mnemonic":KINDS[op],
            "rT":(w>>21)&31,
            "rA":(w>>16)&31,
            "disp":((w&0xffff)^0x8000)-0x8000}


def site(pc,name):
    lo,hi=UNITS[name]
    if not (lo<=pc<hi and pc%4==0):
        raise ValueError("Source site outside declared Golf unit")
    return f"{name}+0x{pc-lo:04X}"


def exact_flag_gate(read):
    a=form(read(EXACT_PTR_LOAD))
    b=form(read(EXACT_FLAG_READ))
    if not a or not b or (
        a["op"],a["rT"],a["rA"],a["disp"])!=(32,3,13,GLOBAL_SLOT):
        raise ValueError("Source global-slot load changed")
    if (b["op"],b["rT"],b["rA"],b["disp"])!=(34,0,3,BYTE_FIELD):
        raise ValueError("Source global-object byte read changed")
    return {
        "original_global_pointer_load_site":site(EXACT_PTR_LOAD,"Ball"),
        "original_flag_byte_read_site":site(EXACT_FLAG_READ,"Ball"),
        "original_small_data_base_GPR":13,
        "global_slot_signed_displacement":GLOBAL_SLOT,
        "object_byte_field_displacement":BYTE_FIELD,
        "original_native_pointer_and_byte_loads_consecutive":True,
        "global_object_is_selected_Ball_proven":False,
        "byte_is_tree_collision_material_proven":False,
    }


def bounded_global_producer(read,unit,at,base):
    lo,_=UNITS[unit]
    uncertain=False
    for step in range(1,WINDOW+1):
        pc=at-4*step
        if pc<lo: break
        w=read(pc)
        op=w>>26
        if op in (16,17,18) or (op==19 and ((w>>1)&1023) in (16,528)):
            return {"status":"stop_prior_control_transfer",
                    "stop_site":site(pc,unit),
                    "same_global_object_proven":False}
        defs=before.old.lineage.gpr_writers(w)
        if op==31 and ((w>>1)&1023) not in (444,339,371,28,316,23,55,87,119,266,40):
            uncertain=True
        if op in (20,21,23,30,33,35,37,39,41,43,45,46,47):
            uncertain=True
        if any(dst==base for dst,*_ in defs):
            d=form(w)
            hit=(d is not None and
                 (d["op"],d["rT"],d["rA"],d["disp"])==
                 (32,base,13,GLOBAL_SLOT))
            if hit:
                return {
                    "status":"bounded_global_slot_load_with_unknown_writer_risk"
                        if uncertain else "bounded_direct_global_slot_load",
                    "global_source_site":site(pc,unit),
                    "instructions_prior_to_byte_access":step,
                    "known_no_intervening_GPR_base_writes":True,
                    "unknown_intervening_GPR_writer_semantics_exhausted":not uncertain,
                    "same_global_object_proven":False,
                    "runtime_executed_on_tree_impact_proven":False,
                }
            return {"status":"stop_other_GPR_base_definition",
                    "stop_site":site(pc,unit),
                    "same_global_object_proven":False}
    return {"status":"no_bounded_global_source",
            "same_global_object_proven":False}


def census(read,progress=None):
    results={}
    global_store_sites=[]
    for name,(lo,hi) in UNITS.items():
        if progress is not None:
            progress["stage"]="native_unit_"+name
        counts=Counter()
        accesses=[]
        global_reads=[]
        global_stores=[]
        for pc in range(lo,hi,4):
            x=form(read(pc))
            if not x:
                continue
            if x["rA"]==13 and x["disp"]==GLOBAL_SLOT:
                if x["op"]==32:
                    global_reads.append(site(pc,name))
                elif x["op"] in (36,38,39,44,45):
                    global_stores.append({
                        "source_site":site(pc,name),
                        "source_operation":x["mnemonic"],
                        "source_register":x["rT"]})
            if x["disp"]!=BYTE_FIELD:
                continue
            counts[x["mnemonic"]]+=1
            if len(accesses)<PER_UNIT_MAX:
                row={
                    "source_site":site(pc,name),
                    "opcode_category":x["mnemonic"],
                    "base_register":x["rA"],
                    "value_or_destination_register":x["rT"],
                    "possible_global_base_ancestry":
                        bounded_global_producer(read,name,pc,x["rA"]),
                    "object_receiver_identity_verified":False,
                    "native_tree_impact_execution_verified":False,
                }
                accesses.append(row)
        results[name]={
            "source_numeric_0x5C_D_form_access_counts":dict(counts),
            "bounded_access_sites":accesses,
            "additional_accesses_not_displayed":
                max(0,sum(counts.values())-len(accesses)),
            "original_r13_slot_lwz_count":len(global_reads),
            "bounded_original_r13_slot_lwz_sites":global_reads[:PER_UNIT_MAX],
            "original_r13_slot_store_count":len(global_stores),
            "bounded_original_r13_slot_store_sites":global_stores[:PER_UNIT_MAX],
            "object_instance_or_byte_semantics_verified":False,
        }
        global_store_sites.extend(global_stores)
    return {
        "source_units_examined":list(UNITS),
        "per_source_unit":results,
        "total_direct_global_slot_writer_sites":len(global_store_sites),
        "all_game_modules_scanned":False,
        "global_slot_has_no_other_writer_proven":False,
        "byte_plus_0x5C_is_selected_Ball_or_tree_material_proven":False,
    }


def inspect(read,progress=None):
    if progress is not None:
        progress["stage"]="original_exact_flag_gate"
    exact=exact_flag_gate(read)
    if progress is not None:
        progress["stage"]="native_source_unit_census"
    scan=census(read,progress)
    return {
        "kind":"P0_ORIGINAL_BALL_GLOBAL_5C_NATIVE_SOURCE_WRITER_CENSUS_V1",
        "status":"SOURCE_QUALIFIED_GLOBAL_POINTER_BYTE_FIELD_CANDIDATES",
        "original_qualified_byte_branch_input":exact,
        "bounded_global_and_byte_field_source_census":scan,
        "backedge_second_caller_negative_operand_verified_if_executed":True,
        "byte_field_runtime_nonzero_verified":False,
        "global_owner_selected_live_Ball_verified":False,
        "native_tree_collision_contact_branch_verified":False,
        "wood_vs_foliage_material_split_verified":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int,progress=None):
    if progress is not None:
        progress["stage"]="prior_native_source_qualification"
    p=before.run(archive,capture)
    if (not p.get("original_seven_pair_SHA_and_source_verified") or
            p.get("original_source_capture")!=capture or
            p.get("original_entry_r4_to_r28_straightline_source_verified") is not True):
        raise ValueError("Original negative-argument and scene SHA gates not met")
    if progress is not None:
        progress["stage"]="private_archive_SHA_verification"
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            f=seven.src._file(roots[capture],f"{capture}.{i}.raw",size)
            h=stack.enter_context(f.open("rb"))
            banks.append(stack.enter_context(mmap.mmap(h.fileno(),0,access=mmap.ACCESS_READ)))
        def read(pc):
            if pc%4 or pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Original PPC source outside SHA-qualified MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        result=inspect(read,progress)
    if progress is not None:
        progress["stage"]="final_private_archive_SHA_verification"
    seven._check_archive(archive)
    return {**result,"original_archive_and_native_scene_SHA_verified":True,
            "original_capture":capture}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    a=p.parse_args(argv)
    progress={"stage":"initial"}
    try:
        print(json.dumps(run(a.archive,a.capture,progress),sort_keys=True,
                         separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,KeyError,TypeError,IndexError,
            AttributeError,OverflowError,struct.error) as exc:
        # Source data, paths, native PCs, binary bytes and exception
        # messages MUST NOT be included in an error report.
        print(json.dumps({
            "kind":"P0_ORIGINAL_BALL_GLOBAL_5C_NATIVE_SOURCE_WRITER_CENSUS_V1",
            "status":"ABSTAIN_ORIGINAL_SHA_SOURCE_OR_ARGUMENT_GATE",
            "failed_public_stage":progress["stage"],
            "failure_exception_class":type(exc).__name__,
            "exception_message_or_private_data_exposed":False,
            "training_approved":False},sort_keys=True))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
