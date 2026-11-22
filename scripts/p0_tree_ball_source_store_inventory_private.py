#!/usr/bin/env python3
"""Source-qualified original Rev1 PPC Ball candidate writer inventory.

Use the ORIGINAL seven-pair SHA-verified private MEM1/MEM2 archive.
Inspect only bounded published Golf units (Ball, Player, PlayerManager,
Simulation), and original native store/load instructions that MAY
reference Ball +0x30/+0xCC/+0xF0/+0xFC/+0xAC.

A D-form store displacement is NOT an object-relative field without
receiver provenance. A syntactic 'lwz rN,0x4C(rX)' followed by
'stfs ...,0/4/8(rN)' is NOT known to be Ball+0x30 without dataflow
proving that rX is the selected Ball object. Conservative register
clobber/control-transfer stops prevent long-distance speculative alias.

The completed original live 110 packets prove Ball+0x4C selfref +0x30
in that live dataset (separate offline study); THIS code inventory does
not prove these instructions actually executed at the wood/leaf event.

Read-only. Emits only *public source-unit-relative* instruction sites
and bounded syntax counts; no raw PPC instruction words, runtime RAM
pointers, game coordinates, ROM bytes, private paths or file hashes.
Never reads Dolphin, writes game memory, submits training labels.
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
import audit_p0_seven_numbered_source_pairs_private as seven
import p0_tree_hitbox_source_callgraph_private as units
import p0_ball_kcol_twelve_calls_private as kcol
import p0_tree_flag_receiver_disambiguation_private as flags

MEM1=0x80000000
SOURCE_UNITS={
    "Ball":units.UNITS["Ball"],
    "Simulation":units.UNITS["Simulation"],
    "Player":(0x8029E62C,0x802A2210),
    "PlayerManager":(0x802A2210,0x802A3560),
}
FOCUS={
    "Ball_fn_80299C70_cache_update_candidate":(0x80299C70,0x8029A038),
    "Player_fn_802A0320_translation_writer_candidate":(0x802A0320,0x802A0674),
}
FIELD_OFFSETS={
    "Ball_plus_0x30_triplet":(0x30,0x34,0x38),
    "Ball_plus_0xAC_unverified":(0xAC,0xB0,0xB4),
    "Ball_plus_0xCC_candidate_cache":(0xCC,0xD0,0xD4),
    "Ball_plus_0xF0_candidate_cache":(0xF0,0xF4,0xF8),
    "Ball_plus_0xFC_candidate_cache":(0xFC,0x100,0x104),
}
TARGET_OFFSETS=frozenset(o for group in FIELD_OFFSETS.values() for o in group)
STOP_OPS=frozenset({16,17,18,19})
GPR_DWRITE_OPS=frozenset({
    7,8,10,11,12,13,14,15,20,21,23,24,25,26,27,28,29,30,31,
    32,33,34,35,40,41,42,43,46,47,
})
MAX_SITES_PER_FAMILY=24
MAX_INSTRUCTIONS=20


def form(w):
    """Exact *syntactic* PPC D-form extraction, not typed receiver semantics."""
    op=w>>26
    if op not in (32,36,48,52):
        return None
    offset=w&0xffff
    if offset&0x8000:
        offset-=0x10000
    return {
        "op":op,
        "register":(w>>21)&31,
        "base":(w>>16)&31,
        "offset":offset,
    }


def label(pc,unit):
    lo,hi=SOURCE_UNITS[unit]
    if pc<lo or pc>=hi or pc%4:
        raise ValueError("Original source code site out of public unit")
    return f"{unit}+0x{pc-lo:04X}"


def containing_focus(pc):
    return [name for name,(a,b) in FOCUS.items() if a<=pc<b]


def direct_store_inventory(read):
    report={}
    for name,(lo,hi) in SOURCE_UNITS.items():
        members=Counter()
        sites={}
        for pc in range(lo,hi,4):
            q=form(read(pc))
            if q is None or q["op"] not in (36,52):
                continue
            if q["offset"] not in TARGET_OFFSETS:
                continue
            key=("float_store" if q["op"]==52 else "word_store",q["offset"])
            members[key]+=1
            if len(sites.setdefault(key,[]))<MAX_SITES_PER_FAMILY:
                sites[key].append({
                    "source_instruction_relative":label(pc,name),
                    "in_known_focus_window":containing_focus(pc),
                    "base_is_selected_Ball_proven":False,
                    "executed_in_original_tree_shot_proven":False,
                })
        report[name]={
            "candidate_displacement_store_instruction_count":sum(members.values()),
            "source_field_displacement_sites":[
                {"instruction_kind":kind,
                 "D_form_displacement":f"+0x{off:03X}",
                 "source_instruction_count":n,
                 "sites":sites[(kind,off)],
                 "source_receiver_Ball_identity_proven":False}
                for (kind,off),n in sorted(members.items(),
                         key=lambda v:(v[0][1],v[0][0]))
            ],
        }
    return report


def gpr_clobber(word,reg):
    op=word>>26
    return op in GPR_DWRITE_OPS and ((word>>21)&31)==reg


def ptr_member_copies(read,unit):
    """Conservative bounded source syntax, no C++ receiver proof."""
    lo,hi=SOURCE_UNITS[unit]
    sites=[]
    dropped=0
    for pc in range(lo,hi,4):
        anchor=form(read(pc))
        if not (anchor and anchor["op"]==32
                and anchor["offset"]==0x4C
                and anchor["register"] not in (0,1)):
            continue
        ptr=anchor["register"]
        hits=[]
        stop="end_of_source_window"
        for i in range(1,MAX_INSTRUCTIONS+1):
            check=pc+4*i
            if check>=hi:
                stop="bounded_unit_end"
                break
            w=read(check)
            op=w>>26
            if op in STOP_OPS:
                stop="control_transfer_before_verified_copy"
                break
            q=form(w)
            if q and q["op"]==52 and q["base"]==ptr and q["offset"] in (0,4,8):
                hits.append({
                    "source_store_relative":label(check,unit),
                    "triplet_relative_component_offset":f"+0x{q['offset']:01X}",
                    "source_fp_reg_index":q["register"],
                    "source_pointer_reg_index":ptr,
                })
            if gpr_clobber(w,ptr):
                stop="gpr_candidate_pointer_clobber"
                break
            if len(hits)==3:
                stop="three_possible_components_seen"
                break
        if hits:
            if len(sites)<MAX_SITES_PER_FAMILY:
                sites.append({
                    "source_lwz_0x4C_relative":label(pc,unit),
                    "possible_stfs_through_pointer":hits,
                    "stop_reason":stop,
                    "same_selected_Ball_receiver_verified":False,
                    "source_native_store_executed_in_live_110_packets":False,
                })
            else:
                dropped+=1
    return {
        "bounded_lwz_plus_0x4C_to_stfs_zero_four_eight_candidates":sites,
        "extra_candidates_not_displayed":dropped,
        "source_lwz_receiver_identity_proven":False,
        "source_ptr_register_dataflow_complete":False,
    }


def source_audit(read):
    result=direct_store_inventory(read)
    pointer={name:ptr_member_copies(read,name) for name in SOURCE_UNITS}
    return {
        "kind":"P0_ORIGINAL_TREE_BALL_SOURCE_STORES_V1",
        "status":"ORIGINAL_SHA_SOURCE_SELECTED_PPC_SYNTAX_ONLY",
        "source_unit_displacement_stores":result,
        "source_unit_plus_0x4C_pointer_derived_float_triplets":pointer,
        "source_window_roles":{k:{"owner_hint":k,"role_is_hypothesis":True}
                               for k in FOCUS},
        "same_source_receiver_as_live_selected_Ball_proven":False,
        "actual_collision_instruction_executed_proven":False,
        "ball_plus_0x30_world_translation_semantics_proven":False,
        "ball_plus_0xCC_f0_fc_cache_copy_semantics_proven":False,
        "native_wood_vs_leaf_contact_branch_verified":False,
        "native_velocity_or_impulse_verified":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    if capture not in range(1,8):
        raise ValueError("Original archive selected capture 1..7")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for n,size in enumerate(seven.SIZE,1):
            f=seven.src._file(roots[capture],f"{capture}.{n}.raw",size)
            h=stack.enter_context(f.open("rb"))
            banks.append(stack.enter_context(mmap.mmap(
                h.fileno(),0,access=mmap.ACCESS_READ)))
        reader=seven.roster.TwoBankReader(*banks)
        source=seven._get(reader)
        field=source["field"]
        count=reader.u32(field+0x1C)
        tree_array=reader.u32(field+0x20)
        if count!=94 or seven.roster._bank(tree_array,count*84)!="MEM2":
            raise ValueError("Original 94 tree array source ownership failure")
        def read(pc):
            if pc<MEM1 or pc+4>MEM1+len(banks[0]) or pc%4:
                raise ValueError("Native code outside MEM1 source")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        # Existing independent static PPC producer, scene and native call gates.
        if not units.tree_loop_source_gated(read):
            raise ValueError("Original FieldManager tree source call changed")
        flags.validate_source(read)
        kcol.inspect(read,strict=True)
        report=source_audit(read)
    seven._check_archive(archive)
    return {
        **report,
        "original_capture_number":capture,
        "original_native_archive_sha_qualified":True,
        "original_golf_scene_source_qualified":True,
        "original_native_94_tree_receiver_loop_qualified":True,
        "original_5_ball_to_kcol_7_reverse_calls_gated":True,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=p.parse_args(argv)
    try:
        out=run(args.archive,args.capture)
        print(json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False))
        return 0
    except (ValueError,OSError,IndexError,OverflowError,TypeError,
            AttributeError,KeyError,struct.error):
        print(json.dumps({"kind":"P0_ORIGINAL_TREE_BALL_SOURCE_STORES_V1",
            "status":"ABSTAIN_ORIGINAL_SHA_OR_NATIVE_SOURCE_GATES",
            "training_approved":False}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
