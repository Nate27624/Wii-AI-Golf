#!/usr/bin/env python3
"""Original P0 source-gated Tree table vs Ball dispatch-receiver aliases.

The previous capture7 indirect audit observed 94 shared Tree firstwords,
34 Ball bctrl sites, and several source chains that load tables from
candidate Ball child objects. This read-only original RSPE01 Rev1 probe
checks whether the actual *captured* candidate Ball child objects use
the SAME table address as the native 94 Tree records.

Strict sources: original 7-pair archive SHA/scene, 94x84 FieldManager loop,
five Ball->KCol and seven inverse PPC paths, precise D-form and bctrl
anchors of the listed Ball source call sites. Candidate Ball pointers
come ONLY from the previously source-correlated 4-entry PlayerManager
roster; these remain object hypotheses, not verified active golfers.

Never export RAM pointers, raw KCL/ROM/code words, private XYZ, or game
assets. A vtable alias would NOT prove a tree hit/collider, and a
negative match would NOT rule out other/indirect collision pathways.
No training approval, Dolphin, game writes, or new captures.
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
import audit_p0_seven_numbered_source_pairs_private as seven
import audit_golf_two_bank_roster_private as roster
import p0_ball_kcol_active_resource_private as active
import p0_tree_ball_indirect_dispatch_private as indirect
import p0_tree_hitbox_source_callgraph_private as native

MEM1=roster.MEM1_BASE
EXPECTED_SOURCE=(
    # site, PPC opcode, target reg, base reg, signed member offset
    (0x03BC,32,3,31,0x144),  # source receiver r31 -> child 0x144
    (0x03C4,32,12,3,0x78),   # child+0x78 -> dispatch table
    (0x03C8,32,12,12,0x48),  # dispatch entry
    (0x0484,32,3,31,0x140),
    (0x048C,32,12,3,0x00),
    (0x0490,32,12,12,0x7C),
    (0x049C,32,3,31,0x13C),
    (0x04A0,32,12,3,0x00),
    (0x04A4,32,12,12,0x88),
    (0x04B0,32,3,31,0x140),
    (0x04B4,32,12,3,0x00),
    (0x04B8,32,12,12,0x88),
)
SOURCE_BCTRL=(0x03D0,0x0498,0x04AC,0x04C0)
SOURCE_MTCTR=(0x03CC,0x0494,0x04A8,0x04BC)
CHILDREN=(
    ("child_plus_0x13C_firstword",0x13C,0),
    ("child_plus_0x140_firstword",0x140,0),
    ("child_plus_0x144_plus_0x78",0x144,0x78),
)
MAX_ROSTER_SLOTS=roster.ROSTER_SLOTS


def signed16(x):
    return x-65536 if x&0x8000 else x


def validate_source(read):
    active.inspect_source(read)
    if not native.tree_loop_source_gated(read):
        raise ValueError("Original source Tree loop changed")
    ball_base=native.UNITS["Ball"][0]
    for off,opcode,rt,ra,disp in EXPECTED_SOURCE:
        word=read(ball_base+off)
        result=(word>>26,(word>>21)&31,(word>>16)&31,
                signed16(word&0xFFFF))
        if result!=(opcode,rt,ra,disp):
            raise ValueError("Original Ball dispatch receiver chain changed")
    for off in SOURCE_BCTRL:
        if read(ball_base+off)!=0x4E800421:
            raise ValueError("Original indirect call site changed")
    for off in SOURCE_MTCTR:
        word=read(ball_base+off)
        if word>>26!=31 or (word>>1)&1023!=467:
            raise ValueError("Original CTR write site missing")
        spr=((word>>16)&31)|(((word>>11)&31)<<5)
        if spr!=9:
            raise ValueError("Original CTR write target changed")
    return True


def bounded_table(rd,object_ptr,member_off,subfield_off,bank):
    if bank(object_ptr,0x148)!="MEM2":
        return "source_object_unavailable",False
    child=rd.u32(object_ptr+member_off)
    if bank(child,subfield_off+4) not in ("MEM1","MEM2"):
        return "child_unavailable",False
    table=rd.u32(child+subfield_off)
    if bank(table,0x8C+4)!="MEM1":
        return "table_unavailable",False
    return table,True


def compare_receivers(rd,tree_table,bank):
    pm=rd.u32(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    if bank(pm,roster.ROSTER_SLOTS*roster.ROSTER_STRIDE+roster.BALL_CANDIDATE_MEMBER)!="MEM2":
        raise ValueError("Original PlayerManager candidate outside MEM2")
    rows=[]
    for i in range(MAX_ROSTER_SLOTS):
        ball=rd.u32(pm+roster.BALL_CANDIDATE_MEMBER+i*roster.ROSTER_STRIDE)
        if bank(ball,0x148)!="MEM2":
            continue
        firstword=rd.u32(ball)
        if not roster._in_data(firstword,roster.BALL_DATA):
            continue
        row={"slot":i,"ball_candidate_firstword_in_public_Ball_data":True}
        for name,member,subfield in CHILDREN:
            value,valid=bounded_table(rd,ball,member,subfield,bank)
            row[name+"_table_bounded"]=valid
            row[name+"_table_equals_94_tree_firstword"]=(
                value==tree_table if valid else None)
        rows.append(row)
    if not rows:
        raise ValueError("No source-correlated Ball candidate objects")
    return {
        "ball_candidate_source_roster_slots_examined":MAX_ROSTER_SLOTS,
        "ball_candidate_firstword_in_public_Ball_data_count":len(rows),
        "candidate_ball_child_receivers":rows,
        "candidate_alias_to_tree_table_count_by_child":{
            name:sum(int(r[name+"_table_equals_94_tree_firstword"] is True)
                     for r in rows)
            for name,_,_ in CHILDREN
        },
        "candidate_ball_children_are_actual_impact_receivers_proven":False,
        "shared_firstword_is_actual_cpp_vtable_proven":False,
        "indirect_target_reaching_definition_proven":False,
        "tree_contact_event_proven":False,
        "native_tree_hitbox_proven":False,
        "ball_velocity_response_proven":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    if capture not in range(1,8):
        raise ValueError("Only original seven phases supported")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            p=seven.src._file(folders[capture],f"{capture}.{i}.raw",size)
            handle=stack.enter_context(p.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(handle.fileno(),0,access=mmap.ACCESS_READ)))
        rd=roster.TwoBankReader(*banks)
        field=seven._get(rd)["field"]
        tree_count=rd.u32(field+0x1C)
        array=rd.u32(field+0x20)
        if tree_count!=94 or roster._bank(array,tree_count*84)!="MEM2":
            raise ValueError("Original source 94 trees unavailable")
        def read(pc):
            if not MEM1<=pc<=MEM1+len(banks[0])-4:
                raise ValueError("Original native instruction outside MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        validate_source(read)
        def bank(p,n):
            return roster._bank(p,n)
        tree=indirect.inspect_tree_firstword(rd.u32,array,tree_count,bank)
        if not tree["all_94_tree_firstwords_identical"]:
            raise ValueError("Source shared tree firstword changed")
        table=rd.u32(array)
        comparison=compare_receivers(rd,table,bank)
    seven._check_archive(archive)
    return {
        "kind":"P0_TREE_TABLE_VS_BALL_CHILD_INDIRECT_RECEIVERS",
        "status":"SOURCE_BOUNDED_RUNTIME_TABLE_ALIAS_COMPARISON",
        "capture":capture,
        "original_archive_sha_scene_94_tree_and_ball_kcol_gates":True,
        "ball_dispatch_source_chain_offsets_verified":[
            "+0x03BC..+0x03D0","+0x0484..+0x04C0"],
        **comparison,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=p.parse_args(argv)
    try:
        print(json.dumps(run(args.archive,args.capture),sort_keys=True,
                         separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,IndexError,OverflowError,
            AttributeError,KeyError,struct.error):
        print('{"status":"ABSTAIN_TREE_TABLE_BALL_RECEIVER_COMPARISON",'
              '"training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
