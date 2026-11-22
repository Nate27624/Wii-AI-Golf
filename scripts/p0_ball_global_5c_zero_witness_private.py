#!/usr/bin/env python3
"""Source-only original Rev1 global +0x5C byte clear-path witness.

The previous source-qualified audit proves original init code can write
1 to +0x5C(r3), and shows a possible later byte update:
  Ball+0x2CC4  li r30,0
  Ball+0x2D30  lwz r26,-23304(r13)
  Ball+0x2D8C  stb r30,+0x5C(r26)
This audit checks those exact native syntax sites, decodes unknown X-form
824 (srawi: GPR destination rA) and 202 (addze: destination rD),
and constructs a conditional static may-reach source route.
It does NOT prove these instructions all execute, the flag is nonzero,
a specific Ball is selected, a tree was hit, or that the initializer
receiver equals the r13-global object.

Read-only SHA-gated original seven-pair capture. No Dolphin, video,
new game shots, native instruction words/ROM, raw memory, private
addresses/paths, XYZ, guest writes, training or fitted physics.
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
import p0_ball_global_5c_initializer_r26_private as prior
import p0_ball_cache_cfg_reachability_private as cfg
import p0_ball_cache_r27_lineage_private as lineage
import audit_p0_seven_numbered_source_pairs_private as seven

BALL=prior.BALL
MEM1=prior.MEM1
R30_CONST=BALL+0x2CC4
GLOBAL_LOAD=BALL+0x2D30
BYTE_CLEAR=BALL+0x2D8C
X_SITES=((BALL+0x2D44,824),(BALL+0x2D48,202))
MAX_ROUTE=128


def label(pc):
    return cfg.src(pc)


def xform(w,expected_xo=None):
    if w>>26!=31:
        raise ValueError("Expected PPC native X-form source opcode")
    xo=(w>>1)&1023
    if expected_xo is not None and xo!=expected_xo:
        raise ValueError("Source X-form opcode changed")
    rs=(w>>21)&31
    ra=(w>>16)&31
    rb=(w>>11)&31
    if xo==824:
        return {"mnemonic":"srawi","X_form_opcode":xo,
                "source_register":rs,"destination_register":ra,
                "shift_amount":rb,"writes_other_GPRs":False}
    if xo==202:
        return {"mnemonic":"addze","X_form_opcode":xo,
                "source_register":ra,"destination_register":rs,
                "writes_other_GPRs":False}
    raise ValueError("Unsupported native X-form in bounded gate")


def exact_source(read):
    li=read(R30_CONST)
    if (li>>26,(li>>21)&31,(li>>16)&31,
        cfg.signed(li&65535,16))!=(14,30,0,0):
        raise ValueError("Original r30 literal-zero site changed")
    ld=read(GLOBAL_LOAD)
    if (ld>>26,(ld>>21)&31,(ld>>16)&31,
        cfg.signed(ld&65535,16))!=(32,26,13,prior.source.GLOBAL_SLOT):
        raise ValueError("Original global r26 pointer load changed")
    store=read(BYTE_CLEAR)
    if (store>>26,(store>>21)&31,(store>>16)&31,
        cfg.signed(store&65535,16))!=(38,30,26,92):
        raise ValueError("Original byte writer source changed")
    x=[{"source_site":label(site),**xform(read(site),xo)}
       for site,xo in X_SITES]
    return {
        "original_r30_literal_zero_source":label(R30_CONST),
        "original_global_pointer_r26_load_source":label(GLOBAL_LOAD),
        "original_zero_byte_store_candidate_source":label(BYTE_CLEAR),
        "original_X_form_effects":x,
        "native_r30_zero_on_every_runtime_path_proven":False,
        "global_receiver_is_selected_active_ball_proven":False,
    }


def gpr_writes_qualified(w):
    """Return (recognized, set of GPR destination registers).

    This intentionally decodes only known PPC subsets; unrecognized
    instructions fail closed rather than implying r26/r30 preservation.
    """
    op=w>>26
    rt=(w>>21)&31
    ra=(w>>16)&31
    xo=(w>>1)&1023 if op==31 else None
    if op in (14,15,32,34,40,42):
        return True,{rt}
    if op in (33,35,41,43,49,51):
        if op in (49,51):  # floating-point load with base register update
            return True,{ra}
        return True,{rt,ra}
    if op==46:  # lmw
        return True,set(range(rt,32))
    if op in (20,21,23,24,25,26,27,28,29):
        return True,{ra}
    if op in (36,38,44,48,50,52,54,59,60,63,11,10,16,18,19):
        return True,set()
    if op in (37,39,45,53,55,61):
        return True,{ra}
    if op==31:
        if xo in (444,28,316,824):
            return True,{ra}
        if xo in (202,23,55,87,119,266,40,339,371):
            return True,{rt}
        if xo==467: # mtspr writes SPR, not GPR
            return True,set()
        return False,set()
    return False,set()


def witness(read):
    audit=cfg.explore(read)
    path=cfg.route(audit["parent"],BYTE_CLEAR)
    if path is None:
        return {
            "static_source_may_reach_byte_store":False,
            "all_three_source_anchors_on_one_witness":False,
            "protected_GPR26_GPR30_preservation_source_qualified":False,
            "bounded_shortest_source_witness":[],
        }
    if len(path)>MAX_ROUTE:
        raise ValueError("Original static witness exceeds bounded report")
    anchors=[R30_CONST,GLOBAL_LOAD,BYTE_CLEAR]
    on_path=all(q in path for q in anchors)
    ordered=on_path and [path.index(q) for q in anchors]==sorted(
        path.index(q) for q in anchors)
    branches=[]
    for i,pc in enumerate(path[:-1]):
        t=cfg.decode_transfer(pc,read(pc))
        if t["kind"]=="conditional_bc":
            nxt=path[i+1]
            branches.append({
                "source_site":label(pc),
                "source_choice":"taken" if nxt==t["target"] else "fallthrough",
                "condition_satisfied_in_actual_guest_proven":False})
    violations=[]
    if ordered:
        for i,pc in enumerate(path):
            if pc in (R30_CONST,GLOBAL_LOAD,BYTE_CLEAR):
                continue
            if pc<GLOBAL_LOAD and pc<R30_CONST:
                continue
            protected=set()
            if i>path.index(R30_CONST):
                protected.add(30)
            if i>path.index(GLOBAL_LOAD):
                protected.add(26)
            if not protected:
                continue
            ok,defs=gpr_writes_qualified(read(pc))
            if not ok or defs.intersection(protected):
                violations.append({
                    "source_site":label(pc),
                    "instruction_source_semantics_qualified":ok,
                    "protected_register_write":bool(defs.intersection(protected))})
    return {
        "static_source_may_reach_byte_store":True,
        "source_shortest_witness_instruction_count":len(path),
        "all_three_source_anchors_on_one_witness":bool(ordered),
        "source_conditional_branch_choices":branches,
        "protected_r26_r30_source_effect_uncertainties_or_clobbers":violations,
        "protected_GPR26_GPR30_preservation_source_qualified":
            bool(ordered and not violations),
        "direct_calls_after_r30_assignment_rely_on_PPC_nonvolatile_ABI":
            [label(pc) for pc in path[path.index(R30_CONST)+1:]
             if cfg.decode_transfer(pc,read(pc))["kind"]=="direct_bl_call"]
            if ordered else [],
        "conditional_branch_register_values_observed":False,
        "native_guest_byte_write_executed_proven":False,
        "native_byte_value_is_zero_if_witness_executes_without_clobber":
            bool(ordered and not violations),
        "receiver_is_same_global_slot_value_if_witness_executes_without_clobber":
            bool(ordered and not violations),
        "witness_is_complete_actual_cfg_proven":False,
    }


def inspect(read):
    exact=exact_source(read)
    trace=witness(read)
    return {
        "kind":"P0_ORIGINAL_BALL_GLOBAL_5C_ZERO_WRITE_WITNESS_V1",
        "status":"ORIGINAL_SHA_QUALIFIED_GLOBAL_BYTE_CLEAR_PATH_CONTEXT",
        "native_zero_and_pointer_source_sites":exact,
        "bounded_original_native_source_witness":trace,
        "previous_initialization_written_one_to_same_global_receiver_proven":False,
        "selected_live_ball_identity_proven":False,
        "global_flag_at_guest_collision_time_known":False,
        "native_tree_contact_wood_vs_foliage_material_verified":False,
        "native_ball_velocity_impulse_or_restitution_verified":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    old=prior.run(archive,capture)
    if (old.get("original_SHA_7pair_archive_and_scene_gates_verified") is not True
            or old.get("original_capture")!=capture):
        raise ValueError("Prior original Rev1 SHA/scene gates failed")
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
                raise ValueError("Original native source read outside qualified MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        report=inspect(read)
    seven._check_archive(archive)
    return {**report,"original_SHA_archive_scene_and_native_source_verified":True,
            "original_capture":capture}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",required=True,type=Path)
    parser.add_argument("--capture",type=int,choices=range(1,8),default=7)
    a=parser.parse_args(argv)
    try:
        print(json.dumps(run(a.archive,a.capture),
                         sort_keys=True,separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,
            OverflowError,AttributeError,struct.error) as exc:
        print(json.dumps({
            "kind":"P0_ORIGINAL_BALL_GLOBAL_5C_ZERO_WRITE_WITNESS_V1",
            "status":"ABSTAIN_ORIGINAL_SOURCE_OR_SHA_GATE",
            "failure_exception_class":type(exc).__name__,
            "exception_message_or_private_data_exposed":False,
            "training_approved":False},sort_keys=True))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
