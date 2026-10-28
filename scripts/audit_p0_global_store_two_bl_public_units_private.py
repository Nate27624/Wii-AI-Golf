#!/usr/bin/env python3
"""P0: source-qualified owner lookup for TWO static BLs before global-ball stw.

The #240 source owner already found post-return candidate paths; this script
only names the PUBLISHED compiled source .text units containing their targets.
The original B0 full-bank SHA and RSPE01 Rev1 gates come from #219.
No ROM exports, arbitrary memory scan, heap pointers, PPC words, paths or
gameplay values are written to stdout. NOT a constructor/allocator proof.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import audit_ball_xyz_source_callers_private as base

FIRST_BL = 0x8029A048
SECOND_BL = 0x8029A058
RETURN = 0x8029A034
POSITIVE_LITERAL = 0x8029A040
SPLIT_BRANCH = 0x8029A050
STORE = 0x8029A05C
SDA_FIELD_ANCHOR = 0x80299EE4
SDA_GLOBAL_LOAD = 0x80299CD0
FIELD_SINGLETON_STATIC = 0x804BF868
FIELD_SDA_DISPLACEMENT = -23320
SOURCE_UNIT = "RPGolMapObjBall"
CODE = (RETURN, POSITIVE_LITERAL, FIRST_BL, SPLIT_BRANCH, SECOND_BL,
        STORE, SDA_FIELD_ANCHOR, SDA_GLOBAL_LOAD)


def _d(word):
    if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
        raise ValueError("invalid source instruction")
    imm = word & 65535
    return ((word >> 26) & 63, (word >> 21) & 31,
            (word >> 16) & 31, imm - 65536 if imm & 0x8000 else imm)


def _bc_target(pc, word):
    if type(word) is not int or word >> 26 != 16 or word & 1:
        return None
    disp = word & 0xFFFC
    if disp & 0x8000:
        disp -= 0x10000
    return (disp if word & 2 else pc + disp) & 0xFFFFFFFF


def _source_unit_for(pc, public):
    matches = [(lo, hi, name) for lo, hi, name in public if lo <= pc < hi]
    if len(matches) != 1:
        return {"public_unit_found": False,
                "public_source_unit": None,
                "public_unit_relative_offset": None}
    lo, hi, name = matches[0]
    return {"public_unit_found": True, "public_source_unit": name,
            "public_unit_relative_offset": f"+0x{pc - lo:05X}"}


def classify_source(read_u32, public):
    """Validate #240's exact two-BL context without implementing their CFG."""
    if not callable(read_u32) or type(public) is not tuple or not public:
        raise ValueError("source PPC callback and public index required")
    words = {pc: read_u32(pc) for pc in CODE}
    if words[RETURN] != 0x4E800020:
        raise ValueError("prior return is not exact PPC blr")
    op, rt, ra, positive = _d(words[POSITIVE_LITERAL])
    if (op, rt, ra) != (14, 3, 0) or positive <= 0:
        raise ValueError("source first call size argument changed")
    if _d(words[SDA_FIELD_ANCHOR]) != (32, 3, 13, FIELD_SDA_DISPLACEMENT):
        raise ValueError("SDA anchor changed")
    global_op, global_rt, global_ra, offset = _d(words[SDA_GLOBAL_LOAD])
    if (global_op, global_rt, global_ra) != (32, 3, 13):
        raise ValueError("source global r13 load changed")
    if _d(words[STORE]) != (36, 3, 13, offset):
        raise ValueError("global source-slot stw no longer matches load")
    slot = FIELD_SINGLETON_STATIC - FIELD_SDA_DISPLACEMENT + offset
    if not (base.MEM1_START <= slot < base.MEM1_START + base.MEM1_LEN
            and slot % 4 == 0):
        raise ValueError("r13 global slot not within captured MEM1")
    if _bc_target(SPLIT_BRANCH, words[SPLIT_BRANCH]) != STORE:
        raise ValueError("conditional skip-to-store form changed")
    targets = []
    for label, pc in (("first_bl", FIRST_BL), ("optional_second_bl", SECOND_BL)):
        found = base.decode_ppc_branch(pc, words[pc])
        if found is None or found[1] is not True:
            raise ValueError("source direct BL missing")
        dest, _ = found
        unit = _source_unit_for(dest, public)
        targets.append({"callsite": label,
                        "source_relative_site": f"+0x{pc - 0x80296FD8:04X}",
                        "public_call_target_pc": f"0x{dest:08X}",
                        **unit,
                        "exact_function_entry_verified": False,
                        "callee_allocator_or_constructor_verified": False})
    return {
        "kind": "P0-POSTRETURN-GLOBAL-STORE-TWO-BL-PUBLIC-UNIT-LOOKUP",
        "game_id": "RSPE01",
        "disc_revision": 1,
        "public_unit_source": "doldecomp/ogws RSPE01_01 source splits",
        "exact_bl_count": 2,
        "prior_instruction_exact_blr": True,
        "positive_literal_argument_to_first_bl": True,
        "conditional_branch_may_skip_second_bl": True,
        "global_load_and_store_same_r13_slot_syntax": True,
        "source_global_slot_memory_identity_verified": False,
        "hypothetical_post_return_entry_is_function_proven": False,
        "runtime_global_slot_store_execution_verified": False,
        "returned_r3_reaching_definition_verified": False,
        "callee_function_entry_or_symbols_verified": False,
        "callee_allocator_or_constructor_verified": False,
        "global_ball_is_physical_rendered_ball_verified": False,
        "ball_xyz_velocity_impact_power_score_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
        "callees": targets,
    }


def audit(session: Path, data_root: Path):
    bank = base.checked_private_b0(session, data_root)
    units = base.load_public_text_units()  # original 832 pinned source units
    def load(pc):
        if not base.MEM1_START <= pc <= base.MEM1_START + base.MEM1_LEN - 4:
            raise ValueError("code PC outside native MEM1")
        with bank.open("rb") as fh:
            fh.seek(pc - base.MEM1_START)
            b = fh.read(4)
        if len(b) != 4:
            raise ValueError("short code read")
        return struct.unpack(">I", b)[0]

    with bank.open("rb") as fh:
        if fh.read(6) != b"RSPE01":
            raise ValueError("game id wrong")
        fh.seek(7)
        if fh.read(1) != b"\x01":
            raise ValueError("disc revision wrong")
    for pc in CODE:
        if base.source_unit(pc) is None:
            raise ValueError("source PC not in published Golf compilation units")
    result = classify_source(load, units)
    if base.checked_private_b0(session, data_root) != bank:
        raise ValueError("original B0 SHA drift after read")
    result["original_b0_mem1_sha_checked_before_after"] = True
    result["public_832_unit_index_authenticated"] = len(units) == 832
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        root = Path(__file__).resolve().parents[2] / "Wii-AI-Golf-Data"
        report = audit(args.baseline, root)
    except (base.UntrustedInput, OSError, ValueError, TypeError,
            KeyError, AttributeError, IndexError, OverflowError):
        print("P0_GLOBAL_TWO_BL_ABSTAIN: original B0 source/revision/SHA "
              "or exact post-return PPC proof unavailable", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
