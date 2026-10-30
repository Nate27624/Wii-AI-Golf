#!/usr/bin/env python3
"""Source-qualified private tree array indirection falsification (read-only).

Tests whether RPGolFieldManager+0x20 is a pointer table to individual tree
objects. Emits categorical counts, no RAM addresses, original positions,
pointer values, raw bytes, hashes, filename or object identity.
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

SCRIPT_DIR = str(Path(__file__).resolve().parent)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import audit_p0_seven_numbered_source_pairs_private as seven

TABLE_STRIDES = (4, 8, 12, 16, 20, 24, 32, 40, 48)
TABLE_OFFSETS = (0, 4, 8, 12)
MAX_TREES = 4096
# Pos vectors and code/vtables are candidate tests only; they do not establish
# the native visual model identity or validated collision obstacle physics.


def finite_vec(v):
    return len(v) == 3 and all(math.isfinite(x) and abs(x) < 1e7 for x in v)


def check_table(word, vec, bank, base, count, stride, offset):
    """One table shape: returns fixed-enum, count-only diagnostics."""
    if type(count) is not int or not 3 <= count <= MAX_TREES:
        return None
    if stride not in TABLE_STRIDES or offset not in TABLE_OFFSETS or offset >= stride:
        return None
    if not bank(base, (count - 1) * stride + offset + 4, "MEM2"):
        return None
    counters = Counter()
    vt = Counter()
    places = set()
    addresses = set()
    for i in range(count):
        ref = word(base + i * stride + offset)
        if ref == 0:
            counters["null_entries"] += 1
            continue
        if not bank(ref, 0x50, "MEM2"):
            counters["invalid_object_pointer"] += 1
            continue
        if ref in addresses:
            counters["reused_object_pointer"] += 1
            continue
        addresses.add(ref)
        counters["valid_object_pointers"] += 1
        candidate_vt = word(ref)
        if not bank(candidate_vt, 8, "MEM1"):
            counters["bad_vtable_pointer"] += 1
            continue
        # Vtable address must point to plausible code references, not merely
        # an arbitrary nonzero integer somewhere in main RAM.
        entry0, entry1 = word(candidate_vt), word(candidate_vt + 4)
        if not (bank(entry0, 4, "MEM1") or bank(entry1, 4, "MEM1")):
            counters["vtable_no_code_refs"] += 1
            continue
        vt[candidate_vt] += 1
        counters["plausible_vtables"] += 1
        point = vec(ref + 0x30)
        if not finite_vec(point):
            counters["invalid_translation"] += 1
            continue
        counters["finite_translations"] += 1
        places.add(tuple(round(x, 3) for x in point))
        # Do not require self-ref: for tee, +0x4C->+0x30 was independently
        # confirmed, but the tree subclass's pointer offset is unproven.
        if word(ref + 0x4C) == ref + 0x30:
            counters["base_translation_selfref_4C"] += 1
        if word(ref + 0x44) == ref + 0x30:
            counters["base_translation_selfref_44"] += 1
    top2 = sum(n for _, n in vt.most_common(2))
    count_all = counters["valid_object_pointers"]
    valid_vt = counters["plausible_vtables"]
    finite = counters["finite_translations"]
    unique_pos = len(places)
    candidate = (count_all >= math.ceil(count * .85)
                 and valid_vt >= math.ceil(count * .80)
                 and top2 >= math.ceil(count * .75)
                 and finite >= math.ceil(count * .75)
                 and unique_pos >= min(12, math.ceil(count*.25)))
    return {
        "table_stride_bytes": stride,
        "table_pointer_offset_bytes": offset,
        "source_count": count,
        "unique_object_pointers": count_all,
        "plausible_vtable_objects": valid_vt,
        "top_two_vtable_objects": top2,
        "finite_translation_objects": finite,
        "distinct_translation_candidates": unique_pos,
        "selfref_plus_0x4c_matches": counters["base_translation_selfref_4C"],
        "selfref_plus_0x44_matches": counters["base_translation_selfref_44"],
        "null_entries": counters["null_entries"],
        "duplicate_entries": counters["reused_object_pointer"],
        "pointer_table_hypothesis_pass": candidate,
        "tree_location_verified": False,
    }


def study(word, vec, bank, base, count):
    """Rank a bounded layout set, abstain on underdetermined pointer data."""
    rows = [r for stride in TABLE_STRIDES for off in TABLE_OFFSETS
            if (r := check_table(word, vec, bank, base, count, stride, off)) is not None]
    rows.sort(key=lambda r: (
        -int(r["pointer_table_hypothesis_pass"]),
        -r["top_two_vtable_objects"],
        -r["plausible_vtable_objects"],
        -r["finite_translation_objects"],
        -r["unique_object_pointers"],
        r["table_stride_bytes"],
        r["table_pointer_offset_bytes"]))
    qualified = [r for r in rows if r["pointer_table_hypothesis_pass"]]
    return {
        "status": ("POINTER_TABLE_STRUCTURAL_CANDIDATE"
                   if len(qualified) == 1
                   else "POINTER_TABLE_AMBIGUOUS" if qualified
                   else "POINTER_TABLE_UNRESOLVED"),
        "qualified_table_hypotheses": qualified[:5],
        "top_unqualified_hypotheses": [] if qualified else rows[:4],
        "actual_tree_coordinates_verified": False,
        "actual_tree_models_verified": False,
        "source_course_transform_verified": False,
        "training_approved": False,
    }


def run(archive: Path, captures: tuple[int, ...]):
    if not captures or any(n not in range(1, 8) for n in captures):
        raise ValueError("unsupported capture")
    seven._check_archive(archive)  # Original seven-pair SHA inventory gate
    reports = []
    for capture in captures:
        with ExitStack() as stack:
            original = []
            for i, size in enumerate(seven.SIZE, 1):
                path = seven.src._file(archive, f"{capture}.{i}.raw", size)
                handle = stack.enter_context(path.open("rb"))
                original.append(stack.enter_context(
                    mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)))
            rd = seven.roster.TwoBankReader(*original)
            source = seven._get(rd)  # Rev1, scene, owner, selected ball, tee/pin
            field = source["field"]
            count = rd.u32(field + 0x1C)
            base = rd.u32(field + 0x20)
            if not 3 <= count <= MAX_TREES or seven.roster._bank(base, 4) != "MEM2":
                raise ValueError("Source tree array missing or unbounded")
            def bank(p, width, name):
                return seven.roster._bank(p, width) == name
            def vec(at):
                return tuple(struct.unpack(">f", rd.u32(at + 4*j).to_bytes(4,"big"))[0]
                             for j in range(3))
            reports.append({
                "capture": capture,
                "source_tree_count": count,
                "source_array_bounded": True,
                **study(rd.u32, vec, bank, base, count)
            })
    seven._check_archive(archive)  # Entire archive bytes stable post-analysis
    return {"kind": "P0_PRIVATE_GOLF_TREE_POINTER_TABLE_FALSIFICATION",
            "status": "SOURCE_GATED_LAYOUT_REPORT",
            "reports": reports, "training_approved": False}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--captures", nargs="+", type=int, default=[7])
    args=ap.parse_args(argv)
    try:
        print(json.dumps(run(args.archive, tuple(args.captures)),
                         sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, IndexError, KeyError, TypeError, OverflowError,
            AttributeError, struct.error):
        print(json.dumps({"kind":"P0_PRIVATE_GOLF_TREE_POINTER_TABLE_FALSIFICATION",
                          "status":"ABSTAIN_SOURCE_OR_ARCHIVE_GATE",
                          "training_approved":False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
