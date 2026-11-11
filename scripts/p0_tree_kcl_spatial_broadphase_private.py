#!/usr/bin/env python3
"""Original Wii Sports Golf tree-centre vs candidate KCL triangle spatial audit.

READ-ONLY original seven-phase SHA/source/scene/84-byte tree-loop gated.
Reconstruct original game KCL faces using native prism vertex/normal indices,
then compare source 94 tree +0x30 centres against candidate vertical/elevated
KCL triangles using XZ *AABB LOWER BOUNDS* ONLY. This is a spatial
coincidence/falsification test, NEVER a collision shape or hitbox radius.

No private tree/KCL XYZ, code bytes, model art, native addresses or
individual-coordinate rows in output; all results are aggregate. No game
writes, Dolphin actions, physics labels or training approval.
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

MEM1=0x80000000
STRIDE=84
COUNT=94
KCL_PRISMS=2498
# These exact counts are previous operator-qualified original KCL attributes.
EXPECTED_FLAGS={1:208,2:585,3:301,4:508,5:44,6:478,7:7,9:99,12:268}
KCL_PREFIXES=(0x38,0x3C,0x40,0x44,0x48,0x4C,0x50,0x60,0x80)
HORIZONTAL_WINDOWS=(25.0,50.0,100.0,200.0)
ELEVATION_MINIMUMS=(0.0,25.0,75.0)
ABS_FACE_Y_MAX=0.40
MAX_CANDIDATES=2


def dprod(a,b):
    return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]


def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def norm2(a):
    return dprod(a,a)


def f32(rd,addr):
    return struct.unpack(">f",rd.u32(addr).to_bytes(4,"big"))[0]


def vec3(rd,addr):
    return tuple(f32(rd,addr+4*j) for j in range(3))


def parse_candidate(bank,offset,*,required_prisms=KCL_PRISMS):
    """Strict KCL prism parser, returns (tri bounds/normals/attr, histogram).

    KCL "height" is part of triangle reconstruction, not tree vertical size.
    The candidate header uses KCL internal positions; origin transforms and
    octree active ownership are *not* validated by this function.
    """
    if offset<0 or offset%4 or offset+0x3C>len(bank):
        return None
    try:
        po,no,pr,octo=struct.unpack_from(">4I",bank,offset)
        ps=pr+16
        if not (0x38<=po<=0x1000 and all(z%4==0 for z in (po,no,pr,octo))
                and po+36<=no and no+48<=ps
                and ps+16*3<=octo and octo<=32*1024*1024
                and offset+octo+4<=len(bank)):
            return None
        nverts=(no-po)//12
        nnormals=(ps-no)//12
        nprisms=(octo-ps)//16
        if not (3<=nverts<=65535 and 4<=nnormals<=65535
                and nprisms==required_prisms):
            return None
        thickness=struct.unpack_from(">f",bank,offset+0x10)[0]
        kcl_origin=struct.unpack_from(">fff",bank,offset+0x14)
        shifts=struct.unpack_from(">3I",bank,offset+0x2C)
        if not (math.isfinite(thickness) and 0<thickness<100000
                and all(math.isfinite(v) and abs(v)<1e7 for v in kcl_origin)
                and all(v<32 for v in shifts)):
            return None
        cache_vert={}
        cache_normal={}
        tris=[]
        counts=Counter()
        for i in range(nprisms):
            height,vi,fi,na,nb,nc,attr=struct.unpack_from(
                ">f6H",bank,offset+ps+16*i)
            if not (math.isfinite(height) and 1e-8<height<1e7
                    and vi<nverts and max(fi,na,nb,nc)<nnormals):
                return None
            if vi not in cache_vert:
                p=struct.unpack_from(">fff",bank,offset+po+vi*12)
                if any(not math.isfinite(v) or abs(v)>1e7 for v in p):
                    return None
                cache_vert[vi]=p
            for j in (fi,na,nb,nc):
                if j not in cache_normal:
                    v=struct.unpack_from(">fff",bank,offset+no+j*12)
                    if not all(math.isfinite(a) for a in v) or not 0.7<norm2(v)<1.3:
                        return None
                    cache_normal[j]=v
            face,ea,eb,ec=(cache_normal[j] for j in (fi,na,nb,nc))
            va=cross(ea,face)
            vb=cross(eb,face)
            da=dprod(va,ec)
            db=dprod(vb,ec)
            if not all(math.isfinite(v) for v in (da,db)) or abs(da)<1e-7 or abs(db)<1e-7:
                return None
            p=cache_vert[vi]
            q=tuple(p[j]+vb[j]*(height/db) for j in range(3))
            r=tuple(p[j]+va[j]*(height/da) for j in range(3))
            if not all(math.isfinite(x) and abs(x)<1e7 for pt in (q,r) for x in pt):
                return None
            area=cross(tuple(q[j]-p[j] for j in range(3)),
                       tuple(r[j]-p[j] for j in range(3)))
            if not 1e-12<norm2(area)<1e26:
                return None
            points=(p,q,r)
            tris.append((
                min(t[0] for t in points),max(t[0] for t in points),
                min(t[2] for t in points),max(t[2] for t in points),
                min(t[1] for t in points),max(t[1] for t in points),
                abs(face[1]),attr))
            counts[attr]+=1
        return tris,dict(counts)
    except (ValueError,IndexError,OverflowError,struct.error,ZeroDivisionError):
        return None


def scan_exact_candidate(banks):
    """Locate exactly one original 2498-prism histogram among MEM1/MEM2."""
    matches=[]
    for bank in banks:
        for prefix in KCL_PREFIXES:
            mark=struct.pack(">I",prefix)
            at=-1
            while True:
                at=bank.find(mark,at+1)
                if at<0:
                    break
                if at%4:
                    continue
                parsed=parse_candidate(bank,at)
                if parsed and parsed[1]==EXPECTED_FLAGS:
                    matches.append(parsed[0])
                    if len(matches)>=MAX_CANDIDATES:
                        raise ValueError("Ambiguous original candidate KCL dataset")
    if len(matches)!=1:
        raise ValueError("No unique previously source-typed KCL geometry")
    return matches[0]


def projected_bbox_lower_bound(point,t):
    """XZ axis-aligned bounding-box DISTANCE LOWER BOUND, not triangle contact."""
    x,_,z=point
    xmin,xmax,zmin,zmax=t[:4]
    dx=max(xmin-x,0.0,x-xmax)
    dz=max(zmin-z,0.0,z-zmax)
    return math.hypot(dx,dz)


def contacts_lower_bound(point,triangles,*,face_limit=ABS_FACE_Y_MAX):
    """Count broad spatial coincidences by window and above-centre height.

    A positive count does NOT prove the triangle actually intersects
    the projected circle, let alone a tree hitbox or active KCL octree.
    """
    result={}
    for radius in HORIZONTAL_WINDOWS:
        for min_elevation in ELEVATION_MINIMUMS:
            hits=Counter()
            for t in triangles:
                if t[6]>face_limit or t[5]-point[1]<min_elevation:
                    continue
                if projected_bbox_lower_bound(point,t)<=radius:
                    hits[t[7]]+=1
            result[(radius,min_elevation)]=hits
    return result


def summarize(trees,triangles,controls):
    if len(trees)!=COUNT or len(controls)!=2 or len(triangles)!=KCL_PRISMS:
        raise ValueError("Expected exactly 94 source trees / 2 controls / 2498 faces")
    allpoints=[*trees,*controls]
    if not all(len(p)==3 and all(math.isfinite(x) and abs(x)<1e7 for x in p) for p in allpoints):
        raise ValueError("Unbounded coordinate components")
    vertical=[tri for tri in triangles if tri[6]<=ABS_FACE_Y_MAX]
    tree_hits=[contacts_lower_bound(p,vertical) for p in trees]
    control_hits=[contacts_lower_bound(p,vertical) for p in controls]
    profiles=[]
    for radius in HORIZONTAL_WINDOWS:
        for elev in ELEVATION_MINIMUMS:
            key=(radius,elev)
            nums=[sum(h[key].values()) for h in tree_hits]
            ctrl=[sum(h[key].values()) for h in control_hits]
            hist=Counter()
            for h in tree_hits:
                hist.update(h[key])
            profiles.append({
                "xz_aabb_lower_bound_window_source_units":radius,
                "face_max_height_above_tree_centre_min_source_units":elev,
                "trees_with_one_or_more_candidate_vertical_faces":sum(n>0 for n in nums),
                "trees_with_five_or_more_candidate_vertical_faces":sum(n>=5 for n in nums),
                "median_candidate_faces_per_tree":statistics.median(nums),
                "max_candidate_faces_per_tree":max(nums),
                "tee_and_pin_control_face_counts":ctrl,
                "candidate_flags_tallied_with_repetition":{
                    "0x"+format(k,"04X"):v for k,v in sorted(hist.items())},
                "true_triangle_distance_verified":False,
                "contact_volume_verified":False,
            })
    return {
        "source_trees":len(trees),
        "kcl_prism_triangles":len(triangles),
        "vertical_face_normal_abs_y_threshold":ABS_FACE_Y_MAX,
        "candidate_vertical_faces":len(vertical),
        "spatial_window_profiles":profiles,
        "same_coordinate_frame_physically_aligned_verified":False,
        "candidate_kcl_octree_active_for_ball_verified":False,
        "tree_specific_collision_mesh_verified":False,
        "tree_hitbox_geometry_verified":False,
        "ball_response_verified":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    if capture not in range(1,8):
        raise ValueError("Unsupported original capture")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            p=seven.src._file(roots[capture],f"{capture}.{i}.raw",size)
            h=stack.enter_context(p.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(h.fileno(),0,access=mmap.ACCESS_READ)))
        rd=seven.roster.TwoBankReader(*banks)
        source=seven._get(rd)
        manager=source["field"]
        count=rd.u32(manager+0x1C)
        base=rd.u32(manager+0x20)
        if count!=COUNT or seven.roster._bank(base,count*STRIDE)!="MEM2":
            raise ValueError("Source tree array/count not qualified")
        def readcode(pc):
            if not MEM1<=pc<=MEM1+len(banks[0])-4:
                raise ValueError("Native PPC source code out of bound")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        if not native.tree_loop_source_gated(readcode):
            raise ValueError("Original 84-byte source PPC loop mismatch")
        trees=[vec3(rd,base+i*STRIDE+0x30) for i in range(COUNT)]
        controls=[vec3(rd,source[k]+0x30) for k in ("start_obj","pin_obj")]
        triangles=scan_exact_candidate(banks)
        result=summarize(trees,triangles,controls)
    seven._check_archive(archive)
    return {
        "kind":"P0_PRIVATE_TREE_KCL_SPATIAL_BOUND_TEST",
        "status":"SOURCE_TREE_KCL_BROADSPATIAL_AUDIT",
        "capture":capture,
        "original_sha_scene_84tree_code_verified":True,
        "kcl_histogram_original_2498_fully_qualified":True,
        **result,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",type=Path,required=True)
    parser.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=parser.parse_args(argv)
    try:
        print(json.dumps(run(args.archive,args.capture),
                         sort_keys=True,separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,IndexError,TypeError,OverflowError,
            AttributeError,KeyError,struct.error,ZeroDivisionError):
        print('{"status":"ABSTAIN_TREE_KCL_BROADSPATIAL","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
