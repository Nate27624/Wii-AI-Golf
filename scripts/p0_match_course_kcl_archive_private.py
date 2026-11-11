#!/usr/bin/env python3
"""Match an original private Wii Sports Golf KCL OBJ to extracted disc KCLs.

This source-only diagnostic identifies the original archive whose collision
triangles match the captured memory KCL candidate. It does NOT infer a
game course index from an FC file number, or assume visual/world registration.
No raw KCL/OBJ coordinates, derived geometry hashes, or personal paths print.
No data is written or uploaded and no game or RAM process is accessed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct
import sys

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SRC = SCRIPTS.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import p0_kcl_private_probe as source_kcl
from wii_ai_golf.inspector.terrain import load_private_obj

MAX_KCL_BYTES = 32 * 1024 * 1024
MAX_KCL_FILES = 96
MAX_PRISMS = 30000
MAX_TRIANGLES = 30000
COURSE_PATTERN = re.compile(r"glf_course_(?:fc\d+|E3|angle|survey)", re.I)


def _key(a, b, c):
    # Same 9-significant-digit format used in original source RAM->private
    # OBJ export. Sorted corners + Counter make prism order irrelevant.
    return tuple(sorted(
        tuple(format(float(v), ".9g") for v in p)
        for p in (a, b, c)
    ))


def original_obj_signature(mesh):
    if not 1 <= len(mesh.faces) <= MAX_TRIANGLES:
        raise ValueError("Invalid original private OBJ face count")
    return Counter(_key(*(mesh.vertices[v] for v in tri))
                   for tri in mesh.faces)


def compare_extracted_kcl(data: bytes, obj_sig: Counter,
                          expected_faces: int) -> dict:
    """Compare all original source prisms to private OBJ; no positions output."""
    if len(data) > MAX_KCL_BYTES or len(data) < 0x80:
        return {"status": "ABSTAIN_KCL_FILE_SIZE"}
    header = source_kcl.parse_kcl_candidate(data, 0)
    if header is None:
        return {"status": "KCL_HEADER_NOT_SUPPORTED"}
    count = header["prism_count_upper_bound"]
    if count != expected_faces:
        return {"status": "ORIGINAL_PRISM_COUNT_DIFFERS",
                "original_prism_count": count}
    if count > MAX_PRISMS:
        return {"status": "ABSTAIN_KCL_PRISM_COUNT_BOUND"}
    try:
        po, no, prism_offset, _ = struct.unpack_from(">IIII", data, 0)
        positions = [
            source_kcl._v3(data, po+12*i)
            for i in range((no-po)//12)]
        normals = [
            source_kcl._v3(data, no+12*i)
            for i in range((prism_offset+0x10-no)//12)]
        archive_sig = Counter()
        for i in range(count):
            tri = source_kcl._triangle(
                data, 0, positions, normals, prism_offset, i)
            if tri is None:
                return {"status": "ABSTAIN_MALFORMED_SOURCE_PRISM"}
            archive_sig[_key(*tri[:3])] += 1
    except (ValueError, TypeError, OverflowError, struct.error, IndexError):
        return {"status": "ABSTAIN_KCL_RECONSTRUCTION"}
    return {
        "status": (
            "EXACT_ALL_SOURCE_TRIANGLES_MATCH"
            if archive_sig == obj_sig
            else "SOURCE_PRISM_GEOMETRY_DIFFERS"),
        "original_prism_count": count,
        "order_independent_9_significant_digit_comparison": True,
    }


def inspect_extracts(obj: Path, extracted_root: Path) -> dict:
    if (not extracted_root.is_dir() or extracted_root.is_symlink()
            or not extracted_root.is_absolute()):
        raise ValueError("Original extracted archive root unavailable")
    mesh = load_private_obj(obj)
    obj_sig = original_obj_signature(mesh)
    # Restrict the search to an explicitly named private "unpacked" root.
    # A broad disk crawl or publication of filenames is not intended.
    if extracted_root.name != "unpacked":
        raise ValueError("Expected private unpacked original archive root")
    files = sorted(p for p in extracted_root.rglob("*.kcl")
                   if p.is_file() and not p.is_symlink())
    if len(files) > MAX_KCL_FILES:
        raise ValueError("Too many private KCL files; narrow your root")
    candidate_results = []
    for path in files:
        match = COURSE_PATTERN.search(str(path.relative_to(extracted_root)))
        if not match:
            continue
        try:
            if path.stat().st_size > MAX_KCL_BYTES:
                status = {"status": "ABSTAIN_KCL_FILE_SIZE"}
            else:
                status = compare_extracted_kcl(
                    path.read_bytes(), obj_sig, len(mesh.faces))
        except OSError:
            status = {"status": "ABSTAIN_ORIGINAL_KCL_FILE_READ"}
        candidate_results.append({
            "archive_candidate": match.group(0),
            **status,
        })
    matches = [item for item in candidate_results
               if item["status"] == "EXACT_ALL_SOURCE_TRIANGLES_MATCH"]
    return {
        "status": (
            "ONE_EXACT_ORIGINAL_ARCHIVE_KCL_MATCH" if len(matches) == 1
            else "AMBIGUOUS_MULTIPLE_ORIGINAL_ARCHIVE_KCL_MATCHES"
            if matches else "NO_EXACT_SOURCE_KCL_MATCH_FOUND"),
        "source_obj_triangle_count": len(mesh.faces),
        "original_disc_kcl_files_checked": len(candidate_results),
        "exact_matched_archive_candidates": sorted({
            x["archive_candidate"] for x in matches}),
        "candidates": candidate_results,
        "game_live_collision_owner_verified": False,
        "native_visual_to_collision_transform_verified": False,
        "training_approved": False,
        "private_geometry_or_asset_bytes_published": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terrain-obj", type=Path, required=True)
    parser.add_argument("--unpacked-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = inspect_extracts(args.terrain_obj, args.unpacked_root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, RuntimeError, TypeError):
        print(json.dumps({
            "status": "ABSTAIN_INVALID_PRIVATE_ORIGINAL_SOURCE",
            "training_approved": False,
            "private_geometry_or_asset_bytes_published": False,
        }))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
