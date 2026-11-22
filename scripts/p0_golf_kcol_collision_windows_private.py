#!/usr/bin/env python3
"""Source-gated Wii Sports Golf KCL query / ball-contact code windows.

Output is bounded to five deliberately selected original-golf KCL executable
regions, including main query dispatcher +0x0000, its +0x1540 callee, a
ball-callable +0x1AC4 wrapper, the +0x2090 triangle processing branch,
and +0x31F0 auxiliary setup. Static source instrumentation ONLY.

No Dolphin access, no original ROM/heap coordinates, no game writes. Native
PPC word hex in --detail is printed only to the operator terminal, never
committed. The original seven-pair SHA + scene + 84-byte tree loop and
anchor PPC control edges must qualify. No claimed tree shapes or physics.
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
import p0_tree_hitbox_source_callgraph_private as linkage
import p0_tree_hitbox_five_calls_private as decoding

KCOL_LO,KCOL_HI=linkage.UNITS["GolfKCol"]
MEM1=0x80000000
WINDOWS=(
    ("kcl_query_entry",0x0000,0x00B0),
    ("query_dispatch_callee",0x1540,0x1620),
    ("ball_query_wrapper",0x1AC4,0x1B40),
    ("collision_triangle_narrowphase",0x2090,0x21F8),
    ("kcl_state_init_candidate",0x31F0,0x3270),
)
MAX_WORDS=260
assert sum((end-start)//4 for _,start,end in WINDOWS)<=MAX_WORDS
# Anchors previously operator-observed on original phase7. Source-relative.
ANCHORS={
    0x0000:0x9421FFB0,
    0x0034:0x4800150D,
    0x1AC4:0xC0230054,
    0x1AE4:0x480005AC,
    0x21D4:0x4BFF0E79,
}
# Exclude modules with utility helpers from any collision-specific inference.
NO_TREE_HITBOX_PROOF=True


def branch_to(word,pc):
    direct=linkage.direct_b(pc,word)
    if direct:
        return direct
    return None


def verify_anchors(read):
    for off,word in ANCHORS.items():
        if read(KCOL_LO+off)!=word:
            raise ValueError("Original GolfKCol source-word anchor mismatch")
    pc=KCOL_LO+0x0034
    branch=branch_to(read(pc),pc)
    if branch!=(KCOL_LO+0x1540,True):
        raise ValueError("Query dispatcher callee mismatch")
    pc=KCOL_LO+0x1AE4
    branch=branch_to(read(pc),pc)
    if branch!=(KCOL_LO+0x2090,False):
        raise ValueError("Narrowphase wrapper branch mismatch")
    return True


def summarize(read, *, detail=False):
    if not verify_anchors(read):
        raise ValueError("Source/code gate failed")
    outputs=[]
    for name,start,end in WINDOWS:
        if not (0<=start<end and start%4==0 and end%4==0
                and KCOL_LO+end<=KCOL_HI):
            raise ValueError("Code window not source bounded")
        direct=[]
        compares=[]
        fps=[]
        lines=[]
        for off in range(start,end,4):
            pc=KCOL_LO+off
            word=read(pc)
            bl=branch_to(word,pc)
            if bl:
                dst,linked=bl
                if len(direct)<16:
                    direct.append({
                        "source_offset":f"+0x{off:04X}",
                        "link":linked,
                        "destination":decoding.source_label(dst)
                    })
            if word>>26==63 and ((word>>1)&1023) in (0,32):
                if len(compares)<12:
                    compares.append(f"+0x{off:04X}")
            d=linkage.dform(word)
            if d and d[0] in ("lfs","lfsu","stfs","stfsu") and len(fps)<16:
                fps.append({"source_offset":f"+0x{off:04X}",
                            "mnemonic":d[0],
                            "base_register":f"r{d[2]}",
                            "offset_bytes":d[3]})
            if detail:
                lines.append(f"GolfKCol+0x{off:04X}  {word:08X}  {decoding.ppc(pc,word)}")
        output={
            "window":name,
            "relative_range":f"+0x{start:04X}..+0x{end-4:04X}",
            "words":(end-start)//4,
            "direct_source_branches":direct,
            "floating_compares":compares,
            "selected_float_member_accesses":fps,
            "source_tree_receiver_verified":False,
            "ball_tree_contact_verified":False,
        }
        if detail:
            output["source_code_lines"]=lines
        outputs.append(output)
    return outputs


def run(archive:Path,capture:int,detail:bool):
    if capture not in range(1,8):
        raise ValueError("Only original capture 1..7 allowed")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            path=seven.src._file(folders[capture],f"{capture}.{i}.raw",size)
            handle=stack.enter_context(path.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(handle.fileno(),0,access=mmap.ACCESS_READ)))
        reader=seven.roster.TwoBankReader(*banks)
        field=seven._get(reader)["field"]
        count=reader.u32(field+0x1C)
        trees=reader.u32(field+0x20)
        if count!=94 or seven.roster._bank(trees,count*84)!="MEM2":
            raise ValueError("Original source tree owner unavailable")
        def read(pc):
            if not MEM1<=pc<=MEM1+len(banks[0])-4:
                raise ValueError("Original MEM1 native source text outside bounds")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        if not linkage.tree_loop_source_gated(read):
            raise ValueError("Original source array fingerprint not found")
        result=summarize(read,detail=detail)
    seven._check_archive(archive)
    return {
        "kind":"P0_OGWS_GOLFKCOL_NARROWPHASE_SOURCE_WINDOWS",
        "status":"GOLF_KCOL_QUERY_WINDOWS_SOURCE_VERIFIED",
        "capture":capture,
        "source_count_trees":94,
        "original_sha_and_scene_gated":True,
        "windows":result,
        "tree_hitbox_shape_verified":False,
        "trunk_leaves_split_verified":False,
        "ball_velocity_contact_response_verified":False,
        "training_approved":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    p.add_argument("--detail",action="store_true")
    a=p.parse_args(argv)
    try:
        report=run(a.archive,a.capture,a.detail)
        if a.detail:
            print(json.dumps({k:v for k,v in report.items() if k!="windows"},sort_keys=True,separators=(",",":")))
            for window in report["windows"]:
                print(f"===== {window['window']} {window['relative_range']} =====")
                print("\n".join(window["source_code_lines"]))
            print("===== END FIVE KCOL SOURCE WINDOWS =====")
        else:
            print(json.dumps(report,sort_keys=True,separators=(",",":")))
        return 0
    except (OSError,ValueError,IndexError,KeyError,TypeError,OverflowError,
            AttributeError,struct.error):
        print('{"status":"ABSTAIN_GOLFKCOL_SOURCE_WINDOWS","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
