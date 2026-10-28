#!/usr/bin/env python3
"""P0: r26 provenance IN the published function containing the lone f1 store.

One Rev1 source function ONLY: fn_8029B57C size 0x274, with source
PSVECSquareDistance BL at function +0x4C and stfs f1,0(r26) at +0x50.
The boundaries are from published doldecomp/ogws RSPE01_01 symbols.txt;
compiled code is checked against original private US Rev1 B0 SHA before/after.
No dynamic memory deref, raw PPC words, heap addresses, values or paths emitted.
Static syntax and public function boundaries do NOT establish execution/physics.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_simulate_distance_f1_store_private as previous

base = previous.base
UNIT = previous.UNIT_NAME
UNIT_START = previous.UNIT_START
FUNCTION_ENTRY = 0x8029B57C
FUNCTION_SIZE = 0x274
CALL_PC = previous.CALL_PC
STORE_PC = CALL_PC + 4
SOURCE_LIMIT = 0x80

if not (FUNCTION_ENTRY < CALL_PC < STORE_PC < FUNCTION_ENTRY + FUNCTION_SIZE
        and CALL_PC - FUNCTION_ENTRY == 0x4C):
    raise RuntimeError("reviewed source anchor mismatch")


def _w(code: bytes, pos: int) -> int:
    off = pos - UNIT_START
    if type(code) is not bytes or off < 0 or off % 4 or off + 4 > len(code):
        raise ValueError("invalid source word range")
    return struct.unpack_from(">I", code, off)[0]


def _signed(word: int) -> int:
    n = word & 0xffff
    return n - 0x10000 if n & 0x8000 else n


def _ctrl(word: int) -> str | None:
    op = word >> 26
    if op == 18:
        return "direct_branch_or_call"
    if op == 16:
        return "conditional_branch"
    if op == 17:
        return "system_call"
    if op == 19:
        xo = (word >> 1) & 1023
        if xo in (16, 50, 528):
            return "return_or_indirect_branch"
    return None


def _write_class(word: int, reg: int) -> str | None:
    """Conservative PPC GPR destinations: only recognizable source syntax.

    A source class is not a complete reaching definition or source type.
    """
    if type(word) is not int or not 0 <= word <= 0xffffffff:
        raise ValueError("unknown source PPC")
    op = word >> 26
    rt = (word >> 21) & 31
    ra = (word >> 16) & 31
    rb = (word >> 11) & 31
    if op in (14, 15) and rt == reg:
        return ("literal_addi_or_addis_zero_base" if ra == 0
                else f"addi_or_addis_from_r{ra}")
    if op in (32, 33, 34, 35, 40, 41, 42, 43):
        if rt == reg:
            return f"integer_load_from_r{ra}_offset_{_signed(word):+d}"
        if op in (33, 35, 41, 43) and ra == reg:
            return "integer_update_load_base_write_untyped"
    if op in (20, 21, 23, 24, 25, 26, 27, 28, 29) and ra == reg:
        return "rotate_or_logical_RA_destination_untyped"
    if op == 46 and rt <= reg:
        return "lmw_GPR_range_overwrite"
    if op in (37, 39, 45, 49, 51, 53, 55) and ra == reg:
        return "memory_update_base_write_untyped"
    if op == 31:
        xo = (word >> 1) & 1023
        if xo == 444 and ra == reg and rb == rt:
            return f"mr_from_r{rt}"
        # Incomplete X-form decode: flag, never assert register preservation.
        if rt == reg or ra == reg:
            return "other_X_form_possible_write_untyped"
    return None


def inspect(code: bytes, start: int, unit_name: str):
    if (type(code) is not bytes or type(start) is not int
            or start != UNIT_START or unit_name != UNIT or len(code) % 4
            or len(code) < STORE_PC + 4 - UNIT_START):
        raise ValueError("source unit or code bytes changed")
    prior = previous.inspect_local(code, start, unit_name)
    if (prior["source_store_base_register"] != "r26"
            or prior["source_store_signed_D_form_displacement"] != 0
            or prior["exact_distance_call_public_source_relative"] != "+0x00388"
            or prior["exact_f1_stfs_public_source_relative"] != "+0x0038C"):
        raise ValueError("original source f1 store evidence changed")

    if CALL_PC - FUNCTION_ENTRY > SOURCE_LIMIT:
        raise ValueError("function prefix outside bound")
    words = [(pc, _w(code, pc))
             for pc in range(FUNCTION_ENTRY, CALL_PC, 4)]
    controls = [(pc, _ctrl(word)) for pc, word in words if _ctrl(word)]
    writes = [(pc, kind) for pc, word in words
              if (kind := _write_class(word, 26)) is not None]
    last = writes[-1] if writes else None
    post_control = (sum(pc > last[0] for pc, _ in controls)
                    if last else len(controls))
    return {
        "kind": "P0-SIMULATE-SINGLE-SOURCE-FUNCTION-R26-ORIGIN",
        "game_id": "RSPE01",
        "disc_revision": 1,
        "source_unit": unit_name,
        "published_function_entry_source_relative": f"+0x{FUNCTION_ENTRY - UNIT_START:05X}",
        "published_function_size_bytes": FUNCTION_SIZE,
        "call_from_function_entry_bytes": CALL_PC - FUNCTION_ENTRY,
        "source_prefix_instructions": len(words),
        "source_prefix_control_transfer_count": len(controls),
        "source_prefix_other_direct_calls_seen": sum(
            (w >> 26 == 18 and bool(w & 1)) for _, w in words),
        "r26_syntactic_write_count": len(writes),
        "r26_last_syntactic_definition": last[1] if last else "INCOMING_R26_UNRESOLVED",
        "r26_last_write_source_relative": (
            f"+0x{last[0] - UNIT_START:05X}" if last else None),
        "control_transfers_after_last_r26_definition": post_control,
        "r26_is_PPC_nonvolatile_abi_register": True,
        "callee_preservation_or_all_path_r26_flow_verified": False,
        "r26_runtime_base_object_or_pointer_verified": False,
        "source_stfs_f1_zero_r26_verified": True,
        "real_squared_distance_or_UI_result_verified": False,
        "physical_ball_world_XYZ_velocity_impact_power_score_verified": False,
        "same_guest_frame_or_execution_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def audit(baseline: Path, root: Path):
    bank = base.checked_private_b0(baseline, root)
    public = base.load_public_text_units()
    owner = [(lo, hi, name) for lo, hi, name in public
             if lo == UNIT_START and name == UNIT]
    if (len(public) != 832 or len(owner) != 1
            or not owner[0][0] <= FUNCTION_ENTRY
            or FUNCTION_ENTRY + FUNCTION_SIZE > owner[0][1]):
        raise ValueError("public Rev1 source function range invalid")
    lo, hi, name = owner[0]
    with bank.open("rb") as stream:
        if stream.read(6) != b"RSPE01":
            raise ValueError("game ID mismatch")
        stream.seek(7)
        if stream.read(1) != b"\x01":
            raise ValueError("Rev1 mismatch")
        stream.seek(lo - base.MEM1_START)
        code = stream.read(hi - lo)
    if len(code) != hi - lo or not any(code):
        raise ValueError("source code block missing")
    result = inspect(code, lo, name)
    if base.checked_private_b0(baseline, root) != bank:
        raise ValueError("native original B0 SHA mismatch after read")
    result["source_rev1_original_B0_SHA_before_after_verified"] = True
    result["public_832_source_index_verified"] = True
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        root = Path(__file__).resolve().parents[2] / "Wii-AI-Golf-Data"
        result = audit(args.baseline, root)
    except (base.UntrustedInput, OSError, ValueError, TypeError, KeyError,
            IndexError, AttributeError, OverflowError):
        print("P0_SIMULATE_R26_ABSTAIN: original B0 Rev1/SHA, exact "
              "function source or register evidence rejected", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
