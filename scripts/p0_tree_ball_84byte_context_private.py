#!/usr/bin/env python3
"""Source-gated P0 ball code around +84 iteration / tree object entry.

Real Wii Sports Golf Rev1 original seven-pair SHA, scene, tree loop gate.
Reports bounded public source-relative PPC native instructions, optional
terminal-only words; no ROM uploads, heap/positions, or Dolphin writes.
An 84-byte addi in ball code is only a structural coincidence until the
source array receiver and actual collision response are proven.
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
import p0_tree_hitbox_source_callgraph_private as src
import p0_tree_hitbox_five_calls_private as decoder

MEM1=0x80000000
# First is around the ONLY Ball unit addi +84 found in real original
# source scan; second is a small constructor/iteration code window
# for the object identified by the field-manager tree loop.
WINDOWS=(
    ("ball_84_byte_step_context","Ball",0x0640,0x0820),
    ("tree_init_first_84_bytes","Tree",0x0000,0x00C0),
)
ANCHORS=(
    ("Ball",0x0738,14,84),
    ("Tree",0x002C,14,84),
)
MAX_WORDS=180
assert sum((hi-lo)//4 for _,__,lo,hi in WINDOWS)<=MAX_WORDS


def scan(read, *, detail=False):
    for unit,off,op,imm in ANCHORS:
        word=read(src.UNITS[unit][0]+off)
        if word>>26!=op or (word&0xFFFF)!=imm:
            raise ValueError("Source-index +84 native PPC anchor changed")
    output=[]
    for name,unit,lo,hi in WINDOWS:
        unit_start,unit_end=src.UNITS[unit]
        if not (0<=lo<hi and lo%4==0 and hi%4==0 and unit_start+hi<=unit_end):
            raise ValueError("Not source bounded")
        calls=[]
        field_offset_sites=[]
        stack_assigns=[]
        lines=[]
        for off in range(lo,hi,4):
            pc=unit_start+off
            w=read(pc)
            decoded=src.dform(w)
            if decoded and decoded[3] in (0x1C,0x20,0x30,0x3C,0x48,0x4C,0x50):
                field_offset_sites.append({
                    "site":f"+0x{off:04X}",
                    "kind":decoded[0],
                    "base_register":"r"+str(decoded[2]),
                    "field_offset":f"+0x{decoded[3]:02X}",
                    "stack_based":decoded[2]==1,
                })
            if decoded and decoded[2]==1 and decoded[0] in ("stw","lwz"):
                stack_assigns.append(f"+0x{off:04X}")
            b=src.direct_b(pc,w)
            if b and b[1] and len(calls)<16:
                calls.append({"caller":f"+0x{off:04X}",
                              "target":decoder.source_label(b[0])})
            if detail:
                lines.append(f"{unit}+0x{off:04X}  {w:08X}  {decoder.ppc(pc,w)}")
        record={
            "source_window":name,
            "source_unit":unit,
            "window_relative":f"+0x{lo:04X}..+0x{hi-4:04X}",
            "word_count":(hi-lo)//4,
            "direct_call_targets":calls,
            "object_member_offset_sites":field_offset_sites[:26],
            "stack_load_store_count":len(stack_assigns),
            "tree_array_receiver_proven":False,
            "ball_tree_contact_proven":False,
        }
        if detail:
            record["local_source_code_lines"]=lines
        output.append(record)
    return output


def run(archive,capture,detail=False):
    if capture not in range(1,8):
        raise ValueError("Invalid capture")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            p=seven.src._file(folders[capture],f"{capture}.{i}.raw",size)
            h=stack.enter_context(p.open("rb"))
            banks.append(stack.enter_context(mmap.mmap(
                h.fileno(),0,access=mmap.ACCESS_READ)))
        reader=seven.roster.TwoBankReader(*banks)
        field=seven._get(reader)["field"]
        count=reader.u32(field+0x1C)
        tree=reader.u32(field+0x20)
        if count!=94 or seven.roster._bank(tree,count*84)!="MEM2":
            raise ValueError("Source tree array unqualified")
        def word(pc):
            if not MEM1<=pc<=MEM1+len(banks[0])-4:
                raise ValueError("Outside native source MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        if not src.tree_loop_source_gated(word):
            raise ValueError("Source tree PPC loop mismatch")
        out=scan(word,detail=detail)
    seven._check_archive(archive)
    return {
        "kind":"P0_TREE_BALL_84BYTE_CODE_CONTEXT",
        "status":"SOURCE_BOUNDED_BALL_STRIDE_CONTEXT",
        "capture":capture,"tree_count_source":count,
        "source_sha_scene_and_tree_loop_qualified":True,
        "windows":out,
        "tree_collision_receiver_verified":False,
        "tree_geometry_verified":False,
        "tree_impact_response_verified":False,
        "training_approved":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--capture",choices=range(1,8),type=int,default=7)
    p.add_argument("--detail",action="store_true")
    args=p.parse_args(argv)
    try:
        report=run(args.archive,args.capture,args.detail)
        if args.detail:
            print(json.dumps({k:v for k,v in report.items() if k!="windows"},sort_keys=True,separators=(",",":")))
            for w in report["windows"]:
                print(f"===== {w['source_window']} {w['window_relative']} =====")
                print("\n".join(w["local_source_code_lines"]))
            print("===== END TREE-BALL 84-BYTE SOURCE CONTEXT =====")
        else:
            print(json.dumps(report,sort_keys=True,separators=(",",":")))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,
            OverflowError,AttributeError,struct.error):
        print('{"status":"ABSTAIN_BALL_TREE_SOURCE_CODE","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
