#!/usr/bin/env python3
"""Original P0 seven-capture Ball/KCol active-prism memory profile (READ ONLY).

Traverse each of seven original RSPE01 Rev1 paired MEM1/MEM2 snapshots.
Every observation is SHA/scene/source-gated and checks the original
94x84 tree-array loop, exact 5+7 Ball/KCol call provenance, native
prism+0x0E material producer, and __init_registers r13 global.
Apply the *correct* 16-byte dummy-prism KCL layout discovered in
capture7, requiring EXACT active vertex/normal/prism buffer aliases
and complete byte equality with the sole 2498-prism terrain candidate.

Report class counts and source-identity comparisons PER capture.
No source pointers, private coordinates, raw buffers, frame data, tree
geometry, game bytes, or source code are exported. An absent class 13
only constrains this active KCL in the observed captures, NOT all
gameplay. No live Dolphin reads, game writes, physics/training labels.
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
import p0_ball_kcol_active_resource_private as active
import p0_ball_kcol_prism_dummy_layout_private as layout
import p0_tree_kcl_spatial_broadphase_private as terrain

MEM1=seven.roster.MEM1_BASE
COUNT=terrain.KCL_PRISMS
STRIDE=16
STEPS=tuple(range(1,8))


def classify_usable_prisms(data, expected_count=COUNT):
    """Only the 16-byte usable records, *excluding* the dummy slot."""
    if expected_count<1 or len(data)!=STRIDE*expected_count:
        raise ValueError("Source KCL usable prism span not qualified")
    hist=Counter()
    for index in range(expected_count):
        # DOL KCL primitive halfword at +0x0E; KCL prism stride is 16.
        material=struct.unpack_from(">H",data,index*STRIDE+14)[0]
        hist[material]+=1
    if sum(hist.values())!=expected_count:
        raise ValueError("Source histogram incomplete")
    return dict(sorted(hist.items()))


def aggregate(rows):
    if len(rows)!=7 or [r["capture"] for r in rows]!=list(STEPS):
        raise ValueError("Incomplete or incorrectly ordered original phases")
    all_match=all(r["all_active_buffers_match_terrain"] for r in rows)
    no13=all(r["class13_count_in_verified_active_prisms"]==0 for r in rows)
    all_known=all(r["active_prism_histogram_matches_existing_terrain"] for r in rows)
    return {
        "all_seven_active_kcl_same_2498_terrain_resource":all_match,
        "all_seven_native_classification_histograms_match_known_terrain":all_known,
        "all_seven_active_prism_class13_counts_zero":no13,
        "same_collision_object_address_in_all_captures":
            all(r["same_kcol_instance_pointer_as_capture1"] for r in rows),
        "same_prism_buffer_address_in_all_captures":
            all(r["same_prism_base_pointer_as_capture1"] for r in rows),
        "class13_tree_event_proven":False,
        "other_kcl_resource_excluded_globally":False,
        "non_kcl_tree_collision_excluded":False,
        "tree_hitbox_geometry_proven":False,
        "ball_velocity_semantics_proven":False,
        "training_approved":False,
    }


def profile_reader(rd,banks,readcode,capture,first_object=None,first_prisms=None):
    if not native.tree_loop_source_gated(readcode):
        raise ValueError("Native original tree loop changed")
    active.inspect_source(readcode)  # Full original five plus seven gates.
    r13=active.recover_r13_base(readcode)
    if r13 is None:
        raise ValueError("Original startup SDA base absent")
    source=seven._get(rd)
    field=source["field"]
    count=rd.u32(field+0x1C)
    tree=rd.u32(field+0x20)
    if count!=94 or seven.roster._bank(tree,count*84)!="MEM2":
        raise ValueError("Original source 94x84 tree array absent")

    slot=r13+active.GLOBAL_DISP
    if seven.roster._bank(slot,4)!="MEM1":
        raise ValueError("Original KCol global slot invalid")
    obj=rd.u32(slot)
    if seven.roster._bank(obj,0x60)!="MEM2":
        raise ValueError("Original KCol global object not MEM2")

    # Read source header once per capture. Must be the UNIQUE existing
    # 2498-prism candidate with the exact original histogram.
    location=active.locate_exact_terrain_kcl(banks)
    verified=layout.compare_prism_layout(
        rd,banks,slot,locate=lambda _:location)
    if not (
        verified["active_prism_pointer_equals_terrain_dummy_base"]
        and verified["active_prism_data_equal_after_dummy_16_byte_skip"]
        and verified["active_2498_prism_bytes_match_known_terrain"]
        and verified["original_active_vertices_exact_pointer_equal"]
        and verified["original_active_normals_exact_pointer_equal"]
    ):
        raise ValueError("Active KCol buffers are not original expected terrain")

    prism_ptr=rd.u32(obj+0x0C)
    span=active.valid_bank_slice(banks,prism_ptr+STRIDE,STRIDE*COUNT)
    if span is None:
        raise ValueError("Active usable prism array outside capture")
    # Copy only in local memory; release mmap-derived views before exit.
    prism_data=bytes(span)
    del span
    hist=classify_usable_prisms(prism_data)
    if hist!=terrain.EXPECTED_FLAGS:
        raise ValueError("Active terrain histogram differs from original gate")

    row={
        "capture":capture,
        "source_trees":count,
        "ball_kcol_global_qualified":True,
        "active_kcol_object_bank":"MEM2",
        "same_kcol_instance_pointer_as_capture1":
            first_object is None or obj==first_object,
        "same_prism_base_pointer_as_capture1":
            first_prisms is None or prism_ptr==first_prisms,
        "active_kcol_prism_pointer_is_dummy_base":True,
        "all_active_buffers_match_terrain":True,
        "active_usable_prisms":COUNT,
        "active_prism_histogram_matches_existing_terrain":True,
        "class13_count_in_verified_active_prisms":hist.get(13,0),
        "active_classification_histogram":{str(k):v for k,v in hist.items()},
        "other_active_kcl_object_proven":False,
        "tree_contact_event_proven":False,
        "training_approved":False,
    }
    return row,obj,prism_ptr


def run(archive:Path):
    folders=seven._check_archive(archive)
    rows=[]
    first_obj=first_prism=None
    for capture in STEPS:
        with ExitStack() as stack:
            banks=[]
            for i,size in enumerate(seven.SIZE,1):
                p=seven.src._file(folders[capture],f"{capture}.{i}.raw",size)
                handle=stack.enter_context(p.open("rb"))
                banks.append(stack.enter_context(
                    mmap.mmap(handle.fileno(),0,access=mmap.ACCESS_READ)))
            rd=seven.roster.TwoBankReader(*banks)
            def readcode(pc):
                if pc<MEM1 or pc+4>MEM1+len(banks[0]):
                    raise ValueError("Original source instruction outside MEM1")
                return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
            row,obj,prism=profile_reader(
                rd,banks,readcode,capture,first_obj,first_prism)
            if first_obj is None:
                first_obj,first_prism=obj,prism
            rows.append(row)
    # Re-hash all archive originals again to guard read-time alterations.
    seven._check_archive(archive)
    summary=aggregate(rows)
    return {
        "kind":"P0_SEVEN_CAPTURE_ACTIVE_TERRAIN_KCL_MATERIAL_AUDIT",
        "status":"SEVEN_SOURCE_QUALIFIED_ACTIVE_KCL_RESOURCE_PROFILES",
        "original_archive_sha_scene_and_84_stride_verified":True,
        "native_ball_kcol_classification_path_qualified":True,
        "original_seven_captures_checked":len(rows),
        "capture_rows":rows,
        **summary,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    a=p.parse_args(argv)
    try:
        print(json.dumps(run(a.archive),sort_keys=True,separators=(",",":"),
                         allow_nan=False))
        return 0
    except (OSError,ValueError,IndexError,TypeError,OverflowError,
            AttributeError,KeyError,struct.error):
        print('{"status":"ABSTAIN_SEVEN_ACTIVE_KCL_MEMORY_PROFILE",'
              '"training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
