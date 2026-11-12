#!/usr/bin/env python3
"""Original Wii Golf 94-tree shared firstword: FULL public text-unit classification.

Previous source-gated audit established 94 shared firstwords and inspected
64 candidate table slots: 20 pointed into the selected Ball code, 2
FieldManager, 42 outside just those selected units. Those 42 have not
been classified against *all* available public code.

Read-only source/SHA/scene/tree-loop/PPC provenance as before. This is
a FOCUSED 64-slot lookup, not a RAM/code scan. Uses the retained
doldecomp/ogws public RSPE01 Rev1 .text source map JSON (no private code).
No ROM bytes, raw RAM pointers, per-tree positions, model assets or
physical collision claims. Even a Tree-named target is not a contact
method until its actual dataflow and receiver are verified.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as seven
import p0_ball_kcol_active_resource_private as active
import p0_tree_ball_indirect_dispatch_private as previous
import p0_tree_hitbox_source_callgraph_private as native

MEM1=seven.roster.MEM1_BASE
MAP=Path(__file__).resolve().parents[1]/"research"/"source_maps"/"RSPE01_01_public_text_units.json"
PUBLIC_BLOB_SHA="df4085de5285b0d188fdfec8c097b301382263d3"
SLOTS=64


def validated_intervals(public):
    if not isinstance(public,dict) or any((
            public.get("kind")!="PUBLIC-RSPE01-REV1-TEXT-OBJECT-SPLITS",
            public.get("game_id")!="RSPE01",
            public.get("disc_revision")!=1,
            public.get("source_blob_sha")!=PUBLIC_BLOB_SHA)):
        raise ValueError("Public source map provenance changed")
    raw=public.get("intervals")
    if not isinstance(raw,list) or len(raw)<100:
        raise ValueError("Incomplete public source text intervals")
    result=[]
    end=0
    for row in raw:
        if (not isinstance(row,list) or len(row)!=3 or
                type(row[0]) is not int or type(row[1]) is not int or
                not isinstance(row[2],str) or not row[2] or
                row[0]%4 or row[1]%4 or row[0]>=row[1] or row[0]<end):
            raise ValueError("Overlapping or invalid original public code split")
        result.append(tuple(row))
        end=row[1]
    return result


def label_target(target,intervals):
    starts=[x[0] for x in intervals]
    j=bisect_right(starts,target)-1
    if j>=0:
        lo,hi,name=intervals[j]
        if lo<=target<hi:
            return name,f"+0x{target-lo:04X}"
    return None,None


def examine(u32,tree_base,count,bank,intervals):
    # Reuse source-qualified 94x84 array + same shared firstword gate.
    prior=previous.inspect_tree_firstword(u32,tree_base,count,bank)
    if not prior["all_94_tree_firstwords_identical"]:
        raise ValueError("Original shared tree firstword gate failed")
    table=u32(tree_base)
    rows=[]
    counts=Counter()
    for slot in range(SLOTS):
        target=u32(table+4*slot)
        owner,relative=label_target(target,intervals)
        category=owner or "not_in_retained_public_text"
        counts[category]+=1
        rows.append({
            "slot":slot,
            "public_compilation_unit":owner,
            "unit_relative_target":relative,
            "within_retained_public_text":owner is not None,
            "actual_cpp_method_proven":False,
            "tree_contact_semantics_proven":False,
        })
    return {
        "shared_tree_firstword_across_94_verified":True,
        "source_tree_count":count,
        "candidate_table_slots_bounded":SLOTS,
        "classification_counts_by_public_compilation_unit":dict(sorted(counts.items())),
        "candidate_target_sites":rows,
        "resolved_code_target_count":sum(v for k,v in counts.items()
                                          if k!="not_in_retained_public_text"),
        "outside_public_map_count":counts["not_in_retained_public_text"],
        "shared_firstword_is_true_cpp_vtable_proven":False,
        "table_entry_called_on_tree_from_ball_proven":False,
        "tree_collision_hitbox_proven":False,
        "ball_velocity_response_proven":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    if capture not in range(1,8):
        raise ValueError("Only original seven captures supported")
    intervals=validated_intervals(json.loads(MAP.read_text(encoding="utf-8")))
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            f=seven.src._file(folders[capture],f"{capture}.{i}.raw",size)
            h=stack.enter_context(f.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(h.fileno(),0,access=mmap.ACCESS_READ)))
        rd=seven.roster.TwoBankReader(*banks)
        field=seven._get(rd)["field"]
        count=rd.u32(field+0x1C)
        tree=rd.u32(field+0x20)
        if count!=94 or seven.roster._bank(tree,94*84)!="MEM2":
            raise ValueError("Original FieldManager 94 trees absent")
        def read(pc):
            if pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Original code source outside MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        if not native.tree_loop_source_gated(read):
            raise ValueError("Original native 94-tree loop changed")
        active.inspect_source(read)
        result=examine(rd.u32,tree,count,seven.roster._bank,intervals)
    seven._check_archive(archive)
    return {
        "kind":"P0_94_TREE_FIRSTWORD_ALL_PUBLIC_CODE_UNIT_CLASSIFICATION",
        "status":"SOURCE_QUALIFIED_64_TABLE_SLOT_PUBLIC_UNIT_RESOLUTION",
        "capture":capture,
        "original_archive_sha_scene_tree_and_ball_kcol_source_gates":True,
        "public_rev1_text_map_provenance_verified":True,
        **result,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=p.parse_args(argv)
    try:
        print(json.dumps(run(args.archive,args.capture),sort_keys=True,
                         separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,IndexError,OverflowError,
            AttributeError,KeyError,struct.error,json.JSONDecodeError):
        print('{"status":"ABSTAIN_TREE_FIRSTWORD_PUBLIC_MAP_RESOLUTION",'
              '"training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
