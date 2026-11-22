#!/usr/bin/env python3
"""Original RSPE01 Rev1 source tree-vs-KCL coordinate frame diagnostics.

The earlier vertically-filtered 94-tree/2498-prism audit returned zero
qualified faces within XZ 200 source units. Distinguish frame mismatch,
normal selection and vertical-elevation filtering by testing ALL KCL
triangles plus tee/pin positive controls. Every distance here is only a
3D or XZ AABB LOWER BOUND; it is NOT actual point/triangle distance or
a collision hitbox. Do NOT derive physical radii from search windows.

Strict original 7-pair SHA, scene source, 94-tree PPC 84-byte loop and
unique exact 2498-KCL-prism histogram. Aggregate output only: no
individual XYZ, KCL geometry, heap/code words, game writes or training.
"""
from __future__ import annotations

import argparse
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

MEM1=0x80000000
SEARCH_WINDOWS=(25.0,50.0,100.0,200.0,500.0,1000.0)
CATEGORIES=("all_faces","near_vertical","near_horizontal")


def bbox_distance_3d(p,t):
    """Euclidean point-to-triangle-AABB lower bound, NOT face distance."""
    dx=max(t[0]-p[0],0.0,p[0]-t[1])
    dy=max(t[4]-p[1],0.0,p[1]-t[5])
    dz=max(t[2]-p[2],0.0,p[2]-t[3])
    return math.sqrt(dx*dx+dy*dy+dz*dz)


def axis_gap(lo_a,hi_a,lo_b,hi_b):
    return max(lo_a-hi_b,lo_b-hi_a,0.0)


def profile(points,triangles):
    if not triangles:
        return None
    near_xz=[]
    near_xyz=[]
    for p in points:
        near_xz.append(min(broad.projected_bbox_lower_bound(p,t) for t in triangles))
        near_xyz.append(min(bbox_distance_3d(p,t) for t in triangles))
    return {
        "nearest_triangle_xz_aabb_lower_bound_source_units":{
            "min":round(min(near_xz),2),
            "median":round(statistics.median(near_xz),2),
            "max":round(max(near_xz),2),
        },
        "nearest_triangle_3d_aabb_lower_bound_source_units":{
            "min":round(min(near_xyz),2),
            "median":round(statistics.median(near_xyz),2),
            "max":round(max(near_xyz),2),
        },
        "point_counts_within_xz_lower_bound_windows":{
            str(int(w)):sum(d<=w for d in near_xz) for w in SEARCH_WINDOWS},
        "point_counts_within_3d_lower_bound_windows":{
            str(int(w)):sum(d<=w for d in near_xyz) for w in SEARCH_WINDOWS},
        "aabb_is_true_triangle_distance":False,
    }


def relative_range_diagnostics(trees,tris):
    """Only public aggregate gaps, never exact source minima/maxima."""
    a={}
    for axis,lo,hi in (("x",0,1),("y",4,5),("z",2,3)):
        mlo=min(t[lo] for t in tris)
        mhi=max(t[hi] for t in tris)
        tlo=min(p[{"x":0,"y":1,"z":2}[axis]] for p in trees)
        thi=max(p[{"x":0,"y":1,"z":2}[axis]] for p in trees)
        a[axis]={
            "tree_span_source_units":round(thi-tlo,2),
            "kcl_span_source_units":round(mhi-mlo,2),
            "tree_kcl_aabb_axis_gap_source_units":round(axis_gap(tlo,thi,mlo,mhi),2),
            "ranges_overlap":tlo<=mhi and thi>=mlo,
        }
    return a


def summarize(trees,controls,tris):
    if (len(trees)!=broad.COUNT or len(controls)!=2 or
            len(tris)!=broad.KCL_PRISMS):
        raise ValueError("Expected 94 verified trees, 2 tee-pin controls, 2498 KCL prisms")
    pts=[*trees,*controls]
    if any(len(p)!=3 or not all(math.isfinite(v) and abs(v)<1e7 for v in p)
           for p in pts):
        raise ValueError("Invalid source point geometry")
    if any(len(t)!=8 or any(not math.isfinite(v) or abs(v)>1e7 for v in t[:7])
           or t[0]>t[1] or t[2]>t[3] or t[4]>t[5] for t in tris):
        raise ValueError("Invalid source face AABBs")
    by_cat={
        "all_faces":tris,
        "near_vertical":[t for t in tris if t[6]<=broad.ABS_FACE_Y_MAX],
        "near_horizontal":[t for t in tris if t[6]>=0.80],
    }
    cats={}
    for cat,selected in by_cat.items():
        cats[cat]={
            "prism_count":len(selected),
            "trees":profile(trees,selected),
            "tee_and_pin_controls":[profile([p],selected) for p in controls],
        }
    # Remove height filter on vertical faces, then independently reapply it
    # per tree to expose why the previous strict test found zero matches.
    vert=by_cat["near_vertical"]
    cascade={}
    for window in (50.0,200.0,500.0):
        direct=[sum(broad.projected_bbox_lower_bound(p,t)<=window for t in vert)
                for p in trees]
        raised=[sum(
            broad.projected_bbox_lower_bound(p,t)<=window and t[5]>=p[1]
            for t in vert) for p in trees]
        cascade[str(int(window))]={
            "tree_count_near_vertical_no_elevation_gate":sum(v>0 for v in direct),
            "tree_count_near_vertical_with_original_elevation_gate":sum(v>0 for v in raised),
        }
    all_control=cats["all_faces"]["tee_and_pin_controls"]
    close=[c is not None and
           c["nearest_triangle_3d_aabb_lower_bound_source_units"]["min"]<=25.
           for c in all_control]
    return {
        "source_tree_count":len(trees),
        "candidate_kcl_face_count":len(tris),
        "source_tree_to_kcl_bbox_axis_alignment":relative_range_diagnostics(trees,tris),
        "face_category_profiles":cats,
        "vertical_face_filter_cascade":cascade,
        "tee_pin_both_have_3d_bbox_lower_bound_at_most_25":all(close),
        "tee_pin_check_establishes_frame_alignment":False,
        "face_bbox_distance_is_only_lower_bound":True,
        "candidate_kcl_in_active_golf_ball_octree_verified":False,
        "tree_hitbox_geometry_verified":False,
        "native_ball_tree_response_verified":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    if capture not in range(1,8):
        raise ValueError("Unsupported original capture")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for idx,size in enumerate(seven.SIZE,1):
            p=seven.src._file(folders[capture],f"{capture}.{idx}.raw",size)
            f=stack.enter_context(p.open("rb"))
            banks.append(stack.enter_context(mmap.mmap(
                f.fileno(),0,access=mmap.ACCESS_READ)))
        reader=seven.roster.TwoBankReader(*banks)
        selected=seven._get(reader)
        field=selected["field"]
        count=reader.u32(field+0x1C)
        base=reader.u32(field+0x20)
        if count!=broad.COUNT or seven.roster._bank(base,count*broad.STRIDE)!="MEM2":
            raise ValueError("Original source tree array not available")
        def word(pc):
            if pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Native PPC code outside MEM1 source")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        if not native.tree_loop_source_gated(word):
            raise ValueError("Native source 94-tree loop PPC mismatch")
        trees=[broad.vec3(reader,base+i*broad.STRIDE+0x30)
               for i in range(broad.COUNT)]
        controls=[broad.vec3(reader,selected[k]+0x30)
                  for k in ("start_obj","pin_obj")]
        candidate=broad.scan_exact_candidate(banks)
        result=summarize(trees,controls,candidate)
    seven._check_archive(archive)
    return {
        "kind":"P0_SOURCE_TREE_KCL_UNFILTERED_FRAME_DIAGNOSTICS",
        "status":"SOURCE_KCL_FRAME_FILTERS_DIAGNOSED",
        "capture":capture,
        "original_sha_scene_tree_stride_and_unique_kcl_gated":True,
        **result,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    a=p.parse_args(argv)
    try:
        print(json.dumps(run(a.archive,a.capture),sort_keys=True,
                         separators=(",",":"),allow_nan=False))
        return 0
    except (ValueError,OSError,OverflowError,TypeError,KeyError,IndexError,
            AttributeError,struct.error):
        print('{"status":"ABSTAIN_TREE_KCL_FRAME_DIAGNOSTIC","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
