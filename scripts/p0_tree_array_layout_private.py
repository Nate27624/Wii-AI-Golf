#!/usr/bin/env python3
"""Read-only, source-gated PRIVATE tree-array layout falsifier.

Infers only candidate fixed *stride* and source-component translation count
from a source-owned tree array; never prints native pointers/XYZ or infers tree
hitboxes, visual models, terrain transforms or training labels.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
import json
import math
import mmap
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as seven

STRIDES = tuple(range(0x48, 0x181, 4))
# 'RPGolMapObjBase' is a 0x48-byte *tentative source header*; some fields
# overlap in the public annotation, so NEVER infer scale or native pointer to
# translation from its +0x3C/+0x40/+0x44 claims.
TRANSLATION_OFFSET = 0x30
MAX_COUNT = 4096


def in_guest(address, length):
    return seven.roster._bank(address,length) in {"MEM1", "MEM2"}


def probe_stride(word, read_vec, base, count, stride, *, memory_check=in_guest):
    """Pure, bounded structural hypothesis; same source vtable across elements.

    Distinct finite translations and same vtable are necessary, not sufficient.
    No gameplay semantics are assigned from a positive stride hypothesis.
    """
    if type(count) is not int or not 3 <= count <= MAX_COUNT:
        return None
    if type(stride) is not int or stride not in STRIDES:
        return None
    if not memory_check(base, (count-1)*stride+0x3C):
        return None
    first_vtable=word(base)
    if not memory_check(first_vtable,4):
        return None
    valid=0
    vtables=Counter()
    rounded=set()
    models=0
    placement_links=0
    reason=Counter()
    for i in range(count):
        at=base+i*stride
        try:
            vt,model,obj=word(at),word(at+0x04),word(at+0x08)
            xyz=read_vec(at+TRANSLATION_OFFSET)
            if (not all(math.isfinite(v) and abs(v)<1e6 for v in xyz)
                    or math.hypot(xyz[0],xyz[2])>=1e6):
                reason["bad_translation"]+=1
                continue
            if not memory_check(vt,4):
                reason["nonpointer_vtable"]+=1
                continue
            if model and not memory_check(model,4):
                reason["invalid_model_pointer"]+=1
                continue
            if obj and not memory_check(obj,4):
                reason["invalid_placement_pointer"]+=1
                continue
            valid+=1
            vtables[vt]+=1
            rounded.add(tuple(round(v,3) for v in xyz))
            models+=int(bool(model))
            placement_links+=int(bool(obj))
        except (ValueError,TypeError,IndexError,struct.error):
            reason["bad_record"]+=1
    common_vtable=max(vtables.values(),default=0)
    return {
        "candidate_stride_bytes":stride,
        "source_tree_count":count,
        "record_structural_hits":valid,
        "common_vtable_hits":common_vtable,
        "distinct_translation_candidates":len(rounded),
        "non_null_model_links":models,
        "non_null_placement_links":placement_links,
        "structural_candidate_only":True,
    }


def study(word, read_vec, base, count, memory_check=in_guest):
    """Rank robust candidates; never expose raw addresses/positions/vtables."""
    if not memory_check(base,4):
        raise ValueError("tree array pointer invalid")
    rows=[x for stride in STRIDES
          if (x:=probe_stride(word,read_vec,base,count,stride,
                              memory_check=memory_check)) is not None]
    rows.sort(key=lambda x: (
        -x["common_vtable_hits"],
        -x["record_structural_hits"],
        -x["distinct_translation_candidates"],
        -x["non_null_placement_links"],
        x["candidate_stride_bytes"]))
    best=rows[:8]
    # Bounded similarity gate, not a game object type proof.
    passing=[x for x in best if x["common_vtable_hits"] >= math.ceil(count*0.9)
             and x["record_structural_hits"] >= math.ceil(count*0.9)
             and x["distinct_translation_candidates"] >= 5]
    return {"status":"STRUCTURAL_TREE_ARRAY_CANDIDATE" if passing
             else "TREE_LAYOUT_UNRESOLVED",
            "qualified_stride_candidates":passing,
            "top_candidate_diagnostics":best[:3],
            "tree_position_world_alignment_verified":False,
            "actual_tree_models_verified":False,
            "training_approved":False}


def run(archive: Path, capture: int):
    if capture not in range(1,8):
        raise ValueError("invalid capture")
    folders=seven._check_archive(archive) # full original SHA inventory
    with ExitStack() as stack:
        maps=[]
        for i,size in enumerate(seven.SIZE,1):
            p=seven.src._file(folders[capture],f"{capture}.{i}.raw",size)
            f=stack.enter_context(p.open("rb"))
            maps.append(stack.enter_context(mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)))
        rd=seven.roster.TwoBankReader(*maps)
        owner=seven._get(rd)
        field=owner["field"]
        count=rd.u32(field+0x1c)
        base=rd.u32(field+0x20)
        if not 3<=count<=MAX_COUNT or seven.roster._bank(base,4)!="MEM2":
            raise ValueError("tree array source owner invalid")
        def vec(address):
            return tuple(struct.unpack(">f",rd.u32(address+4*i).to_bytes(4,"big"))[0]
                         for i in range(3))
        result=study(rd.u32,vec,base,count)
    seven._check_archive(archive) # verify original bytes after mmap closes
    return {"kind":"P0_PRIVATE_GOLF_TREE_ARRAY_LAYOUT",
            "capture":capture,"source_scene_gated":True,
            "tree_count_source":count,
            "source_array_MEM2_valid":True,
            **result}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=p.parse_args(argv)
    try:
        print(json.dumps(run(args.archive,args.capture),sort_keys=True,indent=2))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,
            OverflowError,AttributeError,struct.error):
        print(json.dumps({"kind":"P0_PRIVATE_GOLF_TREE_ARRAY_LAYOUT",
                          "status":"ABSTAIN_ARCHIVE_OR_SOURCE_GATE",
                          "training_approved":False}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
