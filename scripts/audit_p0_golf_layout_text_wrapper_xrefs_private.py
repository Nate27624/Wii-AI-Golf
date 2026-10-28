#!/usr/bin/env python3
"""P0 Golf result UI: exact source calls into layout text/message wrappers.

Rev1 public source symbol addresses (kiwi515/ogws_info headers). Only
original SHA-pinned private B0 MEM1 and existing published Golf text units.
Returns *code-unit-relative* callsite categories, never native instruction
words, message text, runtime addresses, captures or private metadata.
A static BL cannot prove result screen execution, dataflow or backing RAM.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_golf_result_ui_xrefs_private as source

base = source.base
# Public RSPE01 Rev1 headers:
# kiwi515/ogws_info/RP/RPKernel/RPSysLytTextBox.h
# kiwi515/ogws_info/RP/RPKernel/RPSysLayout.h
# Overload at +0x80198e24 is ambiguous with setScaleX in published header:
# deliberately OMIT that address pending independent source corroboration.
UI_ENTRIES = (
    ("layout_find_textbox", 0x80196280, "pane_lookup"),
    ("layout_create", 0x80196A38, "layout_create"),
    ("textbox_set_message_va", 0x80198FD0, "formatted_message"),
    ("textbox_set_message_variadic", 0x80199148, "formatted_message"),
    ("textbox_set_text_variadic", 0x8019931C, "formatted_text"),
)
TARGETS = {addr: (name, category) for name, addr, category in UI_ENTRIES}
MAX_CALLS = 32
CLUSTER = 0x400
MAX_CLUSTER_OUTPUT = 24

def source_calls(chunks):
    """Source list (published file, public object-file start PC, bytes)."""
    rows = []
    for name, start, blob in chunks:
        base.ensure(name.startswith(source.GOLF_PREFIX)
                    and type(start) is int and start % 4 == 0
                    and type(blob) is bytes and len(blob) % 4 == 0)
        for off in range(0, len(blob), 4):
            pc = start + off
            word = struct.unpack_from(">I", blob, off)[0]
            edge = base.decode_ppc_branch(pc, word)
            if edge is None:
                continue
            dest, linked = edge
            if dest in TARGETS:
                label, category = TARGETS[dest]
                rows.append((name, off, label, category, linked))
    return rows

def summarise(rows: list, source_unit_count: int):
    allowed = {(name, cat) for name, _, cat in UI_ENTRIES}
    base.ensure(type(rows) is list
                and type(source_unit_count) is int
                and source_unit_count > 0
                and all(len(r)==5 and (r[2], r[3]) in allowed
                        and type(r[1]) is int and r[1] % 4 == 0
                        and type(r[4]) is bool
                        for r in rows))
    by_entry = []
    for name, _pc, category in UI_ENTRIES:
        calls = [r for r in rows if r[2] == name]
        linked = [r for r in calls if r[4]]
        by_entry.append({
            "public_ui_method": name,
            "method_role_not_result_identity": category,
            "direct_bl_count": len(linked),
            "nonlink_b_count": len(calls) - len(linked),
            "published_golf_source_relative_call_sites": [
                {"source_unit": unit, "code_offset": f"+0x{off:05X}"}
                for unit, off, _, _, _ in linked[:MAX_CALLS]
            ],
            "omitted_bl_sites": max(0, len(linked) - MAX_CALLS),
        })

    buckets = defaultdict(list)
    for unit, off, label, category, linked in rows:
        if linked:
            buckets[(unit, off // CLUSTER)].append((label, category))
    windows = []
    for (unit, bin_no), calls in buckets.items():
        cats = {cat for _, cat in calls}
        windows.append({
            "source_unit": unit,
            "code_window_relative_start": f"+0x{bin_no*CLUSTER:05X}",
            "window_size_bytes": CLUSTER,
            "calls_in_window": len(calls),
            "methods": sorted({name for name, _ in calls}),
            "find_textbox_and_formatted_text_in_same_window":
                "pane_lookup" in cats
                and bool(cats & {"formatted_message", "formatted_text"}),
            "source_window_cooccurrence_not_callgraph_or_value_proof": True,
        })
    windows.sort(key=lambda x: (
        -int(x["find_textbox_and_formatted_text_in_same_window"]),
        -x["calls_in_window"], x["source_unit"],
        x["code_window_relative_start"],
    ))
    return {
        "kind": "P0-REV1-GOLF-LAYOUT-TEXT-WRAPPER-EXACT-XREF-V1",
        "game_id": "RSPE01",
        "disc_revision": 1,
        "original_private_b0_mem1_manifest_sha_verified": True,
        "golf_public_source_unit_count": source_unit_count,
        "source_is_static_direct_ppc_b_bl_only": True,
        "public_ui_methods": by_entry,
        "candidate_source_windows": windows[:MAX_CLUSTER_OUTPUT],
        "omitted_candidate_windows": max(0, len(windows) - MAX_CLUSTER_OUTPUT),
        "nearby_calls_are_not_same_function_proof": True,
        "indirect_virtual_calls_unresolved": True,
        "hitting_green_ui_producer_verified": False,
        "displayed_distance_value_or_units_verified": False,
        "typed_backing_memory_field_verified": False,
        "same_guest_frame_result_event_verified": False,
        "ball_xyz_velocity_power_contact_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }

def audit(session: Path, data_root: Path):
    # Original #219 trust anchor (canonical checkpoint manifest + B0 SHA).
    bank = base.checked_private_b0(session, data_root)
    units = source.golf_units(base.load_public_text_units())
    rows = []
    with bank.open("rb") as stream:
        base.ensure(stream.read(6) == base.GAME_ID)
        stream.seek(7)
        base.ensure(stream.read(1) == b"\x01")
        for start, end, name in units:
            stream.seek(start - base.MEM1_START)
            data = stream.read(end - start)
            base.ensure(len(data) == end - start and any(data))
            rows.extend(source_calls([(name, start, data)]))
    base.ensure(base.checked_private_b0(session, data_root) == bank)
    return summarise(rows, len(units))

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        root = Path(__file__).resolve().parents[2] / "Wii-AI-Golf-Data"
        answer = audit(args.baseline, root)
    except (base.UntrustedInput, OSError, ValueError, TypeError,
            KeyError, IndexError, OverflowError, AttributeError):
        print("P0_LAYOUT_UI_ABSTAIN: original B0 source or published Rev1 code not qualified",
              file=sys.stderr)
        return 2
    print(json.dumps(answer, indent=2, sort_keys=True, allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
