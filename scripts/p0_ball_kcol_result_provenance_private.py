#!/usr/bin/env python3
"""Read-only native Ball/KCol classification producer and Ball-vector use trace.

Continuation of the source-qualified material audit. Reads original
RSPE01 Rev1 seven-pair archive, requires source scene/SHA, verified
94x84 FieldManager tree loop, the exact 5 Ball->GolfKCol and 7 reverse
calls, and previous native material-return PPC anchors BEFORE emitting
any code windows. No game-memory writes, Dolphin, or new captures.

The selected windows are bounded *syntax*, not proof that class 13 is a
tree, that a query result is a contact, or that Ball +0xAC/B0/B4 is
velocity. --detail prints source-relative native code ONLY to the
operator's local console. Do not upload native code/ROM or RAM data to Git.
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
import p0_ball_kcol_material_branch_private as previous
import p0_tree_hitbox_source_callgraph_private as units
import p0_tree_hitbox_five_calls_private as decoder

MEM1 = 0x80000000
# The earlier audit leaves these exact source-relative ranges unexamined.
# Deliberately include the *whole* KCol narrowphase result-commit tail
# to follow output halfwords back to a prism, result, or sentinel.
WINDOWS = (
    ("ball_special_event_helper_tail", "Ball", 0x0220, 0x0300),
    ("ball_postmask_vector_setup", "Ball", 0x0C98, 0x0D60),
    ("ball_hit_loop_exit", "Ball", 0x0E68, 0x0F40),
    ("ball_vector_reader_writer_context", "Ball", 0x34F0, 0x35CC),
    ("kcol_main_query_output", "GolfKCol", 0x0000, 0x0120),
    ("kcol_prism_flag_accessors", "GolfKCol", 0x0194, 0x01D8),
    ("kcol_triangle_result_commit", "GolfKCol", 0x2240, 0x26C0),
)
MAX_SOURCE_WORDS = 620
assert sum((end-start)//4 for _,_,start,end in WINDOWS) <= MAX_SOURCE_WORDS


def inspect(read, detail=False):
    """Require *all* previous original PPC/call gates, then inspect windows."""
    upstream = previous.inspect(read, detail=False)
    if not (
        upstream["original_five_ball_queries_exactly_qualified"]
        and upstream["original_seven_kcol_inverse_calls_qualified"]
        and not upstream["ball_velocity_field_semantics_proven"]
        and not upstream["native_tree_contact_dispatch_proven"]
    ):
        raise ValueError("Original Ball/KCol source provenance changed")

    rows = []
    words_total = 0
    for name, owner, start, end in WINDOWS:
        lo, hi = units.UNITS[owner]
        if start < 0 or start % 4 or end % 4 or end <= start or lo+end > hi:
            raise ValueError("Source-relative window outside proven code unit")
        count = (end-start)//4
        words_total += count
        if words_total > MAX_SOURCE_WORDS:
            raise ValueError("Native source output cap exceeded")

        summary = Counter()
        lines = []
        for offset in range(start, end, 4):
            pc = lo + offset
            word = read(pc)
            op = word >> 26
            if op in (10, 11):
                summary["integer_compares"] += 1
            elif op == 16:
                summary["conditional_branches"] += 1
            elif op == 18:
                summary["direct_branches"] += 1
            elif op in (40, 42):
                summary["halfword_reads"] += 1
            elif op == 44:
                summary["halfword_writes"] += 1
            elif op in (48, 49, 50):
                summary["float_reads"] += 1
            elif op in (52, 53, 54):
                summary["float_writes"] += 1
            if detail:
                lines.append(
                    f"{owner}+0x{offset:04X}  {word:08X}  "
                    f"{decoder.ppc(pc, word)}"
                )
        item = {
            "region": name,
            "source_unit": owner,
            "relative_span": f"+0x{start:04X}..+0x{end-4:04X}",
            "instruction_count": count,
            "syntactic_counts": dict(sorted(summary.items())),
            "classification_producer_identified": False,
            "ball_vector_receiver_verified": False,
        }
        if detail:
            item["native_code_lines_local_only"] = lines
        rows.append(item)
    return {
        "kind": "P0_BALL_KCOL_RESULT_PROVENANCE_SOURCE",
        "status": "CLASSIFICATION_PRODUCER_AND_VECTOR_CONSUMERS_UNDER_REVIEW",
        "windows": rows,
        "total_native_source_words": words_total,
        "earlier_exact_material_and_call_gates_passed": True,
        "classification_13_tree_event_proven": False,
        "ball_velocity_field_semantics_proven": False,
        "tree_hitbox_geometry_verified": False,
        "training_approved": False,
    }


def run(archive: Path, capture: int, detail: bool):
    if capture not in range(1, 8):
        raise ValueError("Only original seven source captures supported")
    folders = seven._check_archive(archive)
    with ExitStack() as stack:
        banks = []
        for index, size in enumerate(seven.SIZE, 1):
            file = seven.src._file(
                folders[capture], f"{capture}.{index}.raw", size)
            handle = stack.enter_context(file.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)))
        reader = seven.roster.TwoBankReader(*banks)
        field = seven._get(reader)["field"]
        count = reader.u32(field+0x1C)
        array = reader.u32(field+0x20)
        if count != 94 or seven.roster._bank(array, count*84) != "MEM2":
            raise ValueError("Original source 94x84 tree array failed")
        def read(pc):
            if pc < MEM1 or pc+4 > MEM1+len(banks[0]):
                raise ValueError("Original native code outside MEM1")
            return struct.unpack_from(">I", banks[0], pc-MEM1)[0]
        if not units.tree_loop_source_gated(read):
            raise ValueError("Original FieldManager tree loop mismatch")
        report = inspect(read, detail)
    seven._check_archive(archive)
    return {
        "capture": capture,
        "original_archive_sha_scene_and_84_stride_verified": True,
        "source_trees": 94,
        **report,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--capture", type=int, choices=range(1, 8), default=7)
    p.add_argument("--detail", action="store_true")
    args = p.parse_args(argv)
    try:
        report = run(args.archive, args.capture, args.detail)
        if args.detail:
            print(json.dumps(
                {k:v for k,v in report.items() if k != "windows"},
                sort_keys=True, separators=(",", ":")))
            for item in report["windows"]:
                print(f"===== {item['region']} {item['relative_span']} =====")
                print("\n".join(item["native_code_lines_local_only"]))
            print("===== END BOUNDED RESULT PROVENANCE WINDOWS =====")
        else:
            print(json.dumps(
                report, sort_keys=True, separators=(",", ":"), allow_nan=False))
        return 0
    except (ValueError, OSError, IndexError, TypeError, OverflowError,
            AttributeError, KeyError, struct.error):
        print('{"status":"ABSTAIN_BALL_KCOL_RESULT_PROVENANCE",'
              '"training_approved":false}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
