"""Offline PPC field-access atlas for Wii Sports Rev1 golf source units.

Searches ONLY code ranges from doldecomp/ogws RSPE01_01/splits.txt in a local
legally extracted main.dol. Never loads a disc image, reads Dolphin RAM,
writes memory, or asserts a club/power address. Code ranges and offsets in
the report are STATIC ANALYSIS hints, not verified live player fields.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import sys

# Reuse the existing source-gated DOL section parser from S002 PR #122.
from audit_golf_singleton_code import get_code, MAX_DOL_BYTES

UNITS = {
    "RPGolMain": (0x8028E098, 0x8028E900),
    "RPGolPlayer": (0x8029E62C, 0x802A2210),
    "RPGolPlayerManager": (0x802A2210, 0x802A3560),
}
# D-form integer and float loads/stores. No claim that an RA register holds "this".
MEM_OPS = {
    32: ("lwz", "load", 4), 34: ("lbz", "load", 1),
    36: ("stw", "store", 4), 38: ("stb", "store", 1),
    40: ("lhz", "load", 2), 42: ("lha", "load", 2),
    44: ("sth", "store", 2), 48: ("lfs", "load", 4),
    50: ("lfd", "load", 8), 52: ("stfs", "store", 4),
    54: ("stfd", "store", 8),
}
OBJECT_BASES = (3, 30, 31)  # r3 entry parameter, r30/r31 often callee-saved
MAX_MEMBER_OFFSET = 0x3FC
MAX_RESULTS = 40


def _signed16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def _branch_target(word: int, instruction_address: int) -> int | None:
    """Decode unconditional PPC bl target; does NOT resolve bctrl/indirect."""
    if word >> 26 != 18 or word & 1 == 0:
        return None
    displacement = word & 0x03FFFFFC
    if displacement & 0x02000000:
        displacement -= 0x04000000
    if word & 2:  # AA bit: absolute form, unusual for normal bl
        return displacement & 0xFFFFFFFF
    return (instruction_address + displacement) & 0xFFFFFFFF


def _owner(address: int) -> str | None:
    for name, (start, end) in UNITS.items():
        if start <= address < end:
            return name
    return None


def analyze(dol: bytes) -> dict:
    """Return only public source-code offset patterns, never DOL instructions."""
    if type(dol) is not bytes or not 0x100 < len(dol) <= MAX_DOL_BYTES:
        raise ValueError("Need a bounded, locally extracted main.dol")
    fields = Counter()
    sda = Counter()
    calls = Counter()
    instruction_counts = {}
    for unit, (start, end) in UNITS.items():
        source = get_code(dol, start, end - start)
        instruction_counts[unit] = len(source) // 4
        for pos in range(0, len(source), 4):
            word = struct.unpack_from(">I", source, pos)[0]
            address = start + pos
            opcode = word >> 26
            if opcode in MEM_OPS:
                mnemonic, kind, width = MEM_OPS[opcode]
                base = (word >> 16) & 31
                disp = _signed16(word)
                if base in OBJECT_BASES and 0 <= disp <= MAX_MEMBER_OFFSET:
                    fields[(unit, base, disp, mnemonic, kind, width)] += 1
                if base == 13:  # Small data: static/global access, not player member
                    sda[(unit, disp, mnemonic, kind, width)] += 1
            dest = _branch_target(word, address)
            if dest is not None:
                target_unit = _owner(dest)
                if target_unit is not None and target_unit != unit:
                    calls[(unit, target_unit)] += 1

    rows = [{
        "source_unit": unit, "base_register": f"r{base}",
        "relative_displacement": f"+0x{disp:03X}",
        "opcode_mnemonic": mnemonic, "access_kind": kind,
        "width_bytes": width, "instruction_count": count,
    } for (unit, base, disp, mnemonic, kind, width), count in fields.items()]
    rows.sort(key=lambda r: (-r["instruction_count"], r["source_unit"],
                            r["relative_displacement"], r["base_register"],
                            r["access_kind"], r["width_bytes"], r["opcode_mnemonic"]))
    static_rows = [{
        "source_unit": unit,
        "r13_signed_displacement": ("+" if disp >= 0 else "-") +
                                  f"0x{abs(disp):04X}",
        "opcode_mnemonic": mnemonic, "access_kind": kind,
        "width_bytes": width, "instruction_count": count,
    } for (unit, disp, mnemonic, kind, width), count in sda.items()]
    static_rows.sort(key=lambda r: (-r["instruction_count"], r["source_unit"],
                                   r["r13_signed_displacement"], r["access_kind"]))
    call_rows = [{
        "from_source_unit": src, "to_source_unit": dest, "direct_bl_count": count,
    } for (src, dest), count in sorted(calls.items())]
    return {
        "schema_version": 1,
        "kind": "offline_rev1_golf_player_ppc_access_atlas",
        "revision_verified_from_dol_alone": False,
        "game_code_sections_only": True,
        "source_ranges": {unit: {
            "start": f"0x{start:08X}", "end_exclusive": f"0x{end:08X}",
        } for unit, (start, end) in UNITS.items()},
        "scanned_instruction_counts": instruction_counts,
        "object_base_candidate_count": len(rows),
        "object_access_patterns": rows[:MAX_RESULTS],
        "object_access_patterns_truncated": len(rows) > MAX_RESULTS,
        "float_store_candidates": [r for r in rows if r["opcode_mnemonic"] in ("stfs", "stfd")][:MAX_RESULTS],
        "float_store_candidate_count": sum(r["opcode_mnemonic"] in ("stfs", "stfd") for r in rows),
        "r13_static_pattern_count": len(static_rows),
        "r13_static_patterns": static_rows[:MAX_RESULTS],
        "r13_static_patterns_truncated": len(static_rows) > MAX_RESULTS,
        "cross_source_direct_calls": call_rows,
        "confirmed_club_pose_address": False,
        "confirmed_power_address": False,
        "warning": (
            "PPC D-form base register and displacement patterns are NOT typed "
            "C++ members. r3/r30/r31 may be unrelated temporaries or pointers; "
            "r13 is a static-data base of UNKNOWN runtime value. Direct bl calls "
            "do not prove source-level object ownership. The DOL alone does NOT "
            "establish the disc revision. No runtime RAM was read."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dol", required=True, type=Path,
                        help="Locally extracted main.dol only (never ISO/WBFS)")
    parser.add_argument("--out", type=Path,
                        help="Optional local report path; defaults to stdout")
    args = parser.parse_args(argv)
    try:
        if not args.dol.is_file() or not 0x100 < args.dol.stat().st_size <= MAX_DOL_BYTES:
            raise ValueError("Missing or oversized local main.dol")
        report = analyze(args.dol.read_bytes())
        payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.out:
            if args.out.resolve() == args.dol.resolve():
                raise ValueError("Cannot overwrite the input DOL")
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as stream:
                stream.write(payload)
        print(payload, end="")
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print("Golf player code atlas stopped: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
