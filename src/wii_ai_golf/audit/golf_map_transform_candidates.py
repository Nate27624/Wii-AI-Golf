"""Offline candidate-only golf pin/start transforms from S002's paired bank gate.

Research stack depends on PR #151 golf_cross_bank_state, not another live
collector. Source member annotations are internally contradictory beyond +0x3C;
DO NOT dereference supposed +0x40/+0x44 map-object pointer members.
Actual position semantics, class inheritance and MEM1/MEM2 snapshot atomicity
are unverified. Candidate floats are returned only in a SEPARATE PRIVATE result.
"""
from __future__ import annotations

from contextlib import ExitStack
import math
import mmap
from pathlib import Path
import struct

from .golf_cross_bank_state import (
    _Banks, audit_pair, MEM1_SIZE, MEM2_SIZE, STATIC_FIELD,
)

# Source: kiwi515/ogws_info/RPGolMapObjBase.h, candidate-only.
BASE_TRANSLATION_OFFSET = 0x30
BASE_MAPOBJ_POINTER_OFFSET = 0x08
# This is **on-disk** PMP map entry documentation (not proven runtime object).
PMP_POSITION_OFFSET = 0x08
FIELD_SELECTED = {"pin": 0x44, "start": 0x50}
POSSIBLE_GOLF_MAP_DATA_RANGES = (
    (0x803C77E8, 0x803C77F8),  # RPGolMapObjBase.cpp .data
    (0x803C77F8, 0x803C78E8),  # RPGolFieldManager.cpp .data
)
MAX_COORD = 100_000.0
AGREEMENT_TOLERANCE = 0.1


def _candidate_vec(banks, address: int):
    if banks.region(address, 12) not in ("MEM1", "MEM2"):
        return None
    values = struct.unpack(">fff", banks.read(address, 12))
    if not all(math.isfinite(x) and abs(x) <= MAX_COORD for x in values):
        return None
    return values


def inspect_named_map_object(banks, address: int) -> tuple[dict, dict]:
    """Bounded source *hypotheses*. Never assert pointer is derived Base class."""
    if banks.region(address, 0x3C) != "MEM2":
        raise ValueError("Selected map candidate requires bounded MEM2 object")
    first = banks.u32(address)
    data_hint = any(a <= first < b for a, b in POSSIBLE_GOLF_MAP_DATA_RANGES)
    v = _candidate_vec(banks, address + BASE_TRANSLATION_OFFSET)
    map_pointer = banks.u32(address + BASE_MAPOBJ_POINTER_OFFSET)
    map_region = banks.region(map_pointer, 0x14)
    # PMP file layout uses +0x08; runtime RPUtlMapObject layout is UNKNOWN.
    m = (_candidate_vec(banks, map_pointer + PMP_POSITION_OFFSET)
         if map_region else None)
    similar = (v is not None and m is not None
               and max(abs(a - b) for a, b in zip(v, m)) <= AGREEMENT_TOLERANCE)
    plaus = lambda vv: vv is not None and any(abs(x) >= 1e-3 for x in vv)
    safe = {
        "selected_object_in_mem2": True,
        "first_word_in_map_object_module_data_range": data_hint,
        "base_plus_0x30_triplet_finite_and_bounded": v is not None,
        "base_plus_0x30_triplet_nonzero": plaus(v),
        "base_mMapObj_plus_0x08_pointer_readable": map_region is not None,
        "hypothetical_pmp_plus_0x08_triplet_finite_and_bounded": m is not None,
        "hypothetical_pmp_plus_0x08_triplet_nonzero": plaus(m),
        "two_unverified_triplets_agree_within_tolerance": similar,
    }
    private = {
        "base_plus_0x30_candidate_floats": list(v) if v is not None else None,
        "hypothetical_map_entry_plus_0x08_floats": list(m) if m is not None else None,
    }
    return safe, private


def audit_paired_map_candidates(mem1, mem2) -> tuple[dict, dict]:
    """Strict previous source gate then two small source-shaped candidate windows.

    Safe report may be pasted into an issue only after owner's publication review.
    Private report is for local research only and MUST NOT enter GitHub.
    """
    verified = audit_pair(mem1, mem2, strict_size=True)
    if verified["source_chain"]["current_golf_scene_region"] != "MEM2":
        raise ValueError("Expected source-supported Golf scene in MEM2")
    banks = _Banks(mem1, mem2)
    field = banks.u32(STATIC_FIELD)
    if banks.region(field, 0xA8) != "MEM2":
        raise ValueError("Expected field manager in MEM2")
    safe = {}
    private = {}
    for name, offset in FIELD_SELECTED.items():
        target = banks.u32(field + offset)
        safe[name], private[name] = inspect_named_map_object(banks, target)
    vecs = [private[k]["base_plus_0x30_candidate_floats"]
            for k in ("pin", "start")]
    both = all(v is not None for v in vecs)
    separation = (math.dist(vecs[0], vecs[1]) if both else None)
    return {
        "kind": "local-golf-map-transform-hypotheses",
        "schema_version": 1,
        "game_id": "RSPE01",
        "revision": 1,
        "mode": 4,
        "input_mem1_exact_size": len(mem1) == MEM1_SIZE,
        "input_mem2_exact_size": len(mem2) == MEM2_SIZE,
        "golf_source_chain_gated": True,
        "selected_objects": safe,
        "both_base_translation_candidates_present": both,
        "candidate_vectors_separated_by_nonzero_distance":
            separation is not None and separation >= 0.01,
        "mapobj_base_documented_offset_overlap": True,
        "source_known_derived_class_inheritance": False,
        "runtime_pmp_layout_verified": False,
        "same_boot_proven": False,
        "same_emulated_frame_proven": False,
        "pin_world_xyz_verified": False,
        "start_world_xyz_verified": False,
        "live_ball_xyz_verified": False,
        "wind_vector_verified": False,
        "approved_for_model_training": False,
        "warning": ("Finite numbers and module-data hints do NOT establish world coordinates. "
                    "RPGolMapObjBase VEC3 scale annotations overlap purported later pointer "
                    "annotations; do not dereference +0x40/+0x44. Position candidates "
                    "are untyped until S002 confirms subclass/member access via DOL."),
    }, {
        "kind": "PRIVATE-UNVERIFIED-golf-map-transform-floats",
        "selected_objects": private,
        "candidate_pin_start_separation_unverified": separation,
        "no_asserted_physical_units": True,
        "not_for_publication": True,
    }


def audit_local_pair(mem1_path, mem2_path, *, private_root, private_output):
    """Mmap existing user-owned banks; private float report only, never overwrite."""
    root = Path(private_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Not a private directory")
    bankpaths = []
    for path, size in ((Path(mem1_path), MEM1_SIZE), (Path(mem2_path), MEM2_SIZE)):
        if (path.is_symlink() or not path.is_file()
                or path.suffix.lower() not in (".raw", ".bin", ".mem")):
            raise ValueError("Wrong private native bank type")
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root) or path.stat().st_size != size:
            raise ValueError("Private bank must have exact supported size")
        bankpaths.append(resolved)
    if len(set(bankpaths)) != 2:
        raise ValueError("Two different memory bank files are needed")
    output = Path(private_output)
    if (output.is_symlink() or output.exists()
            or not output.name.endswith("-PRIVATE.json")
            or output.parent.resolve(strict=True) != root):
        raise ValueError("New PRIVATE report in private root required")
    with ExitStack() as stack:
        streams = [stack.enter_context(open(path, "rb")) for path in bankpaths]
        banks = [stack.enter_context(mmap.mmap(
            stream.fileno(), 0, access=mmap.ACCESS_READ)) for stream in streams]
        safe, private = audit_paired_map_candidates(*banks)
    import json
    with output.open("x", encoding="utf-8") as stream:
        json.dump(private, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return safe
