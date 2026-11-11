#!/usr/bin/env python3
"""Disambiguate native OGWS Golf +0x48 byte readers by source receiver class.

Original, SHA/scene and 94x84-byte tree-source qualified, read-only.
Native source code fingerprints distinguish:
  * FieldManager's actual 94-tree array +0x48 flag writer;
  * a different Tree source function using r30+0x1c/0x20/0x28
    as handles, r30+0x4c/+0x50 as FLOATS, and a camera method;
  * a FieldManager caller using CameraManager-returned r3+0x48.
Collects only aggregate native tree-record field classifications. Never
publishes private pointers, full source code, game XYZ or resources.
Do NOT infer actual collision shape or physics from offset coincidence.
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
import p0_tree_hitbox_source_callgraph_private as native
import p0_tree_proximity_flag_private as proximity

MEM1=0x80000000
TREE=native.UNITS["Tree"][0]
FIELD=native.UNITS["FieldManager"][0]
TREE_COUNT=94
TREE_STRIDE=84

# Concrete public RSPE01_01 compiled object split source targets, confirmed
# independently against research/source_maps/RSPE01_01_public_text_units.json.
TARGETS={
    "Tree+0x04B0 -> MapObjBase":(TREE+0x04B0,0x80290580),
    "Tree+0x04B8 -> MapObjBase":(TREE+0x04B8,0x80290580),
    "Tree+0x04C0 -> MapObjBase":(TREE+0x04C0,0x80290580),
    "Tree+0x04CC -> Camera":(TREE+0x04CC,0x8029BE40),
    "Tree+0x04EC -> Camera":(TREE+0x04EC,0x8029BE40),
    "FieldManager+0x0784 -> CameraManager":(FIELD+0x0784,0x8028ED90),
}
ANCHORS={
    TREE+0x049C:0x7C7E1B78, # r30 = r3; does not prove r3 is 94-tree type
    TREE+0x04A0:0x80030024, # lwz +0x24(r3) as integer
    TREE+0x04AC:0x8063001C, # lwz +0x1c(r3) as handle
    TREE+0x04B4:0x807E0020, # lwz +0x20(r30) as handle
    TREE+0x04BC:0x807E0028, # lwz +0x28(r30) as handle
    TREE+0x04D8:0xD03E004C, # stfs f1,+0x4c(r30)
    TREE+0x04F0:0xD03E0050, # stfs f1,+0x50(r30)
    TREE+0x0504:0x881E0048, # lbz r0,+0x48(r30)
    FIELD+0x0778:0x7C7F1B78, # save field receiver r3 into r31
    FIELD+0x0788:0x88030048, # lbz r0,+0x48(r3) after camera mgr BL
}

SCANNED_UNITS={
    "MapObjBase":(0x8028F9FC,0x80290B44),
    "FieldManager":native.UNITS["FieldManager"],
    "Tree":native.UNITS["Tree"],
    "Ball":native.UNITS["Ball"],
    "Simulation":native.UNITS["Simulation"],
    "CameraManager":(0x8028EAE0,0x8028F9FC),
    "Camera":(0x8029BBB4,0x8029C2F8),
}
# For static direct calls into candidate function entry; no virtual caller
# inference from absent direct callsites.
ENTRY_TARGETS={
    "tree_distance_flag_writer":TREE+0x000C,
    "suspected_other_type_048_reader":TREE+0x047C,
    "camera_manager_048_reader":FIELD+0x0768,
}


def validate_source(read):
    if not native.tree_loop_source_gated(read) or not proximity.fingerprint(read):
        raise ValueError("Native 94-tree source/flag producer changed")
    if any(read(pc)!=word for pc,word in ANCHORS.items()):
        raise ValueError("Native candidate reader/writer instruction changed")
    if any(native.direct_b(pc,read(pc))!=(target,True)
           for pc,target in TARGETS.values()):
        raise ValueError("Native camera/helper BL target changed")
    return True


def classify_native_tree_fields(u32,bank,base,count):
    if count!=TREE_COUNT or not bank(base,count*TREE_STRIDE,"MEM2"):
        raise ValueError("Original contiguous tree array not qualified")
    offsets=(0x1C,0x20,0x24,0x28,0x4C,0x50)
    counts={}
    for off in offsets:
        record=Counter()
        for idx in range(count):
            raw=u32(base+idx*TREE_STRIDE+off)
            try:
                v=struct.unpack(">f",raw.to_bytes(4,"big"))[0]
            except (OverflowError,ValueError):
                raise ValueError("Malformed source word")
            if raw==0: record["zero_word"]+=1
            if math.isfinite(v) and abs(v)<=10000:
                record["plausible_f32"]+=1
            if raw%4==0 and bank(raw,4,"MEM1"):
                record["bounded_aligned_mem1_ptr"]+=1
            if raw%4==0 and bank(raw,4,"MEM2"):
                record["bounded_aligned_mem2_ptr"]+=1
        counts[f"+0x{off:02X}"]={k:record[k] for k in (
            "zero_word","plausible_f32",
            "bounded_aligned_mem1_ptr","bounded_aligned_mem2_ptr")}
    return counts


def find_callers(read):
    found={key:[] for key in ENTRY_TARGETS}
    for owner,(start,end) in SCANNED_UNITS.items():
        for pc in range(start,end,4):
            b=native.direct_b(pc,read(pc))
            if not b or not b[1]:
                continue
            for name,target in ENTRY_TARGETS.items():
                if b[0]==target:
                    sites=found[name]
                    if len(sites)<18:
                        sites.append(owner+"+0x"+format(pc-start,"04X"))
    return found


def classify(read,u32,bank,base,count):
    validate_source(read)
    return {
        "source_qualified_tree_records":count,
        "native_renderer_reader_r30_assigned_from_r3":True,
        "r30_offsets_0x1c_0x20_0x28_used_as_handles":True,
        "r30_offsets_0x4c_0x50_written_as_floats":True,
        "source_byte_0x48_reader_looks_at_r30":True,
        "fieldmanager_byte_reader_after_camera_manager_call":True,
        "specific_direct_call_targets":{
            label: { "source_family":label.split(" -> ")[1],
                     "source_target_relative":{
                       "MapObjBase":"+0x0B84",
                       "Camera":"+0x028C",
                       "CameraManager":"+0x02B0"}[label.split(" -> ")[1]]}
            for label in TARGETS},
        "actual_94_tree_record_field_compatibility":
            classify_native_tree_fields(u32,bank,base,count),
        "direct_callers_of_candidate_function_entries":find_callers(read),
        "reader_has_proven_tree_record_receiver":False,
        "tree_0x48_flag_acts_as_hitbox_filter_proven":False,
        "tree_collision_geometry_proven":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    if capture not in range(1,8):
        raise ValueError("Original source capture 1..7 only")
    files=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            file=seven.src._file(files[capture],f"{capture}.{i}.raw",size)
            h=stack.enter_context(file.open("rb"))
            banks.append(stack.enter_context(mmap.mmap(
                h.fileno(),0,access=mmap.ACCESS_READ)))
        r=seven.roster.TwoBankReader(*banks)
        field=seven._get(r)["field"]
        count=r.u32(field+0x1C)
        base=r.u32(field+0x20)
        if count!=TREE_COUNT or seven.roster._bank(
                base,count*TREE_STRIDE)!="MEM2":
            raise ValueError("Original tree source owner changed")
        def read(pc):
            if pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Out-of-source memory instruction")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        def bank(ptr,n,kind):
            return seven.roster._bank(ptr,n)==kind
        result=classify(read,r.u32,bank,base,count)
    seven._check_archive(archive)
    return {
        "kind":"P0_TREE_FLAG_RECEIVER_DISAMBIGUATION",
        "status":"TREE_BYTE_FLAG_RECEIVER_STATIC_CONTEXT",
        "capture":capture,"original_sha_scene_source_qualified":True,
        **result,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--capture",choices=range(1,8),type=int,default=7)
    a=p.parse_args(argv)
    try:
        print(json.dumps(run(a.archive,a.capture),sort_keys=True,separators=(",",":")))
        return 0
    except (OSError,ValueError,KeyError,IndexError,OverflowError,TypeError,
            AttributeError,struct.error):
        print('{"status":"ABSTAIN_TREE_FLAG_RECEIVER_IDENTITY","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
