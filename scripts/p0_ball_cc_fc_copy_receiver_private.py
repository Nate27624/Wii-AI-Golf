#!/usr/bin/env python3
"""Source-qualified P0 native PPC Ball +0xCC to +0xFC copy verification.

Requires the private original SHA/scene-gated Rev1 seven-capture archive.
A previous code audit established two static calls to 0x80299C70,
r27 <- entry r3, three lfs from r3 +{0,4,8} to r27+{CC,D0,D4},
and separate lfs from r27+{CC,D0,D4} to r27+{FC,100,104}.
This pass verifies exact contiguous PPC instruction windows and traces
nearest bounded source writes to r3/r31, refusing to infer this-object
ownership, dynamic execution, velocity, tree impact or material physics.

Print only original public Ball unit-relative sites, register indices,
signed field displacements and boolean dataflow gates; no original
instruction words, ROM/game bytes, private addresses or coordinates.
Read-only, offline, no Dolphin, no video and no new experiment.
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
import p0_ball_cache_r27_lineage_private as before
import audit_p0_seven_numbered_source_pairs_private as seven

BASE=before.SOURCE_BALL
MEM1=before.MEM1
MEM1=before.MEM1
ENTRY=before.FN_START
FIRST_COPY=[
    (0x2D00,0x2D04,0,0xCC),
    (0x2D08,0x2D0C,4,0xD0),
    (0x2D10,0x2D14,8,0xD4),
]
SECOND_LOADS=[
    (0x2F98,2,0xCC),
    (0x2F9C,1,0xD0),
    (0x2FA0,0,0xD4),
]
SECOND_STORES=[
    (0x2FA8,2,0xFC),
    (0x2FAC,1,0x100),
    (0x2FB0,0,0x104),
]
CALLS=before.CALLS
MOVE=0x2CB8
LAST_SOURCE_LOAD=0x2D00
MAX_CALLER_BACK=128


def decode_load(read,off,fpr,base,disp):
    q=before.dform(read(BASE+off))
    if not q or q["op"]!=48 or (q["rt"],q["ra"],q["offset"])!=(fpr,base,disp):
        raise ValueError("Qualified original lfs source register, offset or instruction changed")
    return True


def decode_store(read,off,fpr,base,disp):
    q=before.dform(read(BASE+off))
    if not q or q["op"]!=52 or (q["rt"],q["ra"],q["offset"])!=(fpr,base,disp):
        raise ValueError("Qualified original stfs register, receiver or field changed")
    return True


def check_first_copy(read):
    # This is a contiguous 6-instruction exact lfs/stfs sequence:
    # r3 +0,4,8 -> r27 +CC,D0,D4. No intervening PPC instructions.
    rows=[]
    for lo,so,src,dst in FIRST_COPY:
        decode_load(read,lo,0,3,src)
        decode_store(read,so,0,27,dst)
        if so!=lo+4:
            raise ValueError("Nonconsecutive source load and store")
        rows.append({
            "original_lfs_public_site":before.site(BASE+lo),
            "source_pointer_GPR":3,
            "source_member_displacement":f"+0x{src:03X}",
            "original_stfs_public_site":before.site(BASE+so),
            "destination_pointer_GPR":27,
            "destination_member_displacement":f"+0x{dst:03X}",
            "same_float_register":0,
        })
    if [x[0] for x in FIRST_COPY] != [0x2D00,0x2D08,0x2D10]:
        raise ValueError("Unexpected source six-instruction block")
    return {
        "exact_consecutive_native_lfs_stfs_triplet":True,
        "source_r3_triplet_to_r27_plus_0xCC_syntax":rows,
        "native_r3_points_to_ball_plus_0x30_proven":False,
        "same_selected_Ball_receiver_proven":False,
        "instruction_executed_during_observed_wood_or_leaves_proven":False,
    }


def check_second_copy(read):
    # Six lfs/stfs surrounding one unknown instruction at +0x2FA4:
    # require that it is not a control transfer, FPR clobber,
    # r27 reassignment, nor obvious store to original source cache.
    for off,fpr,disp in SECOND_LOADS:
        decode_load(read,off,fpr,27,disp)
    for off,fpr,disp in SECOND_STORES:
        decode_store(read,off,fpr,27,disp)
    pc=BASE+0x2FA4
    w=read(pc)
    if before.prior.is_control(w):
        raise ValueError("Source copy sequence control transfer")
    if any(dst==27 for dst,*_ in before.gpr_writers(w)):
        raise ValueError("Source register r27 overwritten between copy")
    # Primary FP operations and FP loads write FRT. This is a
    # conservative syntax gate; unknown X/paired-single ops abstain
    # from proving full dataflow beyond recognized instructions.
    op=w>>26
    if op in (48,49,50,51,59,63) and ((w>>21)&31) in (0,1,2):
        raise ValueError("Source f0/f1/f2 clobbered in copy window")
    q=before.dform(w)
    if q and q["op"] in (52,53):
        raise ValueError("Intervening FP memory store could overwrite source")
    # Exact native PPC integer operations that cannot alter
    # memory or FP registers; full source+destination triple
    # continuity is verified in the local straight-line window.
    # Do not promote to execution/receiver/impact proof.
    benign_integer_ops=(14,15,24,25,26,27,28,29,32,34)
    permitted=op in benign_integer_ops
    return {
        "exact_load_store_triplets_verified":True,
        "intervening_instruction_type":(
            "known_integer_nonmemory_FP_preserving" if permitted
            else "unresolved_other_op"),
        "source_fp_gpr_preservation_proven":permitted,
        "native_static_copy_of_CC_to_FC_verified":permitted,
        "dynamic_copy_executed_in_live_tree_shots_proven":False,
        "selected_active_Ball_receiver_proven":False,
    }


def intermediate_site(read):
    pc=BASE+0x2FA4
    w=read(pc)
    op=w>>26
    q=before.dform(w)
    xform=((w>>1)&1023) if op==31 else None
    # Expose only syntax, never original word/bytes.
    return {
        "public_source_site":before.site(pc),
        "primary_opcode_number":op,
        "X_form_opcode_number_if_applicable":xform,
        "FPR_destination_index_if_recognized":((w>>21)&31) if op in
            (48,49,50,51,52,53,59,63) else None,
        "source_GPR_write_candidates":[{
            "destination_register":dst,
            "syntactic_writer_class":typ,
            "source_register_if_known":src,
        } for dst,typ,src,_ in before.gpr_writers(w)],
        "D_form_syntax_if_supported":{
            "op":q["op"],"register":q["rt"],
            "base":q["ra"],"offset":q["offset"]
        } if q else None,
        "native_dataflow_from_original_source_fully_proven":False,
    }


def r3_between_entry_and_cc(read):
    begin=ENTRY+0x20
    end=BASE+LAST_SOURCE_LOAD
    if begin!=BASE+MOVE:
        raise ValueError("Original r27 binding not at expected prologue")
    mv=read(begin)
    ops=before.gpr_writers(mv)
    if (27,"mr",3,None) not in ops:
        raise ValueError("Original r27 <- r3 function-entry syntax changed")
    src_writes=[]
    branches=[]
    for pc in range(begin+4,end,4):
        w=read(pc)
        if before.prior.is_control(w):
            branches.append(before.site(pc))
        for dst,typ,src,disp in before.gpr_writers(w):
            if dst==3:
                src_writes.append({
                    "public_source_site":before.site(pc),
                    "syntactic_writer_class":typ,
                    "source_register":src,
                    "source_displacement_if_supported":disp,
                })
    return {
        "entry_source_r27_mr_r3_site":before.site(begin),
        "source_r3_writes_after_r27_binding_before_first_CC_source_load":src_writes,
        "bounded_control_transfer_sites":branches[:12],
        "bounded_control_transfer_count":len(branches),
        "source_r3_at_CC_load_is_selected_ball_pointer_proven":False,
        "source_r27_at_CC_store_is_selected_ball_pointer_proven":False,
    }


def caller_r31_recent_defs(read):
    out=[]
    for off in CALLS:
        pc=BASE+off
        call=before.inventory.units.direct_b(pc,read(pc))
        if call is None or not call[1] or call[0]!=ENTRY:
            raise ValueError("Original exact cache direct BL changed")
        # Only report bounded syntax; crossing a function boundary is
        # possible, so this does NOT prove the caller's r31 origin.
        start=max(BASE,pc-4*MAX_CALLER_BACK)
        defs=[]
        for where in range(start,pc,4):
            for dst,typ,src,disp in before.gpr_writers(read(where)):
                if dst==31:
                    defs.append({
                        "public_source_site":before.site(where),
                        "syntax":typ,"source_GPR_if_supported":src,
                        "source_displacement_if_supported":disp,
                    })
        out.append({
            "native_direct_BL_public_site":before.site(pc),
            "bounded_r31_definition_candidate_count":len(defs),
            "closest_r31_definition_candidate":defs[-1] if defs else None,
            "source_r31_definitely_same_this_pointer_through_call":False,
            "caller_function_start_verified":False,
        })
    return out


def inspect(read):
    first=check_first_copy(read)
    second=check_second_copy(read)
    return {
        "kind":"P0_ORIGINAL_BALL_CC_FC_NATIVE_COPY_AND_RECEIVER_AUDIT_V1",
        "status":"SOURCE_QUALIFIED_EXACT_PPC_STORE_COPY_AND_BOUND_RECEIVER_CANDIDATES",
        "source_first_CC_triplet_copy":first,
        "source_second_CC_to_FC_triplet_copy":second,
        "unresolved_intervening_instruction_syntax":intermediate_site(read),
        "source_r27_r3_entry_lineage":r3_between_entry_and_cc(read),
        "caller_r31_source_candidates":caller_r31_recent_defs(read),
        "selected_active_ball_receiver_identity_proven":False,
        "ball_CC_is_world_position_or_velocity_proven":False,
        "ball_FC_native_collision_response_proven":False,
        "runtime_wood_leaves_material_branch_proven":False,
        "original_tree_contact_impact_frame_verified":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    prior=before.run(archive,capture)
    if (prior.get("original_seven_pair_SHA_and_scene_qualified") is not True
            or prior.get("original_source_verified_capture")!=capture):
        raise ValueError("Original qualified Rev1 capture/source gates not met")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for n,size in enumerate(seven.SIZE,1):
            file=seven.src._file(roots[capture],f"{capture}.{n}.raw",size)
            stream=stack.enter_context(file.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ)))
        def read(pc):
            if pc%4 or pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Original native code outside SHA-qualified MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        result=inspect(read)
    seven._check_archive(archive)
    return {**result,"original_seven_pair_SHA_source_qualified":True,
            "original_source_capture":capture}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=p.parse_args(argv)
    try:
        print(json.dumps(run(args.archive,args.capture),
                         sort_keys=True,separators=(",",":"),
                         allow_nan=False))
        return 0
    except (ValueError,OSError,TypeError,KeyError,
            IndexError,OverflowError,AttributeError,struct.error):
        print(json.dumps({
            "kind":"P0_ORIGINAL_BALL_CC_FC_NATIVE_COPY_AND_RECEIVER_AUDIT_V1",
            "status":"ABSTAIN_ORIGINAL_SOURCE_OR_DATAFLOW_GATE",
            "training_approved":False}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
