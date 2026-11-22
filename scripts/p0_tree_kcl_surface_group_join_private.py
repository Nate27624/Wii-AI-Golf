#!/usr/bin/env python3
"""OGWS original 94 trees: resource-word groups vs exact ground KCL faces.

Source-qualified SHA/scene/94x84 field manager PPC tree array and unique
original 2498-prism candidate KCL. Joins individual tree-vertex and
field+4/+8 WORD GROUPS locally; outputs only aggregate contingency matrix,
not original pointers, tree coordinates, KCL vertices, addresses or ROM words.

The observed 72/22 raw word grouping and 72 OOB /22 rough nearest-face
counts are marginal observations only. This probe determines WHETHER THEY
COINCIDE PER TREE. Even perfect association does NOT establish model
species, tree colliders, active ball KCL octree or collision response.
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

sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as seven
import p0_tree_hitbox_source_callgraph_private as native
import p0_tree_kcl_spatial_broadphase_private as broad
import p0_tree_kcl_exact_triangle_distance_private as exact

MEM1=0x80000000
COUNT=94
STRIDE=84
EXPECTED_SURFACE_COUNTS={2:22,4:72}


def nearest_surface(point,faces):
    """Actual nearest 3D triangle; geometry used locally, never exported."""
    best=math.inf
    flag=None
    face_no=None
    for i,face in enumerate(faces):
        lo=broad.projected_bbox_lower_bound(point,face)
        bound_sq=lo*lo+max(face[4]-point[1],0.,point[1]-face[5])**2
        if bound_sq>=best:
            continue
        d=exact.triangle_sq_3d(point,*face[8])
        if d<best:
            best=d
            flag=face[7]
            face_no=i
    if flag is None or not math.isfinite(best):
        raise ValueError("No finite original KCL triangle")
    return flag,math.sqrt(best),face_no


def group_rows(rows):
    """rows = (raw+4, raw+8, scale xyz, nearest KCL flag, distance).

    Raw source words only ever used for in-memory exact equality, and
    never published. Group IDs determined by descending frequency
    and then FIRST observed source row for deterministic ties.
    """
    if len(rows)!=COUNT:
        raise ValueError("Original source tree count mismatch")
    if any(len(row)!=5 or len(row[2])!=3 or
           not all(math.isfinite(x) for x in (*row[2],row[4])) or
           row[4]<0 for row in rows):
        raise ValueError("Unqualified source tree member/geometry")
    counts=Counter((x[0],x[1]) for x in rows)
    if len(counts)!=2 or sorted(counts.values(),reverse=True)!=[72,22]:
        raise ValueError("Original 72/22 two-resource group assumption failed")
    groups=sorted(counts,key=lambda k:(-counts[k],next(i for i,r in enumerate(rows) if (r[0],r[1])==k)))
    categories=Counter(row[3] for row in rows)
    if categories != Counter(EXPECTED_SURFACE_COUNTS):
        raise ValueError("Source tree terrain-class counts changed")
    table=[]
    for i,key in enumerate(groups,1):
        members=[r for r in rows if (r[0],r[1])==key]
        histogram=Counter(r[3] for r in members)
        uniform=sum(
            math.isclose(r[2][0],r[2][1],rel_tol=1e-5,abs_tol=1e-5)
            and math.isclose(r[2][1],r[2][2],rel_tol=1e-5,abs_tol=1e-5)
            for r in members)
        d=[r[4] for r in members]
        table.append({
            "anonymous_source_word_group":"larger" if i==1 else "smaller",
            "tree_count":len(members),
            "nearest_ground_kcl_prism_flag_counts":{
                "0x"+format(k,"04X"):histogram[k] for k in sorted(categories)
            },
            "uniform_xyz_scale_count":uniform,
            "nonuniform_xyz_scale_count":len(members)-uniform,
            "nearest_actual_3d_triangle_distance_source_units":{
                "min":round(min(d),3),
                "median":round(statistics.median(d),3),
                "max":round(max(d),3),
            },
        })
    # If perfect partition, the 72-group will be all 0x0004 OOB
    # and 22-group will be all 0x0002 rough. This is still
    # material association, NOT causal or physical hitbox proof.
    perfect=(
        table[0]["nearest_ground_kcl_prism_flag_counts"]["0x0004"]==72
        and table[1]["nearest_ground_kcl_prism_flag_counts"]["0x0002"]==22
    )
    return {
        "source_tree_count":COUNT,
        "original_94_source_model_plus4_and_mapobj_plus8_word_pair_groups":2,
        "source_tree_group_rows":table,
        "per_tree_group_to_surface_category_correspondence_exact":perfect,
        "tree_model_class_identity_proven":False,
        "tree_collision_object_geometry_proven":False,
        "native_ball_response_proven":False,
        "training_approved":False,
    }


def analyze(archive:Path,capture:int):
    if capture not in range(1,8):
        raise ValueError("Only original seven capture phases")
    folder=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            path=seven.src._file(folder[capture],f"{capture}.{i}.raw",size)
            h=stack.enter_context(path.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(h.fileno(),0,access=mmap.ACCESS_READ)))
        reader=seven.roster.TwoBankReader(*banks)
        source=seven._get(reader)
        fm=source["field"]
        count=reader.u32(fm+0x1C)
        ptr=reader.u32(fm+0x20)
        if count!=COUNT or seven.roster._bank(ptr,COUNT*STRIDE)!="MEM2":
            raise ValueError("Original 94x84 tree owner invalid")
        def word(pc):
            if not MEM1<=pc<=MEM1+len(banks[0])-4:
                raise ValueError("Source PPC out of bounds")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        if not native.tree_loop_source_gated(word):
            raise ValueError("Original verified source tree PPC loop missing")
        faces=broad.scan_exact_candidate(banks,include_vertices=True)
        rows=[]
        for i in range(COUNT):
            obj=ptr+i*STRIDE
            pos=broad.vec3(reader,obj+0x30)
            scale=broad.vec3(reader,obj+0x3C)
            flag,dist,_=nearest_surface(pos,faces)
            rows.append((reader.u32(obj+4),reader.u32(obj+8),
                         scale,flag,dist))
        report=group_rows(rows)
    seven._check_archive(archive)
    return {
        "kind":"P0_SOURCE_TREE_RESOURCE_GROUP_KCL_SURFACE_JOIN",
        "status":"SOURCE_TREE_SURFACE_PER_OBJECT_CROSSTAB",
        "capture":capture,
        "native_sha_scene_tree_loop_and_unique_kcl_qualified":True,
        "nearest_ground_surface_rough_0x0002_and_oob_0x0004_source_backed":True,
        **report,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",required=True,type=Path)
    parser.add_argument("--capture",choices=range(1,8),type=int,default=7)
    a=parser.parse_args(argv)
    try:
        print(json.dumps(analyze(a.archive,a.capture),sort_keys=True,
                         separators=(",",":"),allow_nan=False))
        return 0
    except (ValueError,OSError,IndexError,OverflowError,TypeError,
            AttributeError,KeyError,struct.error):
        print('{"status":"ABSTAIN_TREE_SURFACE_RESOURCE_JOIN","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
