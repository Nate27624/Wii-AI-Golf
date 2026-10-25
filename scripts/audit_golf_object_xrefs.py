"""Read-only Rev1 Wii Sports golf object CODE cross-reference triage.

Inputs are a private, locally extracted main.dol; NEVER pass a ROM image.
This tool does not read Dolphin RAM, open RPC, control a swing, or upload data.
Results contain only documented executable addresses, module names and
RELATIVE source/field candidate offsets. Not verified object semantics.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import importlib.util
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "golf_bounded_dol", HERE / "audit_golf_singleton_code.py"
)
_DOL = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_DOL)

# doldecomp/ogws config/RSPE01_01/splits.txt, exact disjoint .text/.data
# compilation-unit extents, NOT exact functions or class vtable identities.
MODULES = {
    "RPGolMain": ((0x8028E098, 0x8028E900), (0x803C7798, 0x803C77C0)),
    "RPGolPlayer": ((0x8029E62C, 0x802A2210), (0x803C7CC8, 0x803C7DD0)),
    "RPGolPlayerManager": ((0x802A2210, 0x802A3560),
                            (0x803C7DD0, 0x803C7DE0)),
}
# PPC D-form memory operations, not necessarily C++ member accesses.
LOAD_STORE = {
    32: "lwz", 36: "stw", 48: "lfs", 52: "stfs",
    34: "lbz", 38: "stb", 40: "lhz", 44: "sth",
}
MAX_REPORTED_EDGES = 12
MAX_FIELD_HINTS = 32
MAX_DATA_HINTS = 32
MAX_MEMBER_DISPLACEMENT = 0x1FF


def _word_at(data: bytes, position: int) -> int:
    return struct.unpack_from(">I", data, position)[0]


def _signed16(word: int) -> int:
    value = word & 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def _branch_target(pc: int, word: int) -> int | None:
    """Only PPC I-form direct relative branch with link (bl)."""
    if (word >> 26) != 18 or not (word & 1) or (word & 2):
        return None  # ignore b, absolute bla, and dynamic bctrl/bclrl
    displacement = word & 0x03FFFFFC
    if displacement & 0x02000000:
        displacement -= 0x04000000
    return (pc + displacement) & 0xFFFFFFFF


def _module_for_code(addr: int) -> str | None:
    for name, (code, _) in MODULES.items():
        if code[0] <= addr < code[1]:
            return name
    return None


def _mapped_data(dol: bytes, low: int, high: int) -> bytes:
    if high <= low or low % 4 or high % 4:
        raise ValueError("invalid documented data range")
    for start, stop, offset, executable in _DOL.sections(dol):
        if not executable and start <= low and high <= stop:
            pos = offset + (low - start)
            return dol[pos:pos + high - low]
    raise ValueError("documented Rev1 object data range not mapped")


def analyze(dol: bytes) -> dict:
    """No raw instructions, absolute HEAP pointers or file paths in output."""
    code = {}
    data = {}
    for name, ((text_lo, text_hi), (data_lo, data_hi)) in MODULES.items():
        code[name] = _DOL.get_code(dol, text_lo, text_hi - text_lo)
        data[name] = _mapped_data(dol, data_lo, data_hi)

    edges = defaultdict(list)
    operands = defaultdict(lambda: {"occurrences": 0, "near_other_unit_call": 0})
    module_counts = {}
    data_hints = {}
    for name, ((start, _), _) in MODULES.items():
        words = [_word_at(code[name], i) for i in range(0, len(code[name]), 4)]
        module_counts[name] = {
            "instructions_checked": len(words),
            "direct_other_unit_bl_count": 0,
            "r3_base_memory_operands": 0,
        }
        recent_call = None
        for index, instruction in enumerate(words):
            pc = start + index * 4
            if recent_call and index - recent_call[0] > 4:
                recent_call = None
            target = _branch_target(pc, instruction)
            if target is not None:
                other = _module_for_code(target)
                if other and other != name:
                    edges[(name, other)].append((pc, target))
                    module_counts[name]["direct_other_unit_bl_count"] += 1
                    recent_call = (index, other)
                else:
                    recent_call = None

            op = instruction >> 26
            ra = (instruction >> 16) & 31
            displacement = _signed16(instruction)
            if (op not in LOAD_STORE or ra != 3
                    or not 0 <= displacement <= MAX_MEMBER_DISPLACEMENT):
                continue
            module_counts[name]["r3_base_memory_operands"] += 1
            key = (name, displacement, LOAD_STORE[op])
            operands[key]["occurrences"] += 1
            if recent_call and 1 <= index - recent_call[0] <= 4:
                # Heuristic only: we do NOT prove that r3 contains 'this'
                # or a returned object; ABI r3 may be reused arbitrarily.
                operands[key]["near_other_unit_call"] += 1

    calls = []
    for (src, dest), pairs in sorted(edges.items()):
        calls.append({
            "caller_unit": src, "callee_unit": dest,
            "direct_bl_count": len(pairs),
            "source_code_callsites": [
                {"instruction": f"0x{pc:08X}", "target": f"0x{target:08X}"}
                for pc, target in pairs[:MAX_REPORTED_EDGES]
            ],
            "callsites_truncated": len(pairs) > MAX_REPORTED_EDGES,
            "target_is_known_symbol_entry": False,
            "ownership_or_class_identity_proven": False,
        })

    candidates = []
    for (unit, offset, opcode), record in operands.items():
        candidates.append({
            "code_unit": unit, "r3_relative_displacement": f"+0x{offset:03X}",
            "memory_opcode": opcode,
            "instruction_occurrences": record["occurrences"],
            "within_four_instructions_of_other_unit_bl": record["near_other_unit_call"],
            "receiver_identity": "unverified_r3_base",
        })
    candidates.sort(key=lambda row: (
        -row["within_four_instructions_of_other_unit_bl"],
        -row["instruction_occurrences"], row["code_unit"],
        row["r3_relative_displacement"], row["memory_opcode"]))
    truncated = len(candidates) > MAX_FIELD_HINTS

    for name, buf in data.items():
        matches = defaultdict(list)
        for offset in range(0, len(buf), 4):
            value = _word_at(buf, offset)
            unit = _module_for_code(value)
            if unit and value % 4 == 0:
                matches[unit].append(offset)
        data_hints[name] = {
            "words_checked": len(buf) // 4,
            "aligned_code_pointers_by_target_unit": [
                {"target_unit": dest, "count": len(offs),
                 "data_relative_word_offsets": [
                     f"+0x{x:03X}" for x in offs[:MAX_DATA_HINTS]],
                 "truncated": len(offs) > MAX_DATA_HINTS}
                for dest, offs in sorted(matches.items())
            ],
            "exact_vtable_start_or_dynamic_type_verified": False,
        }

    return {
        "kind": "offline_rev1_golf_object_code_xref_triage",
        "schema_version": 1,
        "source": "doldecomp/ogws config/RSPE01_01/splits.txt",
        "source_units_checked": list(MODULES),
        "code_unit_counts": module_counts,
        "direct_cross_unit_calls": calls,
        "r3_relative_memory_operand_hints": candidates[:MAX_FIELD_HINTS],
        "r3_operand_hint_count": len(candidates),
        "r3_operand_hints_truncated": truncated,
        "source_data_function_pointer_hints": data_hints,
        "confirmed_rpgolmain_instance_type": False,
        "confirmed_player_or_club_member_offsets": False,
        "confirmed_golf_power_address": False,
        "disc_revision_independently_verified": False,
        "warning": (
            "PPC compilation-unit boundaries are not function entrypoints. "
            "Direct bl targets are source code addresses, not proof of calls "
            "between object instances. r3 may NOT be C++ this. Data words "
            "resembling code addresses are NOT confirmed vtables. "
            "No golfer/club/power object ownership is identified."
        ),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dol", type=Path, required=True,
                   help="Private legally extracted Rev1 main.dol; never uploaded")
    args = p.parse_args(argv)
    try:
        path = args.dol
        if (not path.is_file() or path.is_symlink()
                or not 0x100 <= path.stat().st_size <= _DOL.MAX_DOL_BYTES):
            raise ValueError("invalid private DOL input")
        report = analyze(path.read_bytes())
        print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, struct.error):
        # Never echo private paths, binary bytes or internal parser values.
        print("Object xref audit stopped: invalid or incompatible private Rev1 DOL",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
