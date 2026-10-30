#!/usr/bin/env python3
"""Read-only Wii Sports Golf tree hitbox / ball-physics code-linkage triage.

Source-qualified original RSPE01 Rev1 seven-pair archive, no Dolphin, no
game writes, no private source code words or native addresses published.
This only audits PUBLIC executable source-unit-relative direct call graph
and field accesses: it does not infer hitboxes, tree/leaf forces, radii, or
actual collision behavior from names or a missing direct call.
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

MEM1 = 0x80000000
# Public doldecomp/ogws RSPE01_01 splits.txt compiled object boundaries.
UNITS = {
    "Tree": (0x80296238,0x80296EA8),
    "TreeWater": (0x80296EA8,0x80296F50),
    "Ball": (0x80296FD8,0x8029B240),
    "Simulation": (0x8029B240,0x8029BBB4),
    "GolfKCol": (0x802A3DE4,0x802A7444),
    "FieldManager": (0x80290B44,0x80294184),
    "CollisionChecker": (0x801BC418,0x801BD51C),
    "CollisionModel": (0x801BB9B8,0x801BC384),
    "Rigid": (0x801B9E00,0x801BAEA0), # optional public utility; omitted in results if doubtful
}
# All important interaction source modules; do not guess other out-of-unit
# targets as physics routines without a public function symbol.
SCAN = ("Tree","TreeWater","Ball","Simulation","GolfKCol",
        "FieldManager","CollisionChecker","CollisionModel")
RELEVANT = ("Tree","TreeWater","Ball","Simulation","GolfKCol",
            "CollisionChecker","CollisionModel")
MAX_SITES_PER_EDGE = 12
MAX_FLOAT_OFFSETS = 16
MAX_FLOAT_COMPARISONS = 15
LOOP = 0x80293008


def source_unit(addr):
    for unit,(start,end) in UNITS.items():
        if start <= addr < end:
            return unit
    return None


def direct_b(pc,word):
    """PPC opcode 18, sign-extended 26-bit displacement + AA/LK."""
    if word>>26 !=18:
        return None
    delta=word & 0x03FFFFFC
    if delta & 0x02000000:
        delta-=0x04000000
    target=(delta if word & 2 else pc+delta)&0xFFFFFFFF
    return target, bool(word&1)


def indirect_call(word):
    """PPC op19 bclr/bcctr + LK (indirect target, unknown owner)."""
    if word>>26!=19 or not (word&1):
        return None
    xo=(word>>1)&1023
    return "branch_to_ctr" if xo==528 else "branch_to_lr" if xo==16 else None


def dform(word):
    """Only load/store forms useful as tree-object field clues."""
    op=word>>26
    if op not in (32,36,48,49,52,53,50,54,40,44):
        return None
    names={32:"lwz",36:"stw",48:"lfs",49:"lfsu",52:"stfs",
           53:"stfsu",50:"lfd",54:"stfd",40:"lhz",44:"sth"}
    disp=word&0xFFFF
    if disp & 0x8000:
        disp-=0x10000
    return names[op],(word>>21)&31,(word>>16)&31,disp


def float_compare(word):
    if word>>26!=63:
        return False
    return ((word>>1)&1023) in (0,32)


def tree_loop_source_gated(read):
    """Source-owner corroboration, not exact raw code-word fingerprint."""
    d1=dform(read(LOOP+0x06E8))
    call=direct_b(LOOP+0x06F0,read(LOOP+0x06F0))
    incr=read(LOOP+0x06F4)
    d2=dform(read(LOOP+0x06FC))
    if not (d1 and d1[0]=="lwz" and d1[2]==28 and d1[3]==0x20
            and call and call[1] and source_unit(call[0])=="Tree"
            and incr>>26==14 and ((incr>>21)&31)==31 and
            ((incr>>16)&31)==31 and (incr&0xFFFF)==84
            and d2 and d2[0]=="lwz" and d2[2]==28 and d2[3]==0x1C):
        return False
    return True


def scan_code(read):
    """Static public source call relationships with bounded evidence sites."""
    edges=Counter()
    sites={}
    unknown_out=Counter()
    indirect=Counter()
    floats={}
    comparisons={}
    for owner in SCAN:
        lo,hi=UNITS[owner]
        field_uses=Counter()
        compare_list=[]
        for pc in range(lo,hi,4):
            w=read(pc)
            branch=direct_b(pc,w)
            if branch:
                target,link=branch
                other=source_unit(target)
                if link and other:
                    edges[(owner,other)]+=1
                    edge=(owner,other)
                    if len(sites.setdefault(edge,[]))<MAX_SITES_PER_EDGE:
                        sites[edge].append(
                            {"source_offset":f"+0x{pc-lo:04X}",
                             "target_unit_relative":f"+0x{target-UNITS[other][0]:04X}"})
                elif link:
                    unknown_out[owner]+=1
            indirect_kind=indirect_call(w)
            if indirect_kind:
                indirect[(owner,indirect_kind)]+=1
            field=dform(w)
            if field and field[0] in ("lfs","lfsu","stfs","stfsu"):
                # Field offset is NOT guaranteed tree hitbox data. Merely a
                # numeric access candidate pending register/object tracing.
                mnem,_,register,offset=field
                if 0<=offset<=0x200 and register !=1:
                    field_uses[(mnem,offset)]+=1
            if float_compare(w) and len(compare_list)<MAX_FLOAT_COMPARISONS:
                compare_list.append(f"+0x{pc-lo:04X}")
        floats[owner]=[
            {"access":mnem,"displacement_bytes":offset,"occurrences":n}
            for (mnem,offset),n in sorted(
                field_uses.items(),key=lambda x:(-x[1],x[0][1],x[0][0]))[:MAX_FLOAT_OFFSETS]]
        comparisons[owner]=compare_list
    return {
        "source_public_units":list(SCAN),
        "direct_calls_between_selected_units":[
            {"caller":source,"callee":dest,"count":edges[(source,dest)],
             "bounded_public_relative_sites":sites[(source,dest)]}
            for source,dest in sorted(edges)],
        "direct_calls_to_unclassified_code_by_source":{
            k:unknown_out[k] for k in SCAN},
        "indirect_calls_by_source":[
            {"source":s,"kind":kind,"count":v}
            for (s,kind),v in sorted(indirect.items())],
        "candidate_floating_member_offsets":floats,
        "first_floating_compare_sites":comparisons,
        "tree_collision_geometry_verified":False,
        "tree_ball_collision_call_path_verified":False,
        "leaf_vs_trunk_hitboxes_verified":False,
        "collision_response_coefficients_verified":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    if capture not in range(1,8):
        raise ValueError("Unsupported source capture")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            p=seven.src._file(roots[capture],f"{capture}.{i}.raw",size)
            h=stack.enter_context(p.open("rb"))
            banks.append(stack.enter_context(mmap.mmap(
                h.fileno(),0,access=mmap.ACCESS_READ)))
        rd=seven.roster.TwoBankReader(*banks)
        source=seven._get(rd)
        field=source["field"]
        count=rd.u32(field+0x1C)
        tree_array=rd.u32(field+0x20)
        if not 3<=count<=4096 or seven.roster._bank(tree_array,count*84)!="MEM2":
            raise ValueError("Invalid source-owned tree object array/count")
        def native_word(pc):
            if pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("PPC source out of range")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        if not tree_loop_source_gated(native_word):
            raise ValueError("Rev1 source-owned tree loop no longer matches")
        report=scan_code(native_word)
    seven._check_archive(archive)
    return {
        "kind":"P0_OGWS_TREE_HITBOX_STATIC_LINKAGE",
        "status":"SOURCE_GATED_STATIC_CALL_GRAPH_ONLY",
        "capture":capture,"source_tree_count":count,
        "proven_source_tree_stride_bytes":84,
        "capture_sha_verified":True,
        "scene_source_qualified":True,
        "analysis":report,
        "training_approved":False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",type=Path,required=True)
    parser.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=parser.parse_args(argv)
    try:
        print(json.dumps(run(args.archive,args.capture),sort_keys=True,separators=(",",":")))
        return 0
    except (OSError,ValueError,IndexError,OverflowError,TypeError,
            AttributeError,KeyError,struct.error):
        print('{"kind":"P0_OGWS_TREE_HITBOX_STATIC_LINKAGE",'
              '"status":"ABSTAIN_SOURCE_OR_ARCHIVE_GATE","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
