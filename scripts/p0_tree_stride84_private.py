#!/usr/bin/env python3
"""Source-proven 0x54-stride OGWS Golf tree array: private read-only inspector.

Reuses exact original SHA256 seven-phase capture and Rev1 scene/source gates.
Validates PPC tree-constructor loop bytes in private MEM1, then reads exactly
source_count contiguous 0x54 objects from the source field's MEM2 pointer.
Outputs bounded *aggregate* position evidence, no private individual tree
coordinates, heap addresses, vtable words, executable instructions or OBJ.
No Dolphin or game RAM writes. Never approves training.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
import json
import math
import mmap
from pathlib import Path
import statistics
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as seven

MEM1_START = 0x80000000
TREE_SIZE = 0x54  # explicit +84 increment in verified PPC loop
TRANS_OFFSET = 0x30  # source annotated RPGolMapObjBase::mTrans
MAX_TREES = 4096

# Original source code in Pack/RPSports/RPGolScene/RPGolFieldManager.cpp,
# public Rev1 split: load-hole-resources starts 0x80293008.
# Fingerprint the ENTIRE pointer arithmetic, constructor, counter, comparison
# and loop branch sequence, not a loose immediate occurrence elsewhere.
CODE_BASE = 0x80293008
CODE_FINGERPRINT = {
    0x0698: 0x9421FFE0,  # stwu r1,-32(r1)
    0x06BC: 0x7C7C1B78,  # mr r28,r3
    0x06E8: 0x801C0020,  # lwz r0,+0x20(r28)
    0x06EC: 0x7C60FA14,  # add r3,r0,r31
    0x06F0: 0x48002B4D,  # bl RPGolMapObjTree+0x0C
    0x06F4: 0x3BFF0054,  # addi r31,r31,+84
    0x06F8: 0x3BDE0001,  # addi r30,r30,+1
    0x06FC: 0x801C001C,  # lwz r0,+0x1c(r28)
    0x0700: 0x7C1E0000,  # cmpw r30,r0
    0x0704: 0x4180FFE4,  # blt -28 to +0x06e8
}
MIN_COORD = -10000000.0
MAX_COORD = 10000000.0


def check_source_tree_loop(word):
    """Fixed public executable addresses; return only pass/fail."""
    return all(word(CODE_BASE+offset) == expected
               for offset,expected in CODE_FINGERPRINT.items())


def finite_triplet(point):
    return (isinstance(point, tuple) and len(point)==3 and
            all(isinstance(v,(float,int)) and math.isfinite(v) and
                MIN_COORD < v < MAX_COORD for v in point))


def inspect_array(read_u32, read_xyz, guest_bank, base, count, tee, pin):
    """Pure synthetic-testable, index-scoped candidate tree translation audit.

    The source object +0x30 field is a candidate translation. Do not assume
    the object was initialized at this frame, is drawable, or is collision.
    """
    if type(count) is not int or not 3<=count<=MAX_TREES:
        raise ValueError("Source tree count out of bounds")
    if not guest_bank(base,count*TREE_SIZE,"MEM2"):
        raise ValueError("Source tree contiguous array outside MEM2")
    if not finite_triplet(tee) or not finite_triplet(pin):
        raise ValueError("Source tee/pin not finite")
    points=[]
    head_types=Counter()
    normal_nonzero=0
    pmp_links=0
    model_links=0
    for n in range(count):
        obj=base+n*TREE_SIZE
        vtable=read_u32(obj)
        if vtable == 0:
            head_types["zero"]+=1
        elif guest_bank(vtable,4,"MEM1"):
            head_types["mem1_pointer"]+=1
        elif guest_bank(vtable,4,"MEM2"):
            head_types["mem2_pointer"]+=1
        else:
            head_types["other_nonzero"]+=1
        model=read_u32(obj+4)
        pmp=read_u32(obj+8)
        model_links += int(bool(model and
                                (guest_bank(model,4,"MEM1") or guest_bank(model,4,"MEM2"))))
        pmp_links += int(bool(pmp and
                              (guest_bank(pmp,4,"MEM1") or guest_bank(pmp,4,"MEM2"))))
        point=read_xyz(obj+TRANS_OFFSET)
        points.append(point)
    valid = [p for p in points if finite_triplet(p)]
    if valid:
        spans=[round(max(p[j] for p in valid)-min(p[j] for p in valid),3)
               for j in range(3)]
        unique=len({tuple(round(v,3) for v in p) for p in valid})
        horiz_pin=[math.hypot(p[0]-pin[0],p[2]-pin[2]) for p in valid]
        horiz_tee=[math.hypot(p[0]-tee[0],p[2]-tee[2]) for p in valid]
        source_span=math.hypot(pin[0]-tee[0],pin[2]-tee[2])
        threshold=max(2500.0,source_span*4)
        near=sum(min(d1,d2)<=threshold for d1,d2 in zip(horiz_pin,horiz_tee))
        med_pin=round(statistics.median(horiz_pin),2)
        med_tee=round(statistics.median(horiz_tee),2)
    else:
        spans=[None,None,None]
        unique=near=0
        med_pin=med_tee=None
        threshold=max(2500.0, math.hypot(pin[0]-tee[0],pin[2]-tee[2])*4)
    # Non-physical candidate only: spatial spread is a sanity check, not
    # proof of model transform. Avoid requiring firstword to be an ABI vtable.
    plausible = (
        len(valid) == count and unique >= min(16,count//2)
        and near >= math.ceil(.70*count)
        and spans[0] > 10 and spans[2] > 10
    )
    report={
        "tree_objects_source_count":count,
        "source_proven_contiguous_stride_bytes":TREE_SIZE,
        "source_base_translation_offset_candidate":f"+0x{TRANS_OFFSET:02X}",
        "finite_translation_triplets":len(valid),
        "distinct_candidate_translations":unique,
        "coordinate_component_spans":spans,
        "near_source_tee_or_pin_count":near,
        "source_near_threshold_units":round(threshold,1),
        "median_horizontal_distance_from_tee":med_tee,
        "median_horizontal_distance_from_pin":med_pin,
        "object_firstword_buckets":dict(sorted(head_types.items())),
        "nonzero_bounded_model_pointer_candidates":model_links,
        "nonzero_bounded_pmp_pointer_candidates":pmp_links,
        "candidate_spatial_sanity_passed":plausible,
        "actual_tree_model_mesh_verified":False,
        "world_visual_alignment_verified":False,
        "collision_hitboxes_verified":False,
        "training_approved":False,
    }
    return report, tuple(points)


def float32(reader,addr):
    return struct.unpack(">f",reader.u32(addr).to_bytes(4,"big"))[0]


def vec(reader,addr):
    return tuple(float32(reader,addr+4*i) for i in range(3))


def run(archive:Path,captures:tuple[int,...]):
    if not captures or len(set(captures))!=len(captures) or any(n not in range(1,8) for n in captures):
        raise ValueError("Unsupported or duplicated source capture")
    originals=seven._check_archive(archive)
    rows=[]
    source_points=[]
    for capture in captures:
        with ExitStack() as stack:
            banks=[]
            for i,size in enumerate(seven.SIZE,1):
                path=seven.src._file(originals[capture],f"{capture}.{i}.raw",size)
                f=stack.enter_context(path.open("rb"))
                banks.append(stack.enter_context(mmap.mmap(
                    f.fileno(),0,access=mmap.ACCESS_READ)))
            reader=seven.roster.TwoBankReader(*banks)
            selected=seven._get(reader)
            field=selected["field"]
            count=reader.u32(field+0x1C)
            array=reader.u32(field+0x20)
            def word(pc):
                if not MEM1_START<=pc<=MEM1_START+len(banks[0])-4:
                    raise ValueError("PPC instruction outside source MEM1")
                return struct.unpack_from(">I",banks[0],pc-MEM1_START)[0]
            if not check_source_tree_loop(word):
                raise ValueError("Source tree loop bytes changed")
            if seven.roster._bank(array,count*TREE_SIZE)!="MEM2":
                raise ValueError("Source tree array bounds not qualified")
            tee=vec(reader,selected["start_obj"]+0x30)
            pin=vec(reader,selected["pin_obj"]+0x30)
            def bank(address,length,name):
                return seven.roster._bank(address,length)==name
            report,pts=inspect_array(reader.u32,lambda a:vec(reader,a),
                                     bank,array,count,tee,pin)
            rows.append({"capture":capture,"status":(
                "TREE_TRANSLATION_CANDIDATES_CONSISTENT"
                if report["candidate_spatial_sanity_passed"]
                else "TREE_TRANSLATION_LAYOUT_UNVERIFIED"),**report})
            source_points.append(pts)
    seven._check_archive(archive)
    stable=(all(len(p)==len(source_points[0]) for p in source_points) and
            all(p==source_points[0] for p in source_points[1:]))
    return {
        "kind":"P0_SOURCE_PROVEN_GOLF_TREE_STRIDE_PRIVATE",
        "status":"SOURCE_LOOP_VERIFIED",
        "original_archive_sha_verified":True,
        "game_scene_source_gated":True,
        "private_guest_ppc_tree_loop_exact_match":True,
        "source_84_byte_tree_stride_verified":True,
        "candidate_positions_bitwise_stable_across_selected_captures":(
            stable if len(captures)>1 else None),
        "records":rows,
        "actual_3d_tree_mesh_verified":False,
        "training_approved":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--captures",type=int,nargs="+",choices=range(1,8),default=[7])
    a=p.parse_args(argv)
    try:
        print(json.dumps(run(a.archive,tuple(a.captures)),sort_keys=True,
                         separators=(",",":"),allow_nan=False))
        return 0
    except (ValueError,OSError,TypeError,KeyError,IndexError,OverflowError,
            AttributeError,struct.error):
        print('{"kind":"P0_SOURCE_PROVEN_GOLF_TREE_STRIDE_PRIVATE",'
              '"status":"ABSTAIN_SOURCE_OR_TREE_LOOP","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
