"""Bounded PPC source provenance around the only +0x90 exact four-byte store.

Uses existing PR #244/#219 original-B0 manifest/SHA and source gates.
This is static instruction syntax, not selected-record receiver proof.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys

import audit_p0_player_record_store_candidates_private as parent
import audit_ball_xyz_source_callers_private as original

SOURCE_UNIT = "RPGolPlayer"
SOURCE_UNIT_START = 0x8029E62C
STORE_REL = 0x1C18
STORE_PC = SOURCE_UNIT_START + STORE_REL
WINDOW_BYTES = 0x180
MAX_REPORT_SITES = 16


def decode_word(word: int, register: int = 31):
    """Classify possible definitions/control flow, not physical semantics.

    Deliberately over-inclusive and does not establish dataflow dominance.
    """
    if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
        raise ValueError("Malformed PPC instruction")
    op = word >> 26
    rt = (word >> 21) & 31
    ra = (word >> 16) & 31
    rb = (word >> 11) & 31
    if op in (16, 17, 18, 19):
        return {"class": "control_flow_hazard"}
    if op in (32, 34, 40, 42) and rt == register:
        return {"class": "gpr_memory_load", "from_register": f"r{ra}"}
    if op in (33, 35, 41, 43):
        if rt == register:
            return {"class": "gpr_memory_load_update", "from_register": f"r{ra}"}
        if ra == register:
            return {"class": "gpr_base_update", "from_register": f"r{ra}"}
    if op in (14, 15) and rt == register:
        return {"class": "addi_or_addis", "from_register": f"r{ra}"}
    if op in (24, 25, 26, 27, 28, 29) and ra == register:
        return {"class": "logical_immediate_result", "from_register": f"r{rt}"}
    if op == 31:
        xo = (word >> 1) & 0x3FF
        if xo == 444 and ra == register:
            return {
                "class": "register_copy_mr" if rt == rb else "logical_or_result",
                "from_register": f"r{rt}" if rt == rb else "multiple",
            }
        if rt == register or ra == register:
            return {"class": "unknown_extended_register_touch"}
    if op in (37, 39, 45, 49, 51, 53, 55) and ra == register:
        return {"class": "update_form_base_register"}
    if op in (7, 8, 12, 13, 20, 21, 22, 23, 30) and (
            rt == register or ra == register):
        return {"class": "possible_integer_register_definition"}
    if op not in (4, 14, 15, 24, 25, 26, 27, 28, 29, 31,
                  36, 38, 44, 48, 50, 52, 54, 59, 63):
        return {"class": "unclassified_opcode_hazard"}
    return None


def scan_slice(data: bytes, start_pc: int, site_pc: int, unit_start: int):
    if (type(data) is not bytes or type(start_pc) is not int or
            type(site_pc) is not int or type(unit_start) is not int or
            len(data) % 4 or not 8 <= len(data) <= WINDOW_BYTES + 4 or
            start_pc % 4 or site_pc % 4 or start_pc < unit_start or
            start_pc + len(data) != site_pc + 4):
        raise ValueError("Invalid bounded source slice")
    word = struct.unpack_from(">I", data, len(data) - 4)[0]
    op, fr, base_reg, displacement = (
        parent.decode_dform_store(word) or (None, None, None, None))
    if (op, base_reg, displacement) != ("stfs", 31, 0x90):
        raise ValueError("Expected original r31+0x90 store absent")
    seen = []
    for offset in range(len(data) - 8, -1, -4):
        pc = start_pc + offset
        event = decode_word(struct.unpack_from(">I", data, offset)[0], 31)
        if event is not None:
            seen.append({
                "source_relative_offset": f"+0x{pc-unit_start:04X}",
                **event,
            })
    hazard_count = sum(x["class"] == "control_flow_hazard" for x in seen)
    register_events = [x for x in seen if x["class"] not in (
        "control_flow_hazard", "unclassified_opcode_hazard")]
    return {
        "kind": "S002-P0-REV1-R31-STORE-SOURCE-SLICE",
        "game_id": "RSPE01", "disc_revision": 1,
        "source_unit": SOURCE_UNIT,
        "source_relative_store_site": f"+0x{site_pc-unit_start:04X}",
        "store_op": "stfs", "store_base_reg": "r31",
        "store_displacement": "+0x090", "store_float_reg": f"f{fr}",
        "instructions_examined": len(data)//4 - 1,
        "control_flow_hazard_count": hazard_count,
        "r31_assignment_or_touch_candidate_count": len(register_events),
        "nearest_hazard_or_definition": seen[0] if seen else None,
        "event_sites_nearest_first": seen[:MAX_REPORT_SITES],
        "additional_event_sites_omitted": max(0, len(seen)-MAX_REPORT_SITES),
        "branch_aware_cfg_dominance_verified": False,
        "r31_is_selected_player_record_verified": False,
        "record_90_actual_writer_verified": False,
        "source_instruction_executed_during_shot_verified": False,
        "ball_world_xyz_verified": False,
        "ball_velocity_verified": False,
        "game_power_ram_verified": False,
        "approved_for_training": False,
        "allowed_to_publish": False,
    }


def audit(session: Path, data_root: Path):
    parent.audit(session, data_root)  # Existing SHA/manifest/revision/source gate.
    try:
        file = original.checked_private_b0(session, data_root)
    except original.UntrustedInput:
        raise ValueError("Untrusted B0 memory") from None
    if not any(name == SOURCE_UNIT and lo == SOURCE_UNIT_START and
               lo <= STORE_PC < hi for name, lo, hi in original.UNITS):
        raise ValueError("Rev1 public source-unit pin mismatch")
    start = STORE_PC - WINDOW_BYTES
    if start < SOURCE_UNIT_START:
        raise ValueError("Source slice outside public unit")
    with file.open("rb") as stream:
        stream.seek(start-original.MEM1_START)
        data = stream.read(WINDOW_BYTES + 4)
    if len(data) != WINDOW_BYTES + 4:
        raise ValueError("Source slice truncated")
    try:
        original.checked_private_b0(session, data_root)
    except original.UntrustedInput:
        raise ValueError("Source changed or invalid") from None
    out = scan_slice(data, start, STORE_PC, SOURCE_UNIT_START)
    out["original_B0_SHA256_verified_before_and_after_slice"] = True
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    default = Path(__file__).resolve().parents[2] / "Wii-AI-Golf-Data"
    p.add_argument("--data-root", type=Path, default=default)
    p.add_argument("--private-session", type=Path)
    args = p.parse_args(argv)
    session = args.private_session or args.data_root / "ball-study-20261027-212633"
    try:
        report = audit(session, args.data_root)
    except (OSError, ValueError, TypeError, OverflowError, KeyError,
            AttributeError, ImportError):
        print("P0 r31 source slice ABSTAINED; source/manifest/revision gate failed. "
              "No private memory or file paths disclosed.", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
