#!/usr/bin/env python3
"""Private Wii Sports Golf Rev1 KCL surface/PMP tree inventory.

Strict read-only original SHA archive, source-selected scene, single valid KCL.
Prints only categorical counts; never exports private mesh, object coordinates
or file addresses, and never writes RAM or approves training.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
import json
import math
import mmap
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as seven

FLAGS = {
    0x0000: "none",
    0x0001: "fairway",
    0x0002: "rough",
    0x0003: "bunker",
    0x0004: "out_of_bounds",
    0x0005: "camera_lock",
    0x0006: "green",
    0x0007: "water",
    0x0009: "fringe",
    0x000A: "pole",
    0x000B: "cup",
    0x000C: "cliff",
    0x000D: "camera_lock_no_collision",
}
TREE_IDS = {
    0x00010002: "tree_variant_1",
    0x00010003: "tree_variant_2",
    0x00010004: "tree_variant_1_water_reflection",
    0x00010005: "tree_variant_2_water_reflection",
}
# Source: kiwi515/Resort2OG/src/core/{RPGame/RPGolFieldManager.h,
# RPUtility/RPUtlMapObject.h,RPUtlMapData.h}, for ORIGINAL Wii Sports.
PMP_RECORD_SIZE = 0x58


def norm2(v):
    return sum(x*x for x in v)


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def read_prism_histogram(bank, offset=0, *, required_min=3):
    """Return histogram only after every prism passes typed numeric checks."""
    try:
        if offset < 0 or offset % 4 or offset+0x3C > len(bank):
            return None
        po,no,pro,octo = struct.unpack_from(">4I", bank,offset)
        ps = pro+0x10  # 1-indexed prism array
        if not (0x38 <= po <= 0x1000 and po % 4 == no % 4 == pro % 4 == octo % 4 == 0
                and po+36 <= no and no+48 <= ps and ps+16*required_min <= octo
                and octo <= 32*1024*1024 and offset+octo+4 <= len(bank)):
            return None
        nv,nn,npr = (no-po)//12, (ps-no)//12, (octo-ps)//16
        if not (3 <= nv <= 65535 and 4 <= nn <= 65535 and required_min <= npr <= 400000):
            return None
        thickness = struct.unpack_from(">f", bank, offset+0x10)[0]
        minimum = struct.unpack_from(">fff", bank,offset+0x14)
        shifts = struct.unpack_from(">3I",bank,offset+0x2C)
        if not (math.isfinite(thickness) and 0 < thickness < 100000
                and all(math.isfinite(x) and abs(x) < 1e7 for x in minimum)
                and all(s < 32 for s in shifts)):
            return None
        used_normals = {}
        used_vertices = {}
        hist = Counter()
        for i in range(npr):
            h,vi,fi,ea,eb,ec,attr = struct.unpack_from(">f6H", bank,offset+ps+16*i)
            if (not math.isfinite(h) or not 1e-8 < h < 1e7
                    or vi >= nv or max(fi,ea,eb,ec) >= nn):
                return None
            if vi not in used_vertices:
                v = struct.unpack_from(">fff",bank,offset+po+12*vi)
                if not all(math.isfinite(x) and abs(x)<1e7 for x in v):
                    return None
                used_vertices[vi] = v
            for ni in (fi,ea,eb,ec):
                if ni not in used_normals:
                    n = struct.unpack_from(">fff",bank,offset+no+12*ni)
                    if not all(math.isfinite(x) for x in n) or not 0.7 < norm2(n) < 1.3:
                        return None
                    used_normals[ni]=n
            face,a,b,c = (used_normals[j] for j in (fi,ea,eb,ec))
            va,vb = cross(a,face),cross(b,face)
            da,db = dot(va,c),dot(vb,c)
            if not (math.isfinite(da) and math.isfinite(db)
                    and abs(da)>1e-7 and abs(db)>1e-7):
                return None
            p=used_vertices[vi]
            v2=tuple(p[j] + vb[j]*(h/db) for j in range(3))
            v3=tuple(p[j] + va[j]*(h/da) for j in range(3))
            if not all(math.isfinite(x) and abs(x)<1e7 for v in (v2,v3) for x in v):
                return None
            area = cross(tuple(v2[j]-p[j] for j in range(3)),
                         tuple(v3[j]-p[j] for j in range(3)))
            if not 1e-12 < norm2(area) < 1e26:
                return None
            hist[attr]+=1
        return hist
    except (ValueError, OverflowError, IndexError, struct.error, ZeroDivisionError):
        return None


def scan(bank, *, maximum=2):
    found=[]
    for prefix in (0x38,0x3C,0x40,0x44,0x48,0x4C,0x50,0x60,0x80):
        marker=struct.pack(">I",prefix)
        start=-1
        while True:
            start=bank.find(marker,start+1)
            if start < 0:
                break
            if start % 4:
                continue
            hist=read_prism_histogram(bank,start)
            if hist is not None:
                found.append(hist)
                if len(found)>=maximum:
                    return found
    return found


def classify_tree_records(records):
    """Pure parser of packed/unpacked OG Golf PMP object-array records."""
    if len(records) % PMP_RECORD_SIZE:
        return None
    result = Counter()
    for off in range(0,len(records),PMP_RECORD_SIZE):
        ident = struct.unpack_from(">I",records,off)[0]
        if ident in TREE_IDS:
            position = struct.unpack_from(">3f",records,off+0x08)
            scale = struct.unpack_from(">3f",records,off+0x14)
            if not all(math.isfinite(x) and abs(x)<1e7 for x in position+scale):
                return None
            result[TREE_IDS[ident]] += 1
    return result


def pmp_inventory(rd, field):
    """Best-effort optional tree locations; fail closed on unknown layout."""
    u=rd.u32
    known_instance_count=u(field+0x1c)
    tree_array=u(field+0x20)
    reported = {
        "source_field_tree_count_bounded": known_instance_count if known_instance_count<=4096 else None,
        "source_field_tree_array_present": bool(tree_array and
            seven.roster._bank(tree_array,4)=="MEM2"),
        "pmp_tree_positions_verified": False,
        "pmp_tree_counts": {},
    }
    try:
        data=u(field+0x18)
        if seven.roster._bank(data,0x10)!="MEM2":
            return reported
        # RPUtlMapData source header: mpHeader +0x0, mpObjects +0x4.
        header=u(data)
        objects=u(data+0x04)
        if seven.roster._bank(header,0xC0)!="MEM2" or u(header)!=0x504D5046:
            return reported
        num=rd.u16(header+0x10) if hasattr(rd,"u16") else (u(header+0x10)>>16)
        if not 1<=num<=2048 or seven.roster._bank(objects,num*PMP_RECORD_SIZE)!="MEM2":
            return reported
        blob=bytes(rd.u8(objects+i) for i in range(num*PMP_RECORD_SIZE)) if hasattr(rd,"u8") else b"".join(
            struct.pack(">I",u(objects+i)) for i in range(0,num*PMP_RECORD_SIZE,4))
        counts=classify_tree_records(blob)
        if counts is not None:
            reported["pmp_tree_positions_verified"]=True
            reported["pmp_tree_counts"]=dict(sorted(counts.items()))
    except (ValueError,OverflowError,TypeError,IndexError,struct.error):
        pass
    return reported


def inventory(archive: Path, capture: int):
    if capture not in range(1,8):
        raise ValueError("Unsupported phase")
    seven._check_archive(archive)  # independently original native SHA manifest
    with ExitStack() as stack:
        banks=[]
        root=archive.resolve(strict=True)
        for i,size in enumerate(seven.SIZE,1):
            p=seven.src._file(root,f"{capture}.{i}.raw",size)
            f=stack.enter_context(p.open("rb"))
            banks.append(stack.enter_context(mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)))
        rd=seven.roster.TwoBankReader(*banks)
        source=seven._get(rd)  # original selected scene + ball + tee/pin gates
        found=[(label,hist) for label,bank in zip(("MEM1","MEM2"),banks)
               for hist in scan(bank)]
        if len(found)!=1:
            raise ValueError("KCL candidate absent or ambiguous")
        label,hist=found[0]
        tree=pmp_inventory(rd,source["field"])
        total=sum(hist.values())
        report={
            "kind":"P0_OGWS_PRIVATE_SURFACE_TREE_INVENTORY",
            "status":"CANDIDATE_SURFACE_FLAGS_COUNTED",
            "game_source":"RSPE01 Rev1 scene5 mode4",
            "capture":capture,
            "bank":label,
            "kcl_prism_records_fully_validated":total,
            "surface_flags":[
                {"attribute":f"0x{attr:04X}",
                 "source_documented_type":FLAGS.get(attr,"UNKNOWN_NO_COLOR_ASSIGNED"),
                 "triangles":count}
                for attr,count in sorted(hist.items())],
            "tree_records":tree,
            "tree_models_extracted":False,
            "visible_texture_classification_verified":False,
            "collision_octree_reachability_verified":False,
            "active_course_asset_ownership_verified":False,
            "terrain_colorization_ready_as_hypothesis":True,
            "training_approved":False,
        }
    seven._check_archive(archive)  # same original source hash after read
    return report


def main(argv=None):
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--archive",type=Path,required=True)
    a.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=a.parse_args(argv)
    try:
        print(json.dumps(inventory(args.archive,args.capture),indent=2,sort_keys=True))
        return 0
    except (ValueError,OSError,KeyError,IndexError,TypeError,OverflowError,
            AttributeError,struct.error):
        print(json.dumps({"kind":"P0_OGWS_PRIVATE_SURFACE_TREE_INVENTORY",
                          "status":"ABSTAIN_SOURCE_OR_GEOMETRY",
                          "training_approved":False}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
