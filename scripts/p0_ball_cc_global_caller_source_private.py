#!/usr/bin/env python3
"""P0 original Rev1 source-pointer producer and Ball caller receiver trail.

Reads ONLY the original seven-capture SHA-qualified private MEM1/MEM2
archive; rechecks native Golf 94 tree and Ball<->KCol source gates.
The previous original trace confirmed r27 <- incoming r3, exact
lfs/stfs r3+0/4/8 -> r27+CC/D0/D4 and r27+CC/D0/D4
-> r27+FC/100/104 (with interleaved lwz r0,108(r27)).
This source audit resolves *where the r3 source comes from* and examines
the caller's r31 <- r3 lifetime and direct native BL argument.

Important: r13-relative global slot may refer to an unrelated object.
Source register dataflow is NOT selected live Ball receiver proof,
tree material branch proof, dynamic execution or a guest-frame timeline.
No Dolphin, new shots, videos, live memory, memory writes or asset export.
Outputs only original public Ball source-unit-relative sites and register
indices/offsets; NEVER original instruction words, absolute native heap
addresses, game XYZ, private paths or ROM bytes.
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
import p0_ball_cc_fc_copy_receiver_private as copy
import p0_ball_cache_r27_lineage_private as lineage
import audit_p0_seven_numbered_source_pairs_private as seven

MEM1=0x80000000
BASE=lineage.SOURCE_BALL
ENTRY=lineage.FN_START
SOURCE_SLOT_DISP=-23304
GLOBAL_LOADS=(0x2CD4,0x2CF8)
DEREF=0x2CFC
FIRST_LFS=0x2D00
CALLERS=(
    {"bind":0x2B08,"arg":0x2B80,"bl":0x2B8C},
    {"bind":0x2C5C,"arg":0x2C70,"bl":0x2C80},
)
MAX_CONDITIONAL_SITES=16


def decode_signed(value,bits):
    if value & (1<<(bits-1)):
        value-=1<<bits
    return value


def branch(read,off):
    pc=BASE+off
    w=read(pc)
    opcode=w>>26
    if opcode not in (16,18):
        return None
    absolute=bool(w&2)
    linked=bool(w&1)
    if opcode==16:
        disp=decode_signed(w&0xFFFC,16)
        bo=(w>>21)&31
        bi=(w>>16)&31
        name="conditional_bc"
    else:
        disp=decode_signed(w&0x03FFFFFC,26)
        bo=bi=None
        name="direct_b_or_bl"
    target=disp if absolute else pc+disp
    lo,hi=lineage.inventory.SOURCE_UNITS["Ball"]
    return {
        "source_site":lineage.site(pc),
        "source_branch_kind":name,
        "destination_ball_unit_relative":(
            f"+0x{target-lo:04X}" if lo<=target<hi else None),
        "target_outside_public_Ball_unit":not(lo<=target<hi),
        "is_absolute_branch":absolute,
        "link_bit":linked,
        "conditional_BO":bo,
        "conditional_BI":bi,
        "branch_direction_or_dynamic_execution_proven":False,
    }


def is_mr(read,off,des,src):
    return (des,"mr",src,None) in lineage.gpr_writers(read(BASE+off))


def exact_source_pointer(read):
    # Source before the first +CC write is a global-pointer lookup,
    # *not* the incoming this pointer. Verify both original native sites.
    for off in GLOBAL_LOADS:
        q=lineage.dform(read(BASE+off))
        if q is None or (q["op"],q["rt"],q["ra"],q["offset"])!=(
                32,3,13,SOURCE_SLOT_DISP):
            raise ValueError("Original r13-relative r3 global-source load changed")
    q=lineage.dform(read(BASE+DEREF))
    if q is None or (q["op"],q["rt"],q["ra"],q["offset"])!=(32,3,3,0x4C):
        raise ValueError("Original global candidate +0x4C pointer dereference changed")
    q=lineage.dform(read(BASE+FIRST_LFS))
    if q is None or (q["op"],q["rt"],q["ra"],q["offset"])!=(48,0,3,0):
        raise ValueError("Original first cache float source changed")
    # Strict adjacent chain: r13-global -> +0x4C pointer -> 3 floats.
    if not (GLOBAL_LOADS[-1]+4==DEREF and DEREF+4==FIRST_LFS):
        raise ValueError("Original native source pointer chain not consecutive")
    return {
        "source_relative_global_loads":[lineage.site(BASE+x)
                                        for x in GLOBAL_LOADS],
        "global_slot_source_base_gpr":13,
        "global_slot_source_signed_displacement":SOURCE_SLOT_DISP,
        "exact_second_global_load_followed_by_member_deref_and_lfs":True,
        "source_member_pointer_load_site":lineage.site(BASE+DEREF),
        "source_member_pointer_displacement":"+0x04C",
        "float_vector_first_component_site":lineage.site(BASE+FIRST_LFS),
        "r3_from_static_global_pointer_not_incoming_receiver_at_CC_source":True,
        "global_object_is_selected_live_Ball_proven":False,
        "pointer_equals_live_selected_Ball_plus_0x30_proven":False,
        "actual_guest_cache_copy_executed_during_tree_contact_proven":False,
    }


def native_branches(read):
    seq=[]
    for off in range(0x2CB8,0x2D18,4):
        result=branch(read,off)
        if result:
            seq.append(result)
    return {
        "observed_native_control_flow_in_small_cache_prelude":seq[
            :MAX_CONDITIONAL_SITES],
        "candidate_branch_count":len(seq),
        "source_partial_CFG_reachability_proven":False,
        "execution_on_original_wood_or_foliage_contact_proven":False,
    }


def caller_receiver_lifetime(read):
    rows=[]
    for c in CALLERS:
        bind,arg,bl=c["bind"],c["arg"],c["bl"]
        if not is_mr(read,bind,31,3):
            raise ValueError("Original caller source receiver r31<-r3 changed")
        if not is_mr(read,arg,3,31):
            raise ValueError("Original caller cache argument r3<-r31 changed")
        branch_result=lineage.inventory.units.direct_b(BASE+bl,read(BASE+bl))
        if branch_result is None or not branch_result[1] or branch_result[0]!=ENTRY:
            raise ValueError("Original caller BL exact cache entry changed")
        writes_31=[]
        controls=[]
        for off in range(bind+4,bl,4):
            word=read(BASE+off)
            if lineage.prior.is_control(word):
                controls.append(lineage.site(BASE+off))
            for dst,kind,src,disp in lineage.gpr_writers(word):
                if dst==31:
                    writes_31.append({
                        "public_source_site":lineage.site(BASE+off),
                        "writer_syntax":kind,
                        "source_reg_if_known":src,
                        "source_displacement_if_supported":disp,
                    })
        writes_arg=[]
        for off in range(arg+4,bl,4):
            for dst,kind,src,disp in lineage.gpr_writers(read(BASE+off)):
                if dst==3:
                    writes_arg.append(lineage.site(BASE+off))
        rows.append({
            "original_receiver_saved_from_r3_site":lineage.site(BASE+bind),
            "original_argument_restored_r3_from_r31_site":lineage.site(BASE+arg),
            "original_exact_direct_cache_BL_site":lineage.site(BASE+bl),
            "recognized_r31_redefinitions_between_bind_and_call":writes_31,
            "recognized_r3_redefinitions_between_arg_and_call":writes_arg,
            "intervening_control_transfer_count":len(controls),
            "intervening_control_sites":controls[:MAX_CONDITIONAL_SITES],
            "recognized_register_syntax_unchanged_in_bounded_linear_source":
                not writes_31 and not writes_arg,
            "source_original_caller_entry_r3_is_selected_Ball_proven":False,
            "source_r31_preservation_all_CFG_paths_proven":False,
            "static_register_chain_is_runtime_live_Ball_execution_proven":False,
        })
    return rows


def analyze(read):
    source=exact_source_pointer(read)
    # Requires earlier exact first three-float and downstream copy gates.
    c1=copy.check_first_copy(read)
    c2=copy.check_second_copy(read)
    if not (c1["exact_consecutive_native_lfs_stfs_triplet"] and
            c2["native_static_copy_of_CC_to_FC_verified"]):
        raise ValueError("Earlier native cache copy no longer source-qualified")
    return {
        "kind":"P0_ORIGINAL_BALL_NATIVE_CACHE_SOURCE_GLOBAL_AND_CALLER_V1",
        "status":"SOURCE_QUALIFIED_GLOBAL_POINTER_AND_CALLER_REGISTER_SYNTAX",
        "source_0xCC_cache_input_pointer_chain":source,
        "source_original_caller_r31_to_entry_r3_evidence":
            caller_receiver_lifetime(read),
        "bounded_native_prelude_branches":native_branches(read),
        "source_0xCC_copy_from_pointer_target_verified":True,
        "source_0xFC_static_copy_from_0xCC_verified":True,
        "selected_live_Ball_as_cache_destination_verified":False,
        "selected_live_Ball_as_global_source_verified":False,
        "wood_vs_foliage_tree_collision_branch_verified":False,
        "native_ball_velocity_or_material_response_proven":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    prior=copy.run(archive,capture)
    if not (prior["original_seven_pair_SHA_source_qualified"] and
            prior["original_source_capture"]==capture):
        raise ValueError("Prior original source gates not verified")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for n,size in enumerate(seven.SIZE,1):
            f=seven.src._file(folders[capture],f"{capture}.{n}.raw",size)
            stream=stack.enter_context(f.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ)))
        def read(pc):
            if pc%4 or pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Original code outside SHA-qualified MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        result=analyze(read)
    seven._check_archive(archive)
    return {**result,
            "original_seven_pair_sha_and_scene_gates_passed":True,
            "original_verified_capture_number":capture}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    opts=p.parse_args(argv)
    try:
        result=run(opts.archive,opts.capture)
        print(json.dumps(result,sort_keys=True,separators=(",",":"),
                         allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,
            OverflowError,AttributeError,struct.error):
        print(json.dumps({
            "kind":"P0_ORIGINAL_BALL_NATIVE_CACHE_SOURCE_GLOBAL_AND_CALLER_V1",
            "status":"ABSTAIN_SHA_OR_ORIGINAL_PPC_SOURCE_CONSISTENCY",
            "training_approved":False}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
