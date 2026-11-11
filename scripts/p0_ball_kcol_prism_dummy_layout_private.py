#!/usr/bin/env python3
"""Read-only original Wii Golf active KCL prism-table dummy-record audit.

Previous active resource test showed exact vertex and normal aliases, but
compared object+0x0C (native prism-base pointer) with terrain header+pr+16
(first usable prism). KCL indices may be one-based; header+pr includes a
16-byte dummy prism. This strictly source-gated diagnostic distinguishes
those two layouts and tests full prism bytes, without inventing a mesh.

Original RSPE01 Rev1 SHA/scene/94x84 tree-loop, 5 Ball-KCol calls, 7
inverse edges, exact primitive+0x0E producer and exact r13 global are
required. No Dolphin, game memory writes, code/asset output, tree hitboxes,
velocity semantics, or training approvals.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as seven
import p0_ball_kcol_active_resource_private as earlier
import p0_tree_hitbox_source_callgraph_private as native
import p0_tree_kcl_spatial_broadphase_private as broad

MEM1=seven.roster.MEM1_BASE
DUMMY_RECORD_BYTES=16
MAX_ALLOWED_PRISMS=broad.KCL_PRISMS


def compare_prism_layout(rd,banks,slot,locate=None):
    """Compare a *qualified* active object pointer with the same terrain KCL.

    Uses only the unique candidate identified by original 2498-prism histogram;
    does not treat arbitrary 2498 successive heap words as valid primitives.
    """
    if seven.roster._bank(slot,4)!="MEM1":
        raise ValueError("SDA global slot outside MEM1")
    obj=rd.u32(slot)
    if seven.roster._bank(obj,0x60) is None:
        raise ValueError("Global object not in captured banks")
    pv,pn,pp=(rd.u32(obj+off) for off in (4,8,12))
    if any(seven.roster._bank(p,12) is None for p in (pv,pn,pp)):
        raise ValueError("KCol source pointer outside captured banks")

    bank_index,header_offset=(locate or earlier.locate_exact_terrain_kcl)(banks)
    bank=banks[bank_index]
    po,no,pr,octo=struct.unpack_from(">4I",bank,header_offset)
    if octo-pr-DUMMY_RECORD_BYTES!=MAX_ALLOWED_PRISMS*DUMMY_RECORD_BYTES:
        raise ValueError("Terrain header prism span unexpected")
    base=seven.roster.MEM1_BASE if bank_index==0 else seven.roster.MEM2_BASE
    vertices=base+header_offset+po
    normals=base+header_offset+no
    dummy_base=base+header_offset+pr
    first_real=dummy_base+DUMMY_RECORD_BYTES
    source_span=octo-(pr+DUMMY_RECORD_BYTES)
    expected=memoryview(bank)[header_offset+pr+DUMMY_RECORD_BYTES:
                              header_offset+octo]
    if pv!=vertices or pn!=normals:
        raise ValueError("Original active vertex/normal identity changed")

    # The original code indexes 16-byte records from object+0x0C.
    # Verify both candidate pointer conventions explicitly. This is
    # a *bounded* comparison, not a search over unknown memory.
    valid_p=broad.KCL_PRISMS>0 and seven.roster._bank(pp,16) is not None
    dummy_pointer_eq=valid_p and pp==dummy_base
    first_pointer_eq=valid_p and pp==first_real
    data_at_plus_16=earlier.valid_bank_slice(
        banks,pp+DUMMY_RECORD_BYTES,source_span)
    data_at_plus_0=earlier.valid_bank_slice(
        banks,pp,source_span)
    with_dummy_match=(dummy_pointer_eq
                      and data_at_plus_16 is not None
                      and data_at_plus_16==expected)
    first_match=(first_pointer_eq and data_at_plus_0 is not None
                 and data_at_plus_0==expected)
    active_matched=bool(with_dummy_match or first_match)
    return {
        "source_terrain_prisms":MAX_ALLOWED_PRISMS,
        "native_prism_index_stride_bytes":DUMMY_RECORD_BYTES,
        "original_active_vertices_exact_pointer_equal":True,
        "original_active_normals_exact_pointer_equal":True,
        "active_prism_pointer_equals_terrain_dummy_base":bool(dummy_pointer_eq),
        "active_prism_pointer_equals_first_usable_prism":bool(first_pointer_eq),
        "active_prism_data_equal_after_dummy_16_byte_skip":bool(with_dummy_match),
        "active_prism_data_equal_at_direct_pointer":bool(first_match),
        "active_2498_prism_bytes_match_known_terrain":active_matched,
        "active_2498_prism_class13_count_if_verified":
            0 if active_matched else None,
        "other_collision_resource_proven":False,
        "tree_collision_proven":False,
        "ball_velocity_proven":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    if capture not in range(1,8):
        raise ValueError("Only original 7-pair cohort supported")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            p=seven.src._file(folders[capture],f"{capture}.{i}.raw",size)
            fh=stack.enter_context(p.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(fh.fileno(),0,access=mmap.ACCESS_READ)))
        rd=seven.roster.TwoBankReader(*banks)
        field=seven._get(rd)["field"]
        count=rd.u32(field+0x1C)
        treearr=rd.u32(field+0x20)
        if count!=94 or seven.roster._bank(treearr,count*84)!="MEM2":
            raise ValueError("Source tree array no longer verified")
        def read(pc):
            if pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Native PPC read outside MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        if not native.tree_loop_source_gated(read):
            raise ValueError("Original source field loop changed")
        earlier.inspect_source(read)
        r13=earlier.recover_r13_base(read)
        if r13 is None:
            raise ValueError("Original Rev1 r13 initializer unresolved")
        result=compare_prism_layout(rd,banks,r13+earlier.GLOBAL_DISP)
    seven._check_archive(archive)
    return {
        "kind":"P0_KCOL_DUMMY_PRISM_RECORD_ACTIVE_RESOURCE_AUDIT",
        "status":"ACTIVE_KCL_PRISM_LAYOUT_COMPARED",
        "original_archive_sha_scene_and_84_stride_verified":True,
        "original_ball_kcol_5_plus_7_and_classification_gates":True,
        "r13_global_source_verified":True,
        "capture":capture,"source_trees":94,
        **result,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=p.parse_args(argv)
    try:
        print(json.dumps(run(args.archive,args.capture),
                         sort_keys=True,separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,IndexError,TypeError,OverflowError,
            AttributeError,KeyError,struct.error):
        print('{"status":"ABSTAIN_KCL_PRISM_DUMMY_LAYOUT",'
              '"training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
