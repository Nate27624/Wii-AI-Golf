#!/usr/bin/env python3
"""Original Wii Sports Golf: Ball<->GolfKCol callsites, not false tree-hitbox edges.

Read-only original seven-pair SHA/scene gated MEM1 code. No game writes, tree
coordinates, private heap values or ROM committed. --detail prints bounded
native PPC code to the local operator terminal; defaults to concise JSON.
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
import p0_tree_hitbox_source_callgraph_private as links
import p0_tree_hitbox_five_calls_private as disasm

MEM1=0x80000000
EDGES=(("Ball","GolfKCol",5),("GolfKCol","Ball",7))
BEFORE=10
AFTER=8
TARGET=14


def inspect(read,detail=False,strict=True):
    result=[]
    counts={}
    for caller,callee,expected in EDGES:
        lo,hi=links.UNITS[caller]
        count=0
        for pc in range(lo,hi,4):
            branch=links.direct_b(pc,read(pc))
            if not branch or not branch[1] or links.source_unit(branch[0])!=callee:
                continue
            count+=1
            dest=branch[0]
            if pc-BEFORE*4<lo or pc+(AFTER+1)*4>hi:
                raise ValueError("Caller beyond public source bounds")
            if dest+TARGET*4>links.UNITS[callee][1]:
                raise ValueError("Callee beyond public source bounds")
            prev=[read(x) for x in range(pc-BEFORE*4,pc,4)]
            after=[read(x) for x in range(pc+4,pc+(AFTER+1)*4,4)]
            def count_fp(words):
                c=Counter()
                for word in words:
                    q=links.dform(word)
                    if q and q[0] in ("lfs","stfs","lfsu","stfsu"):
                        c[q[0]]+=1
                return dict(sorted(c.items()))
            item={
                "caller":caller,
                "caller_site":f"+0x{pc-lo:04X}",
                "callee":callee,
                "callee_site":f"+0x{dest-links.UNITS[callee][0]:04X}",
                "caller_fp_load_store_prior_10":count_fp(prev),
                "caller_fp_load_store_after_8":count_fp(after),
                "tree_hitbox_verified":False,
            }
            if detail:
                def lines(addrs):
                    return [
                        f"{disasm.source_label(a)}  {read(a):08X}  {disasm.ppc(a,read(a))}"
                        for a in addrs]
                item["caller_code"]=lines(range(pc-BEFORE*4,pc+(AFTER+1)*4,4))
                item["callee_code"]=lines(range(dest,dest+TARGET*4,4))
            result.append(item)
        counts[(caller,callee)]=count
        if strict and count!=expected:
            raise ValueError("Original Ball/KCol call count mismatch")
    if len(result)>12:
        raise ValueError("Unbounded cross-code-unit call count")
    return {
        "status":"BALL_GOLFKCOL_DIRECT_CALLS_SOURCE_AUDITED",
        "pair_counts":[{"caller":a,"callee":b,"calls":counts[(a,b)]}
                       for a,b,_ in EDGES],
        "calls":result,
        "tree_math_helpers_not_hitboxes":True,
        "ball_tree_collision_path_verified":False,
        "native_hitbox_geometry_verified":False,
        "native_contact_response_verified":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int,detail:bool):
    if capture not in range(1,8):
        raise ValueError("Invalid source capture")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            p=seven.src._file(folders[capture],f"{capture}.{i}.raw",size)
            h=stack.enter_context(p.open("rb"))
            banks.append(stack.enter_context(mmap.mmap(h.fileno(),0,access=mmap.ACCESS_READ)))
        rd=seven.roster.TwoBankReader(*banks)
        owner=seven._get(rd)
        field=owner["field"]
        count=rd.u32(field+0x1C)
        trees=rd.u32(field+0x20)
        if count!=94 or seven.roster._bank(trees,count*84)!="MEM2":
            raise ValueError("Source tree owner changed")
        def word(pc):
            if not MEM1<=pc<=MEM1+len(banks[0])-4:
                raise ValueError("Not valid source MEM1 text")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        if not links.tree_loop_source_gated(word):
            raise ValueError("Original PPC 84-byte tree loop mismatch")
        result=inspect(word,detail)
    seven._check_archive(archive)
    return {"kind":"P0_BALL_GOLFKCOL_NATIVE_RECEIVER_TRIAGE",
            "capture":capture,"source_trees":count,
            "original_sha_and_scene_gated":True,**result}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",required=True,type=Path)
    parser.add_argument("--capture",type=int,choices=range(1,8),default=7)
    parser.add_argument("--detail",action="store_true")
    a=parser.parse_args(argv)
    try:
        r=run(a.archive,a.capture,a.detail)
        if a.detail:
            print(json.dumps({k:v for k,v in r.items() if k!="calls"},sort_keys=True,separators=(",",":")))
            for c in r["calls"]:
                print(f"===== {c['caller']}{c['caller_site']} -> {c['callee']}{c['callee_site']} =====")
                print("-- CALLER --")
                print("\n".join(c["caller_code"]))
                print("-- TARGET --")
                print("\n".join(c["callee_code"]))
            print("===== END BOUNDED BALL-KCOL SOURCES =====")
        else:
            print(json.dumps(r,sort_keys=True,separators=(",",":")))
        return 0
    except (ValueError,OSError,IndexError,TypeError,AttributeError,KeyError,
            OverflowError,struct.error):
        print('{"status":"ABSTAIN_SOURCE_OR_CALL_GRAPH","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
