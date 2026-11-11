#!/usr/bin/env python3
"""Read-only source-qualified Golf tree object dispatch / collider lead audit.

Original SHA/scene/PPC-loop gates. Inspect 94 contiguous 0x54 objects,
possible method tables, +0x40/+0x44 self-links, and inline 84-byte tree
array access clues in Ball/Tree/Simulation source code. Never prints native
RAM pointers, positions, ROM words or tree models; no physics claims.
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
import p0_tree_hitbox_source_callgraph_private as native
MEM1=0x80000000
STRIDE=84
MAX_SLOTS=20
CODES=("Tree","TreeWater","Ball","Simulation","GolfKCol","FieldManager")
FIELDS={"model_ptr":4,"pmp_ptr":8,"rotation_ptr":0x40,"translation_ptr":0x44}


def label(pc):
    for name in CODES:
        lo,hi=native.UNITS[name]
        if lo<=pc<hi:
            return name+"+0x"+format(pc-lo,"04X")
    return None


def classify(ptr,bank):
    if ptr==0:
        return "zero"
    for name in ("MEM1","MEM2"):
        if ptr%4==0 and bank(ptr,4,name):
            return name.lower()+"_pointer"
    return "other_nonzero"


def inspect_objects(u32,bank,base,count):
    if count!=94 or not bank(base,count*STRIDE,"MEM2"):
        raise ValueError("Original bounded source tree array missing")
    first=Counter()
    field_buckets={k:Counter() for k in FIELDS}
    self_rot=self_pos=0
    for i in range(count):
        obj=base+i*STRIDE
        first[u32(obj)]+=1
        for name,off in FIELDS.items():
            field_buckets[name][classify(u32(obj+off),bank)]+=1
        self_rot+=int(u32(obj+0x40)==obj+0x0C)
        self_pos+=int(u32(obj+0x44)==obj+0x30)
    patterns=[]
    for addr,n in first.most_common(8):
        klass=classify(addr,bank)
        targets=[]
        if klass=="mem1_pointer" and bank(addr,MAX_SLOTS*4,"MEM1"):
            for slot in range(MAX_SLOTS):
                dst=u32(addr+4*slot)
                public=label(dst)
                if public:
                    targets.append({"slot":slot,"target":public})
        patterns.append({"object_count":n,"firstword_class":klass,
                         "public_method_candidates":targets,
                         "firstword_is_vtable_verified":False})
    return {"tree_count":count,"distinct_object_firstwords":len(first),
            "firstword_patterns":patterns,
            "member_pointer_buckets":{k:dict(sorted(v.items()))
                                     for k,v in field_buckets.items()},
            "rotation_self_reference_count":self_rot,
            "translation_self_reference_count":self_pos,
            "tree_model_owner_verified":False,
            "vtable_dispatch_verified":False,
            "tree_collision_geometry_verified":False}


def inline_stride(read):
    results={}
    for unit in ("Ball","Tree","Simulation","FieldManager"):
        lo,hi=native.UNITS[unit]
        by_op={7:[],14:[]}
        for pc in range(lo,hi,4):
            w=read(pc)
            op=w>>26
            imm=w&0xFFFF
            if imm in (84,0xFFAC) and op in by_op:
                by_op[op].append("+0x"+format(pc-lo,"04X"))
        results[unit]={"mulli_84":by_op[7][:18],
                       "mulli_count":len(by_op[7]),
                       "addi_84":by_op[14][:18],
                       "addi_count":len(by_op[14])}
    return results


def run(archive,capture):
    if capture not in range(1,8):
        raise ValueError("Invalid capture")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            p=seven.src._file(folders[capture],f"{capture}.{i}.raw",size)
            h=stack.enter_context(p.open("rb"))
            banks.append(stack.enter_context(mmap.mmap(
                h.fileno(),0,access=mmap.ACCESS_READ)))
        rd=seven.roster.TwoBankReader(*banks)
        field=seven._get(rd)["field"]
        count=rd.u32(field+0x1C)
        base=rd.u32(field+0x20)
        if count!=94 or seven.roster._bank(base,count*STRIDE)!="MEM2":
            raise ValueError("Tree record source mismatch")
        def bank(addr,n,kind):
            return seven.roster._bank(addr,n)==kind
        def word(pc):
            if pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Not source MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        if not native.tree_loop_source_gated(word):
            raise ValueError("Source PPC array stride mismatch")
        objects=inspect_objects(rd.u32,bank,base,count)
        code=inline_stride(word)
    seven._check_archive(archive)
    return {"status":"SOURCE_QUALIFIED_TREE_OBJECT_DISPATCH_REPORT",
            "tree_objects":objects,
            "inline_84_byte_source_code_cues":code,
            "source_sha_scene_stride_gate":True,
            "tree_hitbox_verified":False,
            "native_contact_response_verified":False,
            "training_approved":False}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    a=p.parse_args(argv)
    try:
        print(json.dumps(run(a.archive,a.capture),sort_keys=True,separators=(",",":")))
        return 0
    except (OSError,ValueError,TypeError,IndexError,OverflowError,
            AttributeError,KeyError,struct.error):
        print('{"status":"ABSTAIN_TREE_OBJECT_DISPATCH","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
