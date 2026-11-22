#!/usr/bin/env python3
"""Original Wii Sports Golf exact triangle proximity: 94 trees / tee / pin.

Uses the original source-qualified 2498 KCL prisms and 94 x 0x54
tree objects, plus the native 7-pair SHA / scene / tree-loop PPC gates.
Unlike earlier triangle AABB broadphase checks this calculates:
 - exact closest-point distance to reconstructed 3D triangles,
 - exact horizontal distance to their XZ projected triangles,
 - vertical clearance to XZ-overlapping near-horizontal triangles.
The 2D projected vertical triangles may degenerate to line segments.

The game KCL *resource-to-ball* relationship and octree reachability
are STILL NOT established. Even exact proximity does not mean a physical
tree collider, gameplay hitbox radius, or a collision response. All
output is aggregate: NO original positions, triangles, pointers,
native code bytes, source game assets, writes or training approval.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from collections import Counter
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
SEARCH_WINDOWS=(5.,25.,50.,100.,200.,500.)
GROUPS=("all_faces","near_horizontal","near_vertical")


def dot(u,v):
    return sum(a*b for a,b in zip(u,v))


def sub(u,v):
    return tuple(a-b for a,b in zip(u,v))


def distance_sq(u,v):
    return sum((a-b)**2 for a,b in zip(u,v))


def segment_sq(p,a,b):
    direction=sub(b,a)
    denom=dot(direction,direction)
    if denom<=1e-20:
        return distance_sq(p,a)
    t=max(0.,min(1.,dot(sub(p,a),direction)/denom))
    q=tuple(a[i]+t*direction[i] for i in range(len(a)))
    return distance_sq(p,q)


def triangle_sq_3d(p,a,b,c):
    """Exact point-to-closed-triangle squared distance (Ericson regions)."""
    ab=sub(b,a)
    ac=sub(c,a)
    ap=sub(p,a)
    if sum(z*z for z in broad.cross(ab,ac))<1e-18:
        return min(segment_sq(p,a,b),segment_sq(p,b,c),segment_sq(p,c,a))
    d1=dot(ab,ap)
    d2=dot(ac,ap)
    if d1<=0. and d2<=0.:
        return distance_sq(p,a)
    bp=sub(p,b)
    d3=dot(ab,bp)
    d4=dot(ac,bp)
    if d3>=0. and d4<=d3:
        return distance_sq(p,b)
    vc=d1*d4-d3*d2
    if vc<=0. and d1>=0. and d3<=0.:
        v=d1/(d1-d3)
        q=tuple(a[i]+v*ab[i] for i in range(3))
        return distance_sq(p,q)
    cp=sub(p,c)
    d5=dot(ab,cp)
    d6=dot(ac,cp)
    if d6>=0. and d5<=d6:
        return distance_sq(p,c)
    vb=d5*d2-d1*d6
    if vb<=0. and d2>=0. and d6<=0.:
        w=d2/(d2-d6)
        q=tuple(a[i]+w*ac[i] for i in range(3))
        return distance_sq(p,q)
    va=d3*d6-d5*d4
    if va<=0. and (d4-d3)>=0. and (d5-d6)>=0.:
        t=(d4-d3)/((d4-d3)+(d5-d6))
        q=tuple(b[i]+t*(c[i]-b[i]) for i in range(3))
        return distance_sq(p,q)
    denom=va+vb+vc
    if abs(denom)<=1e-20:
        return min(segment_sq(p,a,b),segment_sq(p,b,c),segment_sq(p,c,a))
    inv=1./denom
    v=vb*inv
    w=vc*inv
    q=tuple(a[i]+v*ab[i]+w*ac[i] for i in range(3))
    return distance_sq(p,q)


def cross2(u,v):
    return u[0]*v[1]-u[1]*v[0]


def project_barycentric(p,a,b,c):
    """Return barycentric XZ weights only for nondegenerate projected face."""
    ab=sub(b,a)
    ac=sub(c,a)
    det=cross2(ab,ac)
    if abs(det)<1e-10:
        return None
    ap=sub(p,a)
    v=cross2(ap,ac)/det
    w=cross2(ab,ap)/det
    u=1.-v-w
    return (u,v,w)


def horizontal_projected_sq(p,triangle):
    a,b,c=triangle
    axz=(a[0],a[2])
    bxz=(b[0],b[2])
    cxz=(c[0],c[2])
    xz=(p[0],p[2])
    weights=project_barycentric(xz,axz,bxz,cxz)
    if weights is not None and min(weights)>=-1e-9:
        return 0.
    return min(segment_sq(xz,axz,bxz),
               segment_sq(xz,bxz,cxz),
               segment_sq(xz,cxz,axz))


def ground_clearance(p,triangle):
    """Signed Y-point minus interpolated triangle Y when XZ is inside."""
    a,b,c=triangle
    weights=project_barycentric(
        (p[0],p[2]),(a[0],a[2]),(b[0],b[2]),(c[0],c[2]))
    if weights is None or min(weights)<-1e-8:
        return None
    y=sum(w*v[1] for w,v in zip(weights,(a,b,c)))
    return p[1]-y


def stats(numbers):
    if not numbers:
        return None
    vals=sorted(numbers)
    return {
        "min":round(vals[0],3),
        "median":round(statistics.median(vals),3),
        "max":round(vals[-1],3),
    }


def nearest_profiles(points,faces):
    """Compute independent minima for each original point, no per-point output."""
    if not faces:
        return None
    minima_2d=[]
    minima_3d=[]
    nearest_attr=Counter()
    gap_2d=[]
    gap_3d=[]
    for p in points:
        min2=float("inf")
        min3=float("inf")
        lb2=float("inf")
        lb3=float("inf")
        closest_flag=None
        for t in faces:
            bounds2=broad.projected_bbox_lower_bound(p,t)
            bounds3=math.sqrt(
                bounds2*bounds2 +
                max(t[4]-p[1],0.,p[1]-t[5])**2)
            lb2=min(lb2,bounds2)
            lb3=min(lb3,bounds3)
            if bounds2<min2:
                d2=math.sqrt(horizontal_projected_sq(p,t[8]))
                min2=min(min2,d2)
            if bounds3<min3:
                d3=math.sqrt(triangle_sq_3d(p,*t[8]))
                if d3<min3:
                    min3=d3
                    closest_flag=t[7]
        minima_2d.append(min2)
        minima_3d.append(min3)
        gap_2d.append(min2-lb2)
        gap_3d.append(min3-lb3)
        if closest_flag is not None:
            nearest_attr[closest_flag]+=1
    return {
        "nearest_actual_triangle_xz_projection_distance_source_units":stats(minima_2d),
        "nearest_actual_triangle_3d_distance_source_units":stats(minima_3d),
        "actual_minus_triangle_aabb_lower_bound_xz_source_units":stats(gap_2d),
        "actual_minus_triangle_aabb_lower_bound_3d_source_units":stats(gap_3d),
        "points_within_actual_xz_triangle_windows":{
            str(int(w)):sum(d<=w for d in minima_2d) for w in SEARCH_WINDOWS},
        "points_within_actual_3d_triangle_windows":{
            str(int(w)):sum(d<=w for d in minima_3d) for w in SEARCH_WINDOWS},
        "nearest_actual_3d_prism_flags":{
            "0x"+format(k,"04X"):v for k,v in sorted(nearest_attr.items())},
        "original_geometry_is_active_ball_collider_verified":False,
        "gameplay_tree_hitbox_radius_verified":False,
    }


def ground_profile(points,near_horizontal):
    if not near_horizontal:
        return None
    values=[]
    covered=0
    for p in points:
        best=None
        for t in near_horizontal:
            if broad.projected_bbox_lower_bound(p,t)>0.0001:
                continue
            dy=ground_clearance(p,t[8])
            if dy is not None and (best is None or abs(dy)<abs(best)):
                best=dy
        if best is not None:
            covered+=1
            values.append(best)
    return {
        "points_with_xz_inside_any_near_horizontal_face":covered,
        "nearest_surface_signed_y_clearance_source_units":stats(values),
        "points_with_signed_clearance_absolute_at_most_5":sum(abs(x)<=5 for x in values),
        "source_point_on_triangle_does_not_prove_active_collision":True,
    }


def summarize(trees,controls,faces):
    if len(trees)!=94 or len(controls)!=2 or len(faces)!=2498:
        raise ValueError("Expected 94 trees, 2 controls and 2498 prisms")
    for p in [*trees,*controls]:
        if len(p)!=3 or not all(math.isfinite(a) and abs(a)<1e7 for a in p):
            raise ValueError("Bad source point")
    for t in faces:
        if len(t)!=9 or len(t[8])!=3:
            raise ValueError("KCL prism geometry missing")
        if any(not all(math.isfinite(x) and abs(x)<1e7 for x in v)
               for v in t[8]):
            raise ValueError("Invalid triangle vertex")
    categorized={
        "all_faces":faces,
        "near_horizontal":[t for t in faces if t[6]>=0.8],
        "near_vertical":[t for t in faces if t[6]<=0.4],
    }
    reports={}
    for name,selected in categorized.items():
        reports[name]={
            "face_count":len(selected),
            "tree_nearest_actual_triangle":nearest_profiles(trees,selected),
            "tee_nearest_actual_triangle":nearest_profiles([controls[0]],selected),
            "pin_nearest_actual_triangle":nearest_profiles([controls[1]],selected),
        }
    horizontal=categorized["near_horizontal"]
    return {
        "source_94_tree_records":len(trees),
        "source_2498_kcl_prism_faces":len(faces),
        "actual_triangle_distance_profiles":reports,
        "terrain_vertical_surface_clearance":{
            "trees":ground_profile(trees,horizontal),
            "tee":ground_profile([controls[0]],horizontal),
            "pin":ground_profile([controls[1]],horizontal),
        },
        "actual_triangle_proximity_is_not_collision_ownership":True,
        "native_kcl_octree_reachability_verified":False,
        "native_tree_collider_shape_verified":False,
        "ball_contact_response_verified":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    if capture not in range(1,8):
        raise ValueError("Original capture must be 1..7")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            file=seven.src._file(folders[capture],f"{capture}.{i}.raw",size)
            h=stack.enter_context(file.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(h.fileno(),0,access=mmap.ACCESS_READ)))
        reader=seven.roster.TwoBankReader(*banks)
        source=seven._get(reader)
        fm=source["field"]
        count=reader.u32(fm+0x1C)
        base=reader.u32(fm+0x20)
        if count!=94 or seven.roster._bank(base,94*84)!="MEM2":
            raise ValueError("Original source tree array not qualified")
        def word(pc):
            if not MEM1<=pc<=MEM1+len(banks[0])-4:
                raise ValueError("Original code outside MEM1 source")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        if not native.tree_loop_source_gated(word):
            raise ValueError("Original 94x84 source PPC loop mismatch")
        trees=[broad.vec3(reader,base+i*84+0x30) for i in range(94)]
        controls=[broad.vec3(reader,source[k]+0x30)
                  for k in ("start_obj","pin_obj")]
        faces=broad.scan_exact_candidate(banks,include_vertices=True)
        report=summarize(trees,controls,faces)
    seven._check_archive(archive)
    return {
        "kind":"P0_GOLF_TREE_EXACT_TRIANGLE_DISTANCE_SOURCE_AUDIT",
        "status":"ORIGINAL_TREE_KCL_ACTUAL_TRIANGLE_PROXIMITY",
        "capture":capture,
        "original_sha_scene_94tree_native_loop_gated":True,
        "unique_2498_kcl_flag_histogram_qualified":True,
        **report,
    }


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive",required=True,type=Path)
    ap.add_argument("--capture",type=int,choices=range(1,8),default=7)
    a=ap.parse_args(argv)
    try:
        print(json.dumps(run(a.archive,a.capture),sort_keys=True,
                         separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,IndexError,OverflowError,TypeError,
            AttributeError,KeyError,ZeroDivisionError,struct.error):
        print('{"status":"ABSTAIN_KCL_ACTUAL_TRIANGLE_DISTANCE","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
