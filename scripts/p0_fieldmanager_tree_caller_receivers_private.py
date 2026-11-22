#!/usr/bin/env python3
"""Read-only source-bound 94-tree loop versus unrelated +0x48 reader caller.

Operator-local PPC disassembly around exactly two distinct native calls:
  FieldManager+0x2BB4 -> Tree+0x000C (source 94x84 tree-loop writer),
  FieldManager+0x230C -> Tree+0x047C (the visually similar +0x48 reader).
Their target source-unit membership alone is not receiver-class evidence.
All original 7-pair archive SHA, scene, original tree loop and known code
gates must pass. No native heap words, model data, positions, or game writes.
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
import p0_tree_hitbox_source_callgraph_private as native
import p0_tree_hitbox_five_calls_private as ppc
import p0_tree_flag_receiver_disambiguation_private as identity

FIELD=native.UNITS["FieldManager"][0]
TREE=native.UNITS["Tree"][0]
MEM1=0x80000000
WINDOWS=(
    ("unknown_reader_caller","FieldManager",0x2220,0x2340),
    ("known_94_tree_writer_caller","FieldManager",0x2B20,0x2C20),
    ("unknown_reader_callee_entry","Tree",0x047C,0x04B0),
    ("known_94_tree_writer_entry","Tree",0x000C,0x005C),
)
CALL_LINKS=(
    ("unknown_reader_caller",FIELD+0x230C,TREE+0x047C),
    ("known_94_tree_writer_caller",FIELD+0x2BB4,TREE+0x000C),
)
MAX_WORDS=176
assert sum((end-start)//4 for _,__,start,end in WINDOWS)<=MAX_WORDS


def inspect(code, detail=False):
    identity.validate_source(code)
    for label,site,target in CALL_LINKS:
        b=native.direct_b(site,code(site))
        if b!=(target,True):
            raise ValueError("Original FieldManager -> Tree source edge changed")
    result=[]
    for name,unit,start,end in WINDOWS:
        lo,hi=native.UNITS[unit]
        if not (0<=start<end and start%4==0 and end%4==0 and lo+end<=hi):
            raise ValueError("Native source window exceeds public object")
        branches=[]
        byte_fields=[]
        lines=[]
        for off in range(start,end,4):
            pc=lo+off
            word=code(pc)
            b=native.direct_b(pc,word)
            if b:
                target,link=b
                if len(branches)<20:
                    branches.append({
                        "relative_site":f"+0x{off:04X}",
                        "linked_call":link,
                        "target":ppc.source_label(target),
                    })
            field=native.dform(word)
            if field and field[3] in (0x1C,0x20,0x24,0x28,0x30,0x3C,0x48,0x4C,0x50):
                if len(byte_fields)<24:
                    byte_fields.append({
                        "relative_site":f"+0x{off:04X}",
                        "mnemonic":field[0],
                        "base_register":f"r{field[2]}",
                        "displacement_bytes":field[3],
                    })
            if detail:
                lines.append(f"{unit}+0x{off:04X} {word:08X} {ppc.ppc(pc,word)}")
        out={
            "window":name,
            "public_unit":unit,
            "relative_range":f"+0x{start:04X}..+0x{end-4:04X}",
            "source_instruction_count":(end-start)//4,
            "direct_branch_targets":branches,
            "selected_member_offset_accesses":byte_fields,
            "known_tree_array_object_receiver_verified":name.startswith("known_94_tree_writer"),
            "separate_reader_is_94_tree_object_proven":False,
            "tree_collision_geometry_verified":False,
        }
        if detail:
            out["operator_local_code_lines"]=lines
        result.append(out)
    return result


def run(archive:Path,capture:int,detail:bool):
    if capture not in range(1,8):
        raise ValueError("Invalid original phase")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            f=seven.src._file(folders[capture],f"{capture}.{i}.raw",size)
            h=stack.enter_context(f.open("rb"))
            banks.append(stack.enter_context(mmap.mmap(
                h.fileno(),0,access=mmap.ACCESS_READ)))
        reader=seven.roster.TwoBankReader(*banks)
        field=seven._get(reader)["field"]
        count=reader.u32(field+0x1C)
        arr=reader.u32(field+0x20)
        if count!=94 or seven.roster._bank(arr,count*84)!="MEM2":
            raise ValueError("Source tree inventory mismatch")
        def code(pc):
            if not MEM1<=pc<=MEM1+len(banks[0])-4:
                raise ValueError("Native instruction out of source bounds")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        report=inspect(code,detail)
    seven._check_archive(archive)
    return {
        "kind":"P0_FIELD_MANAGER_TREE_CALLER_RECEIVER_TRACE",
        "status":"SOURCE_TREE_WRITER_VS_UNKNOWN_READER_CALLERS",
        "capture":capture,
        "source_trees":count,
        "sha_scene_and_original_tree_loop_qualified":True,
        "public_source_windows":report,
        "same_receiver_identity_verified":False,
        "tree_hitboxes_verified":False,
        "training_approved":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    p.add_argument("--detail",action="store_true")
    a=p.parse_args(argv)
    try:
        r=run(a.archive,a.capture,a.detail)
        if a.detail:
            print(json.dumps({k:v for k,v in r.items() if k!="public_source_windows"},
                             sort_keys=True,separators=(",",":")))
            for w in r["public_source_windows"]:
                print(f"===== {w['window']} {w['relative_range']} =====")
                print("\n".join(w["operator_local_code_lines"]))
            print("===== END SOURCE CALLER RECEIVER WINDOWS =====")
        else:
            print(json.dumps(r,sort_keys=True,separators=(",",":")))
        return 0
    except (ValueError,OSError,TypeError,OverflowError,IndexError,KeyError,
            AttributeError,struct.error):
        print('{"status":"ABSTAIN_TREE_CALLER_RECEIVER_TRACE","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
