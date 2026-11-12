#!/usr/bin/env python3
"""Source-gated OGWS Golf per-tree +0x48 flag producer/consumer code windows.

Read-only original SHA/scene source cohort; exactly the 94 trees, 84-byte
objects, native Tree+0x0044 flag producer and Tree+0x0504/FieldManager+0x0788
potential byte consumers. Only native CODE is disassembled to operator terminal,
never native heap, tree coordinates, pointer values or model geometry.

Source-unit-relative offsets alone do NOT prove Tree+0x0504's receiver points
to a tree object nor establish rendering, LOD, collision or ball dynamics.
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
import p0_tree_hitbox_source_callgraph_private as source
import p0_tree_hitbox_five_calls_private as disasm
import p0_tree_proximity_flag_private as proximity

MEM1=0x80000000
COUNT=94
STRIDE=84
WINDOWS=(
    ("tree_flag_producer","Tree",0x000C,0x005C),
    ("tree_flag_consumer_candidate","Tree",0x0450,0x05C0),
    ("field_manager_flag_consumer_candidate","FieldManager",0x073C,0x07C0),
)
MAX_WORDS=150
assert sum((hi-lo)//4 for _,__,lo,hi in WINDOWS) <= MAX_WORDS
CONSUMERS=(
    ("Tree",0x0504,30),
    ("FieldManager",0x0788,3),
)


def check_anchors(read):
    if not proximity.fingerprint(read):
        raise ValueError("Tree distance producer source fingerprint mismatch")
    for name,off,base in CONSUMERS:
        word=read(source.UNITS[name][0]+off)
        if word>>26!=34 or (word&0xFFFF)!=0x48 or ((word>>16)&31)!=base:
            raise ValueError("Source candidate byte consumer changed")


def summarize(read,detail):
    check_anchors(read)
    rows=[]
    for name,unit,start,end in WINDOWS:
        lo,hi=source.UNITS[unit]
        if start<0 or start%4 or end%4 or start>=end or lo+end>hi:
            raise ValueError("Unbounded code window")
        lines=[]
        branches=[]
        nearby=[]
        for off in range(start,end,4):
            pc=lo+off
            word=read(pc)
            if detail:
                lines.append(f"{unit}+0x{off:04X} {word:08X} {disasm.ppc(pc,word)}")
            op=word>>26
            reg=(word>>16)&31
            disp=word&0xFFFF
            if disp==0x48 and op in (32,34,36,38):
                nearby.append({
                    "site":f"+0x{off:04X}",
                    "instruction":{32:"lwz",34:"lbz",36:"stw",38:"stb"}[op],
                    "base_register":f"r{reg}","source_owner_proven":False})
            edge=source.direct_b(pc,word)
            if edge and len(branches)<16:
                dest,link=edge
                branches.append({
                    "site":f"+0x{off:04X}",
                    "linked_call":link,
                    "target":disasm.source_label(dest)})
        row={
            "window":name,
            "unit":unit,
            "source_relative_range":f"+0x{start:04X}..+0x{end-4:04X}",
            "instruction_count":(end-start)//4,
            "offset_0x48_sites":nearby,
            "direct_external_branch_targets":branches,
            "receiver_proven_to_be_tree":False,
            "collision_or_rendering_semantics_verified":False,
        }
        if detail:
            row["operator_local_code_lines"]=lines
        rows.append(row)
    return rows


def run(archive:Path,capture:int,detail:bool):
    if capture not in range(1,8):
        raise ValueError("Unsupported source phase")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            path=seven.src._file(folders[capture],f"{capture}.{i}.raw",size)
            handle=stack.enter_context(path.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(handle.fileno(),0,access=mmap.ACCESS_READ)))
        rd=seven.roster.TwoBankReader(*banks)
        field=seven._get(rd)["field"]
        count=rd.u32(field+0x1C)
        arr=rd.u32(field+0x20)
        if count!=COUNT or seven.roster._bank(arr,count*STRIDE)!="MEM2":
            raise ValueError("Source tree object array mismatch")
        def code(pc):
            if not MEM1<=pc<=MEM1+len(banks[0])-4:
                raise ValueError("Invalid native PPC code range")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        if not source.tree_loop_source_gated(code):
            raise ValueError("Source 84-byte stride PPC changed")
        outputs=summarize(code,detail)
        byte_hist={}
        for i in range(COUNT):
            raw=rd.u32(arr+i*STRIDE+0x48)
            flag=(raw>>24)&0xFF
            byte_hist[str(flag)]=byte_hist.get(str(flag),0)+1
    seven._check_archive(archive)
    return {
        "kind":"P0_TREE_DISTANCE_FLAG_CONSUMER_TRACE",
        "status":"SOURCE_BOUNDED_TREE_FLAG_CONSUMER_CONTEXT",
        "original_sha_scene_tree_stride_gated":True,
        "capture":capture,
        "source_trees":count,
        "tree_distance_producer_known":True,
        "source_flag_byte_offset":"0x48",
        "source_flag_byte_histogram":byte_hist,
        "windows":outputs,
        "consumer_receiver_proven":False,
        "tree_hitbox_geometry_verified":False,
        "flag_is_collision_verified":False,
        "training_approved":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--capture",choices=range(1,8),type=int,default=7)
    p.add_argument("--detail",action="store_true")
    args=p.parse_args(argv)
    try:
        result=run(args.archive,args.capture,args.detail)
        if args.detail:
            print(json.dumps({k:v for k,v in result.items() if k!="windows"},
                             sort_keys=True,separators=(",",":")))
            for w in result["windows"]:
                print(f"===== {w['window']} {w['source_relative_range']} =====")
                print("\n".join(w["operator_local_code_lines"]))
            print("===== END TREE FLAG CODE WINDOWS =====")
        else:
            print(json.dumps(result,sort_keys=True,separators=(",",":")))
        return 0
    except (ValueError,OSError,OverflowError,TypeError,KeyError,
            IndexError,AttributeError,struct.error):
        print('{"status":"ABSTAIN_TREE_FLAG_CONSUMER_SOURCE","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
