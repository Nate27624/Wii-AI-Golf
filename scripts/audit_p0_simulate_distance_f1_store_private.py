#!/usr/bin/env python3
"""One exact original-B0 P0 question: where does SimulateManager store f1?

Only source-site RPGolSimulateManager +0x388, the sole observed exact PSVEC
square-distance BL with a nearby direct stfs f1. Source-bounded PPC syntax
from original US Rev1, original B0 SHA before/after via #219 and #266.
No RAM pointer deref, no game data export or live input.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_golf_vec_f1_return_private as f1

base = f1.base
UNIT_NAME = "Pack/RPSports/RPGolScene/RPGolSimulateManager.cpp"
UNIT_START = 0x8029B240
CALL_REL = 0x00388
CALL_PC = UNIT_START + CALL_REL
UNKNOWN = "UNRESOLVED_SOURCE_GPR_BASE"


def _signed16(word: int) -> int:
    value = word & 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def _store_decode(word: int) -> tuple[int, int] | None:
    if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
        raise ValueError("not source PPC")
    op, frs = (word >> 26), ((word >> 21) & 31)
    if op not in (52, 53) or frs != 1:
        return None
    return (word >> 16) & 31, _signed16(word)


def _relevant_base_write(word: int, reg: int) -> str | None:
    """PPC syntactic GPR writes; do not assert reaching-definition completeness."""
    op = word >> 26
    rt = (word >> 21) & 31
    ra = (word >> 16) & 31
    if op in (14, 15) and rt == reg:
        if ra == 0:
            return "ADDI_ZERO_BASE_LITERAL"
        return f"ADDI_OR_ADDIS_FROM_r{ra}"
    if op in (32, 33, 34, 35, 40, 41, 42, 43):
        if rt == reg:
            return f"INTEGER_GPR_LOAD_BASE_r{ra}"
        if op in (33, 35, 41, 43) and ra == reg:
            return "INTEGER_LOAD_UPDATE_BASE_WRITE"
    if op in (20, 21, 23, 24, 25, 26, 27, 28, 29) and ra == reg:
        return "LOGICAL_Ra_DEST_UNKNOWN_VALUE"
    if op == 46 and rt <= reg:
        return "LMW_RANGE_OVERWRITE"
    if op in (37, 39, 45, 49, 51, 53, 55) and ra == reg:
        return "MEMORY_UPDATE_BASE_WRITE"
    if op == 31:
        xo = (word >> 1) & 1023
        rs = (word >> 21) & 31
        rb = (word >> 11) & 31
        if xo == 444 and ra == reg and rs == rb:
            return f"MR_FROM_r{rs}"
        if ra == reg or rt == reg:
            return "OTHER_X_FORM_POSSIBLE_WRITE"
    return None


def inspect_local(code: bytes, start: int, owner: str) -> dict:
    if (type(code) is not bytes or type(start) is not int
            or start != UNIT_START or owner != UNIT_NAME or len(code) % 4):
        raise ValueError("wrong source unit/bytes")
    at = CALL_PC - start
    if at < 0 or at + 4 > len(code):
        raise ValueError("callsite missing")
    first = f1.inspect_f1(code, start, owner, CALL_PC)
    if (first["first_post_BL_F1_relevant_event_class"]
            != "F1_STFS_SOURCE_STORE_SYNTAX"):
        raise ValueError("previous sole source f1 store lead not reproduced")
    stop = min(len(code), at + 4 + f1.FORWARD)
    destination = None
    for off in range(at + 4, stop, 4):
        word = struct.unpack_from(">I", code, off)[0]
        if f1._control(word):
            raise ValueError("branch/call before candidate f1 store")
        op = word >> 26
        # Keep compatibility with #266's conservatively first-fpr-event rule.
        if op in (48, 49, 50, 51, 56, 57, 59, 60, 61, 63):
            raise ValueError("unresolved FPR event before store")
        dest = _store_decode(word)
        if dest is not None:
            destination = (off, dest[0], dest[1], op)
            break
        if op in (52, 53, 54, 55) and ((word >> 21) & 31) == 1:
            raise ValueError("first f1 effect not exact stfs")
    if destination is None:
        raise ValueError("no exact source stfs f1 found")
    off, ra, signed_disp, opcode = destination
    # This is a *source-offset*, not a dynamic store pointer.
    if ra == 1:
        base_role = "STACK_POINTER_R1_SYNTAX"
    elif ra == 0:
        base_role = "ZERO_BASE_ABSOLUTE_OFFSET_SYNTAX"
    else:
        base_role = "NONSTACK_GPR_BASE_UNTYPED"
    # Distinguish known local written base from ABI/caller-provided base.
    low = max(0, at - 0x80)
    previous = [
        (pos, struct.unpack_from(">I", code, pos)[0])
        for pos in range(low, at, 4)
    ]
    barriers = [i for i, (_pos, word) in enumerate(previous)
                if f1._control(word)]
    suffix = previous[barriers[-1] + 1:] if barriers else previous
    writers = [
        (pos, cls) for pos, word in suffix
        if (cls := _relevant_base_write(word, ra)) is not None
    ]
    prior = writers[-1][1] if writers else UNKNOWN
    return {
        "source_file": owner,
        "exact_distance_call_public_source_relative": f"+0x{at:05X}",
        "exact_f1_stfs_public_source_relative": f"+0x{off:05X}",
        "distance_call_to_stfs_instruction_count": (off - at) // 4,
        "stfs_fpr_source_is_f1": True,
        "source_store_base_register": f"r{ra}",
        "source_store_signed_D_form_displacement": signed_disp,
        "source_store_base_class": base_role,
        "nearest_pre_call_base_syntactic_write": prior,
        "pre_call_source_control_barrier_seen": bool(barriers),
        "destination_is_stack_local_verified": False,
        "destination_is_golf_ball_field_verified": False,
        "store_executed_in_any_shot_verified": False,
        "f1_is_actual_distance_return_from_this_BL_verified": False,
        "squared_distance_ball_to_target_or_units_verified": False,
        "actual_result_HUD_or_score_verified": False,
        "physical_ball_XYZ_velocity_power_impact_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def audit(baseline: Path, data_root: Path) -> dict:
    bank = base.checked_private_b0(baseline, data_root)
    public = base.load_public_text_units()
    owners = [(a, b, n) for a, b, n in public if n == UNIT_NAME]
    if len(owners) != 1 or owners[0][0] != UNIT_START:
        raise ValueError("public Rev1 source-unit owner missing")
    start, end, owner = owners[0]
    with bank.open("rb") as fh:
        if fh.read(6) != b"RSPE01":
            raise ValueError("wrong game")
        fh.seek(7)
        if fh.read(1) != b"\x01":
            raise ValueError("wrong revision")
        fh.seek(start - base.MEM1_START)
        code = fh.read(end - start)
    if len(code) != end - start or not any(code):
        raise ValueError("original source unit unreadable")
    row = inspect_local(code, start, owner)
    if base.checked_private_b0(baseline, data_root) != bank:
        raise ValueError("B0 changed during read")
    return {
        "kind": "P0-GOLF-SIMULATE-ONE-DISTANCE-F1-STORE-DESTINATION",
        "game_id": "RSPE01",
        "disc_revision": 1,
        "original_B0_mem1_sha_before_after_verified": True,
        "public_rev1_source_832_unit_index_verified": len(public) == 832,
        "one_exact_geometry_BL_and_direct_stfs_syntax_verified": True,
        "source_store": row,
        "ball_to_pin_result_semantics_verified": False,
        "runtime_FPR_register_reaching_definition_verified": False,
        "actual_shot_frame_execution_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = Path(__file__).resolve().parents[2] / "Wii-AI-Golf-Data"
        report = audit(args.baseline, root)
    except (base.UntrustedInput, OSError, ValueError, TypeError, KeyError,
            IndexError, AttributeError, OverflowError):
        print("P0_ONE_VECTOR_STFS_ABSTAIN: original B0 SHA/Rev1/source "
              "or exact single-code-site guard failed", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
