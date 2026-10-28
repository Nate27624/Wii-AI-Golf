#!/usr/bin/env python3
"""P0: bounded Rev1 Golf display/formatting callsite xrefs (offline, source only).

This maps *possible code path leads*, NOT the on-screen result producer.
Reuses #219 canonical private B0 SHA + RSPE01 Rev1 and public source-unit gates.
Never outputs native PPC words, raw RAM, private hashes, numeric gameplay values,
runtime pointers or user file paths; no Dolphin or controller interaction.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_ball_xyz_source_callers_private as base

# Exact Rev1 symbol entries from kiwi515/ogws_info/RSPE_r1.map.csv.
# These are POSSIBLE formatting, geometry and score callees, not a verified
# Hitting-the-Green rendering chain. Do not use xref proximity as causality.
CALLEES = (
    ("lyt_text_set_utf8_a", 0x8007C00C, "text"),
    ("lyt_text_set_utf8_b", 0x8007C074, "text"),
    ("c_snprintf", 0x800B7500, "format"),
    ("c_sprintf", 0x800B75D8, "format"),
    ("c_swprintf", 0x800BCE24, "format"),
    ("sys_message_get", 0x80190D90, "message"),
    ("vec_square_distance", 0x800E86D0, "geometry"),
    ("golf_calc_real_score", 0x8029CCBC, "score"),
    ("golf_update_scores", 0x8029CF24, "score"),
    ("golf_nth_hole_score", 0x8029CBD4, "score"),
    ("golf_nth_hole_strokes", 0x8029CC54, "score"),
    ("golf_is_training", 0x8029D3AC, "mode"),
)
TARGET = {address: (name, category) for name, address, category in CALLEES}
GOLF_PREFIX = "Pack/RPSports/RPGolScene/"
MAX_DISPLAY_SITES = 20
MAX_CLUSTERS = 32
# A finite, local code-offset bin merely ranks where to inspect next.
# Neither a function boundary nor evidence of dataflow / same execution path.
CLUSTER_WIDTH = 0x200


def golf_units(intervals):
    """Only the original published Golf source objects; skip other sports."""
    subset = tuple((start, end, name) for start, end, name in intervals
                   if name.startswith(GOLF_PREFIX))
    base.ensure(bool(subset)
                and any(name.endswith("RPGolScene_unsplit.o")
                        for _, _, name in subset)
                and all(0x80280000 <= start < end <= 0x802D0000
                        and start % 4 == 0 and end % 4 == 0
                        for start, end, _ in subset))
    return subset


def classify_calls(chunks):
    """Return only direct b/bl source-site metadata from supplied PPC words.

    chunks: iterable of (published_source_unit, unit_start_pc, native_bytes).
    A synthetic fixture has the same interface, no actual native RAM.
    """
    rows = []
    for name, start, data in chunks:
        base.ensure(name.startswith(GOLF_PREFIX)
                    and isinstance(start, int) and start % 4 == 0
                    and isinstance(data, bytes) and len(data) % 4 == 0)
        for offset in range(0, len(data), 4):
            pc = start + offset
            instruction = struct.unpack_from(">I", data, offset)[0]
            decoded = base.decode_ppc_branch(pc, instruction)
            if decoded is None:
                continue
            destination, linked = decoded
            if destination not in TARGET:
                continue
            callee, category = TARGET[destination]
            rows.append((name, offset, callee, category, linked, pc))
    return rows


def summarize(rows, scanned_units, scanned_words):
    known = {name for name, _, _ in CALLEES}
    base.ensure(all(row[2] in known and row[3] in
                    ("text", "format", "message", "geometry", "score", "mode")
                    and type(row[4]) is bool and
                    type(row[1]) is int and row[1] >= 0 and row[1] % 4 == 0
                    for row in rows))
    per_callee = []
    for name, _, category in CALLEES:
        calls = [r for r in rows if r[2] == name]
        linked = [r for r in calls if r[4]]
        per_callee.append({
            "public_symbol": name,
            "role_category_NOT_result_semantics": category,
            "direct_bl_count": len(linked),
            "direct_nonlink_b_count": len(calls) - len(linked),
            "source_sites": [
                {"source_file": unit,
                 "source_unit_relative_pc": f"+0x{offset:05X}"}
                for unit, offset, _, _, _, _ in linked[:MAX_DISPLAY_SITES]
            ],
            "omitted_bl_sites": max(0, len(linked) - MAX_DISPLAY_SITES),
        })

    grouped = defaultdict(list)
    for unit, offset, callee, category, linked, _ in rows:
        if linked:
            grouped[(unit, offset // CLUSTER_WIDTH)].append(
                (offset, callee, category))
    ranked = []
    for (unit, index), hits in grouped.items():
        categories = sorted({cat for _, _, cat in hits})
        # Prioritize groups containing a formatting sink, but never promote.
        sink = bool(set(categories) & {"text", "format", "message"})
        other = bool(set(categories) & {"geometry", "score", "mode"})
        ranked.append({
            "source_file": unit,
            "relative_window_start": f"+0x{index * CLUSTER_WIDTH:05X}",
            "relative_window_bytes": CLUSTER_WIDTH,
            "direct_bl_count": len(hits),
            "public_callees_in_window": sorted({call for _, call, _ in hits}),
            "categories": categories,
            "text_and_other_category_cooccur": sink and other,
            "cooccurrence_is_not_control_flow_or_dataflow_proof": True,
        })
    ranked.sort(key=lambda x: (
        -int(x["text_and_other_category_cooccur"]),
        -int(bool(set(x["categories"]) & {"text", "format", "message"})),
        -x["direct_bl_count"],
        x["source_file"],
        x["relative_window_start"],
    ))
    return {
        "kind": "P0-GOLF-RESULT-UI-SOURCE-XREF-TRIAGE-V1",
        "game_id": "RSPE01",
        "disc_revision": 1,
        "source_unit_family": GOLF_PREFIX,
        "published_golf_source_unit_count": scanned_units,
        "scanned_source_instruction_words": scanned_words,
        "original_b0_mem1_sha_gated": True,
        "direct_ppc_b_bl_only": True,
        "callees": per_callee,
        "source_windows_for_followup": ranked[:MAX_CLUSTERS],
        "omitted_windows": max(0, len(ranked) - MAX_CLUSTERS),
        "known_display_result_producer_identified": False,
        "live_ui_value_read_or_verified": False,
        "read_side_backing_memory_identified": False,
        "indirect_virtual_layout_and_custom_number_formatting_unresolved": True,
        "human_phase_labels_and_guest_frames_verified": False,
        "world_xyz_velocity_power_contact_score_units_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def audit(session: Path, data_root: Path):
    # The original PR #219 uses a signed private checkpoint manifest,
    # source-gated RSPE01 Rev1 header and immutable original bank SHA.
    bank = base.checked_private_b0(session, data_root)
    units = golf_units(base.load_public_text_units())
    chunks = []
    with bank.open("rb") as fh:
        base.ensure(fh.read(6) == base.GAME_ID)
        fh.seek(7)
        base.ensure(fh.read(1) == b"\x01")
        for start, end, name in units:
            base.ensure(start >= base.MEM1_START
                        and end <= base.MEM1_START + base.MEM1_LEN)
            fh.seek(start - base.MEM1_START)
            data = fh.read(end - start)
            base.ensure(len(data) == end - start and any(data))
            chunks.append((name, start, data))
    # Both before and after, compare original bank to B0's historical SHA.
    base.ensure(base.checked_private_b0(session, data_root) == bank)
    rows = classify_calls(chunks)
    return summarize(rows, len(units), sum((end - start) // 4
                                         for start, end, _ in units))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path,
                        help="Original ignored, archived B0 checkpoint folder")
    args = parser.parse_args(argv)
    try:
        data_root = (Path(__file__).resolve().parents[2] /
                     "Wii-AI-Golf-Data")
        report = audit(args.baseline, data_root)
    except (base.UntrustedInput, OSError, ValueError, TypeError,
            KeyError, IndexError, OverflowError, AttributeError):
        print("P0_GOLF_UI_XREF_ABSTAIN: canonical B0 source, public splits or "
              "code inspection not qualified", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
