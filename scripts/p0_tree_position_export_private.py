#!/usr/bin/env python3
"""Export source-confirmed 94 candidate tree translations to PRIVATE JSON.

This operator-only offline tool is read-only toward original seven-pair native
RAM captures and never starts Dolphin. Export is explicitly local under the
sibling Wii-AI-Golf-Data/derived directory, not inside a Git checkout.

It does NOT extract tree meshes, estimate heights/radii/physics, or approve
training. The UI must label positions as source-verified candidate translations
with unverified visible-scene alignment.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import math
import mmap
import os
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as seven
import p0_tree_stride84_private as tree

SOURCE_CAPTURES=(1,5,7)
EXPECTED_TREES=94
FILENAME="golf-tree-positions-source-94-PRIVATE.json"
SCHEMA_KIND="wii_sports_golf_private_tree_positions_v1"


def make_payload(points, *, captures=SOURCE_CAPTURES):
    """Pure serialization contract for S002 viewer, no derived game physics."""
    if type(points) not in (tuple,list) or len(points)!=EXPECTED_TREES:
        raise ValueError("Expected exactly 94 source tree positions")
    if tuple(captures)!=SOURCE_CAPTURES:
        raise ValueError("Source capture provenance must be original 1/5/7")
    validated=[]
    keys=set()
    for position in points:
        if not isinstance(position,tuple) or not tree.finite_triplet(position):
            raise ValueError("Invalid tree translation candidate")
        key=tuple(round(float(v),3) for v in position)
        if key in keys:
            raise ValueError("Duplicate tree position")
        keys.add(key)
        validated.append([float(x) for x in position])
    return {
        "kind":SCHEMA_KIND,
        "schema_version":1,
        "game_id":"RSPE01",
        "disc_revision":1,
        "source_captures":list(captures),
        "source_count":EXPECTED_TREES,
        "source_element_stride_bytes":84,
        "source_translation_offset_bytes":48,
        "position_frame":"original_source_components_no_transform",
        "tree_positions":validated,
        "source_positions_bitwise_identical_across_captures":True,
        "world_visual_alignment_verified":False,
        "original_tree_meshes_verified":False,
        "collision_hitboxes_verified":False,
        "training_approved":False,
    }


def write_private_payload(data_root:Path, content:dict):
    """Exclusive-create in dedicated Data/derived, never follow symlinks.

    Never overwrite previous operator data. File is not permitted under Git.
    Caller validates original archive gates before writing any candidate.
    """
    if not data_root.is_dir() or data_root.is_symlink():
        raise ValueError("Private Data root missing or symlink")
    root=data_root.resolve(strict=True)
    if root.name!="Wii-AI-Golf-Data":
        raise ValueError("Destination must use private Wii-AI-Golf-Data")
    parent=root/"derived"
    if parent.is_symlink():
        raise ValueError("Private derived folder cannot be a symlink")
    if not parent.exists():
        parent.mkdir(mode=0o700)
    if not parent.is_dir() or parent.is_symlink() or parent.resolve()!=root/"derived":
        raise ValueError("Invalid private destination")
    destination=parent/FILENAME
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Private output exists; refusing overwrite")
    data=(json.dumps(content,allow_nan=False,sort_keys=True,
                     separators=(",",":"))+"\n").encode("utf-8")
    if len(data)>64*1024:
        raise ValueError("Private tree JSON outside size cap")
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    if hasattr(os,"O_BINARY"):
        flags|=os.O_BINARY
    fd=os.open(destination,flags,0o600)
    try:
        with os.fdopen(fd,"wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination


def run(archive:Path):
    # Reuse separately synthetic-tested 10-PPC-word exact loop fingerprint,
    # the SHA gate for all 14 original banks and the source-qualified selected
    # scene across all original 1,5,7 memory samples.
    verification=tree.run(archive,SOURCE_CAPTURES)
    if (verification.get("status")!="SOURCE_LOOP_VERIFIED"
            or not verification.get("source_84_byte_tree_stride_verified")
            or verification.get("candidate_position_words_identical_across_selected_captures") is not True
            or len(verification.get("records",[]))!=len(SOURCE_CAPTURES)
            or any(r.get("tree_objects_source_count")!=EXPECTED_TREES
                   or not r.get("candidate_spatial_sanity_passed")
                   or r.get("finite_translation_triplets")!=EXPECTED_TREES
                   or r.get("distinct_candidate_translations")!=EXPECTED_TREES
                   for r in verification["records"])):
        raise ValueError("Original tree source/position comparison abstained")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            p=seven.src._file(folders[7],f"7.{i}.raw",size)
            handle=stack.enter_context(p.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(handle.fileno(),0,access=mmap.ACCESS_READ)))
        rd=seven.roster.TwoBankReader(*banks)
        selected=seven._get(rd)
        field=selected["field"]
        count=rd.u32(field+0x1C)
        array=rd.u32(field+0x20)
        if count!=EXPECTED_TREES or seven.roster._bank(
                array,EXPECTED_TREES*tree.TREE_SIZE)!="MEM2":
            raise ValueError("Original tree source array failed requalification")
        points=[]
        for i in range(EXPECTED_TREES):
            address=array+i*tree.TREE_SIZE+tree.TRANS_OFFSET
            points.append(tree.vec(rd,address))
        payload=make_payload(tuple(points))
    seven._check_archive(archive)  # no original RAM changed since sampling
    root=seven.src.selected.DATA_ROOT.resolve(strict=True)
    destination=write_private_payload(root,payload)
    return {
        "status":"PRIVATE_TREE_POSITION_JSON_EXPORTED",
        "count":EXPECTED_TREES,
        "source_84_byte_stride_verified":True,
        "positions_bitwise_stable_across_captures_1_5_7":True,
        "private_file":str(destination),
        "visible_tree_mesh_verified":False,
        "tree_collision_verified":False,
        "training_approved":False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        report=run(args.archive)
        print(json.dumps(report,sort_keys=True,separators=(",",":")))
        return 0
    except (OSError,ValueError,OverflowError,IndexError,KeyError,
            AttributeError,TypeError,struct.error):
        print('{"status":"ABSTAIN_NO_PRIVATE_TREE_EXPORT",'
              '"training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
