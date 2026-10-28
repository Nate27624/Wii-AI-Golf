"""S002 source-only Rev1 PPC index-arithmetic review for disputed GolfConfig scores.

The independent public source headers disagree: kiwi515/ogws_info declares
mPlayerScores[4][9]; PackProject/Kokeshi declares mStrokeTotal[9][4].
Both agree on 36 u32 words at +0x04 and two getters' source addresses.

This script does NOT choose the correct layout by trusting either header.
It reads only two pinned PUBLIC source-code function ranges from original
14-bank-SHA-verified numbered archive's MEM1. Output contains opcode
class/source-relative sites only, never native instruction words, numeric
scores, pointer values, private filenames or snapshot hashes.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys

import audit_p0_seven_numbered_source_pairs_private as seven
import audit_golf_two_bank_roster_private as roster

MEM1_BASE = roster.MEM1_BASE
CONFIG_UNIT_BOUNDS = (0x8029CA4C, 0x8029E62C)  # ogws pinned RSPE01_01 splits
FUNCTIONS = (
    ("get_nth_hole_score", 0x8029CBD4, 0x8029CC54),
    ("get_nth_hole_strokes", 0x8029CC54, 0x8029CCBC),
)
INTERESTING_IMMS = frozenset({4, 9, 16, 36})
MAX_OPS_PER_FUNCTION = 36


def instruction_clue(word: int, index: int):
    """Return only recognized *PPC source CODE* arithmetic syntax.

    No semantic promotion; register definitions across calls/branches
    and signed multiplications may require full CFG to resolve.
    """
    if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
        raise ValueError("bad PPC instruction word")
    if type(index) is not int or index < 0 or index % 4:
        raise ValueError("bad bounded function-relative offset")
    op = word >> 26
    rt = (word >> 21) & 31
    ra = (word >> 16) & 31
    rb = (word >> 11) & 31
    xo = (word >> 1) & 1023
    disp = word & 0xFFFF
    if disp & 0x8000:
        disp -= 0x10000
    out = {"function_relative_site":f"+0x{index:02X}"}
    if op == 7:  # mulli
        out.update(opcode_class="mulli",dest=f"r{rt}",
                   sources=[f"r{ra}"],
                   source_immediate=disp if disp in INTERESTING_IMMS else None)
    elif op == 21:  # rlwinm, includes slwi
        sh = rb
        mask_begin = (word >> 6) & 31
        mask_end = (word >> 1) & 31
        out.update(opcode_class=("slwi" if mask_begin == 0
                                and mask_end == 31 - sh else "rlwinm"),
                   dest=f"r{ra}",sources=[f"r{rt}"],
                   source_shift=sh)
    elif op == 31 and xo in (266, 235):  # add, mullw
        out.update(opcode_class="add" if xo == 266 else "mullw",
                   dest=f"r{rt}",sources=[f"r{ra}",f"r{rb}"])
    elif op in (14, 15) and disp in INTERESTING_IMMS:
        out.update(opcode_class="addi" if op == 14 else "addis",
                   dest=f"r{rt}",sources=[f"r{ra}"],
                   source_immediate=disp)
    elif op in (32, 36) and disp in (0, 4, 8, 12, 16):
        out.update(opcode_class="lwz" if op == 32 else "stw",
                   dest_or_value=f"r{rt}",base=f"r{ra}",
                   source_relative_member_offset=disp)
    elif word == 0x4E800020:
        out["opcode_class"] = "blr"
    elif op in (16, 18):
        out["opcode_class"] = "branch"
        out["linked"] = bool(word & 1)
    else:
        return None
    return out


def summarize_source_windows(windows: dict[str, bytes]) -> dict:
    if type(windows) is not dict or set(windows) != {n for n, _, _ in FUNCTIONS}:
        raise ValueError("unknown source functions")
    rows = []
    for name, start, end in FUNCTIONS:
        data = windows[name]
        if type(data) is not bytes or len(data) != end - start or len(data) % 4:
            raise ValueError("wrong source function boundary")
        candidates = []
        for index in range(0, len(data), 4):
            word = struct.unpack_from(">I", data, index)[0]
            clue = instruction_clue(word, index)
            if clue is not None:
                if len(candidates) >= MAX_OPS_PER_FUNCTION:
                    raise ValueError("too many recognized source arithmetic events")
                candidates.append(clue)
        rows.append({
            "public_rev1_source_function": name,
            "bounded_source_instruction_count": len(data) // 4,
            "recognized_source_syntax": candidates,
            "opaque_instruction_count": len(data) // 4 - len(candidates),
            "function_return_and_all_paths_verified": False,
            "score_index_orientation_verified": False,
        })
    return {
        "kind": "P0-GOLF-CONFIG-DUAL-SOURCE-INDEX-CONFLICT-PPC-TRIAGE",
        "source_game": "RSPE01", "revision": 1,
        "ogws_public_config_text_unit_boundary_qualified": True,
        "function_addresses_independently_public_both_sources": True,
        "header_disagreement": "ogws_info-player-major-4x9-versus-Kokeshi-hole-major-9x4",
        "source_functions": rows,
        "score_array_byte_region_identical_under_both_layouts": True,
        "source_comparison_not_complete_reaching_definition_proof": True,
        "one_unique_row_order_selected": False,
        "displayed_result_or_stroke_semantics_verified": False,
        "physical_xyz_velocity_power_impact_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def audit(archive: Path) -> dict:
    folders = seven._check_archive(archive)  # Strict original ALL 14 bank SHA before.
    path = seven.src._file(folders[1], "1.1.raw", roster.MEM1_SIZE)
    windows = {}
    with path.open("rb") as fh:
        header = fh.read(8)
        if len(header) != 8 or header[:6] != b"RSPE01" or header[7] != 1:
            raise ValueError("original B0 source revision drift")
        for name, start, end in FUNCTIONS:
            if (not CONFIG_UNIT_BOUNDS[0] <= start < end <= CONFIG_UNIT_BOUNDS[1]
                    or start % 4 or end % 4):
                raise ValueError("public function out of Config source range")
            fh.seek(start - MEM1_BASE)
            windows[name] = fh.read(end - start)
    report = summarize_source_windows(windows)
    seven._check_archive(archive)  # Original ALL 14 bank SHA after.
    report["original_14_bank_SHA_verified_before_and_after"] = True
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        out = audit(args.archive)
    except (OSError, ValueError, TypeError, AttributeError, KeyError, OverflowError,
            struct.error):
        print("P0 CONFIG INDEX CONFLICT ABSTAIN: original SHA, Rev1 or bounded PPC source gate failed; no values/paths disclosed.",
              file=sys.stderr)
        return 2
    print(json.dumps(out, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
