#!/usr/bin/env python3
"""Read-only Rev1 GolfMathTrig original PPC source study for LocalOps.

No Dolphin launch, user input, RAM writes, file output, native bytes, hashes,
or private local paths in stdout. Source PCs are public Rev1 code addresses.
Operator approval is required for every non-preapproved research run.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import importlib
import json
import mmap
import os
from pathlib import Path
import sys

SOURCE_UNIT = (0x802A3B84, 0x802A3DE4)  # published RSPE01_01 splits.txt
SEGMENTS = {
    "0": (0x802A3CF4, 0x802A3D44),
    "1": (0x802A3D44, 0x802A3D94),
    "2": (0x802A3D94, 0x802A3DE4),
}
CALLS = {
    "nonlinear_helper_1": (0x802B2E54, 0x802A3CF4),
    "nonlinear_helper_2": (0x802B2EE0, 0x802A3CF4),
    "sine_helper": (0x802B2ECC, 0x8002F898),
}


class Abstain(Exception):
    pass


def discover_private_scripts(repo: Path) -> Path:
    """Only inspect a bounded nearby project structure, never search whole disk."""
    base = repo.parent.resolve(strict=True)
    found = []
    # Exactly one, two or three directory levels beneath the Projects parent;
    # never recursively scan user profile, disk roots, or arbitrary locations.
    for pattern in (
        "*/scripts/p0_calc_magnitude_upstream_private.py",
        "*/*/scripts/p0_calc_magnitude_upstream_private.py",
        "*/*/*/scripts/p0_calc_magnitude_upstream_private.py",
    ):
        for file in base.glob(pattern):
            try:
                if (file.is_symlink() or not file.is_file()
                        or file.parent.is_symlink() or file.parent.parent.is_symlink()):
                    continue
                folder = file.parent.resolve(strict=True)
                if not folder.is_relative_to(base):
                    continue
                names = (
                    "audit_p0_seven_numbered_source_pairs_private.py",
                    "audit_p0_inflight_vs_b0_private.py",
                    "audit_golf_two_bank_roster_private.py",
                )
                if all((folder / n).is_file() and not (folder / n).is_symlink()
                       for n in names):
                    found.append(folder)
            except OSError:
                continue
    unique = list(dict.fromkeys(found))
    if len(unique) == 1:
        return unique[0]
    if len(unique) > 1:
        # Distinguish an exact existing operator audit checkout by its
        # repository leaf name, not an absolute private filesystem path.
        matching = [
            folder for folder in unique
            if folder.parent.name == "Wii-AI-Golf-Calc-Source-Audit"
        ]
        if len(matching) == 1:
            return matching[0]
        raise Abstain("PRIVATE_HELPER_AMBIGUOUS")
    raise Abstain("PRIVATE_HELPER_MISSING")


def decode_bl(pc: int, word: int) -> tuple[int, bool] | None:
    if word >> 26 != 18:
        return None
    delta = word & 0x03FFFFFC
    if delta & 0x02000000:
        delta -= 0x04000000
    target = (delta if word & 2 else pc + delta) & 0xFFFFFFFF
    return target, bool(word & 1)


def signed16(value: int) -> int:
    return value - 65536 if value & 32768 else value


def symbolize(pc: int, word: int) -> dict:
    if not (SOURCE_UNIT[0] <= pc < SOURCE_UNIT[1]) or pc % 4:
        raise Abstain("OUT_OF_BOUNDS")
    op = word >> 26
    row = {"pc": f"0x{pc:08X}", "class": f"op{op}"}
    dforms = {
        14: "addi", 15: "addis", 32: "lwz", 34: "lbz", 36: "stw",
        38: "stb", 40: "lhz", 42: "lha", 44: "sth", 48: "lfs",
        50: "lfd", 52: "stfs", 54: "stfd",
    }
    if op in dforms:
        row.update({"class": dforms[op], "reg": (word >> 21) & 31,
                    "base": (word >> 16) & 31, "disp": signed16(word & 65535)})
    elif op == 18:
        branch = decode_bl(pc, word)
        if branch is None:
            raise Abstain("BAD_BRANCH")
        row.update({"class": "bl" if branch[1] else "b",
                    "target": f"0x{branch[0]:08X}"})
    elif op == 16:
        delta = word & 0x0000FFFC
        if delta & 0x8000:
            delta -= 65536
        target = (delta if word & 2 else pc + delta) & 0xFFFFFFFF
        row.update({"class": "bc", "target": f"0x{target:08X}",
                    "bo": (word >> 21) & 31, "bi": (word >> 16) & 31})
    elif op in (59, 63):
        xo5 = (word >> 1) & 31
        xo10 = (word >> 1) & 1023
        if op == 59:
            cls = {18: "fdivs", 20: "fsubs", 21: "fadds",
                   25: "fmuls", 29: "fmadds"}.get(xo5, "fp59")
        else:
            cls = {0: "fcmpu", 12: "frsp", 32: "fcmpo",
                   40: "fneg", 72: "fmr", 264: "fabs"}.get(xo10, "fp63")
        row.update({"class": cls, "frt": (word >> 21) & 31,
                    "fra": (word >> 16) & 31, "frb": (word >> 11) & 31,
                    "frc": (word >> 6) & 31, "xo": xo5 if op == 59 else xo10})
    elif op == 19:
        xo = (word >> 1) & 1023
        row.update({"class": {16: "bclr", 528: "bcctr", 449: "cror"}.get(xo, "op19"),
                    "xo": xo})
    elif op == 31:
        row.update({"class": "int_xform", "rd": (word >> 21) & 31,
                    "ra": (word >> 16) & 31, "rb": (word >> 11) & 31,
                    "xo": (word >> 1) & 1023})
    elif op == 21:
        row.update({"class": "rlwinm", "rs": (word >> 21) & 31,
                    "ra": (word >> 16) & 31})
    elif op in (10, 11):
        row.update({"class": "cmplwi" if op == 10 else "cmpwi",
                    "ra": (word >> 16) & 31,
                    "imm": (word & 65535) if op == 10 else signed16(word & 65535)})
    return row


def research(segment: str) -> dict:
    stage = "PRIVATE_HELPER_DISCOVERY"
    try:
        repo = Path(__file__).resolve().parents[1]
        scripts = discover_private_scripts(repo)
        sys.path.insert(0, str(scripts))
        os.environ["WII_GOLF_AUDIT_SCRIPTS"] = str(scripts)
        stage = "IMPORT"
        audit = importlib.import_module("p0_calc_magnitude_upstream_private")
        original = importlib.import_module("audit_p0_seven_numbered_source_pairs_private")
        inflight = importlib.import_module("audit_p0_inflight_vs_b0_private")
        roster = importlib.import_module("audit_golf_two_bank_roster_private")
        stage = "ORIGINAL_14_BANK_GATE"
        archive = audit._default_archive(audit.DATA)
        receipt = audit.run(archive)
        if (receipt.get("status") != "REV1_CALC_UPSTREAM_STATIC_SOURCE_PASS"
                or receipt.get("original_14_bank_sha_pre_and_post_verified") is not True
                or receipt.get("complete_golf_text_phases_1_5_7_identical") is not True):
            raise Abstain("ORIGINAL_GATE_FAILED")
        folders = original._check_archive(archive)
        stage = "ORIGINAL_SEGMENT_AND_CALLS"
        lo, hi = SEGMENTS[segment]
        if not (SOURCE_UNIT[0] <= lo < hi <= SOURCE_UNIT[1]):
            raise Abstain("SEGMENT_OUT_OF_BOUNDS")
        with ExitStack() as stack:
            banks = []
            for phase in (1, 5, 7):
                bank = inflight._file(folders[phase], f"{phase}.1.raw", roster.MEM1_SIZE)
                handle = stack.enter_context(bank.open("rb"))
                banks.append(stack.enter_context(
                    mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)))

            def read(pc: int, index: int = 0) -> int:
                off = pc - roster.MEM1_BASE
                if pc % 4 or off < 0 or off + 4 > roster.MEM1_SIZE:
                    raise Abstain("PC_OUTSIDE_MEM1")
                return int.from_bytes(banks[index][off:off + 4], "big")

            gates = {
                name: all(decode_bl(pc, read(pc, i)) == (target, True)
                          for i in range(3))
                for name, (pc, target) in CALLS.items()
            }
            if not all(gates.values()):
                raise Abstain("CALL_TARGET_CHANGED")
            if any(read(pc) != read(pc, i)
                   for pc in range(lo, hi, 4) for i in (1, 2)):
                raise Abstain("ORIGINAL_PHASES_DIFFER")
            rows = [symbolize(pc, read(pc)) for pc in range(lo, hi, 4)]
        stage = "ORIGINAL_POST_READ_SHA"
        original._check_archive(archive)
        return {
            "status": "REV1_GOLF_MATH_TRIG_SOURCE_PASS",
            "segment": segment, "source_unit": "RPGolMathTrig.cpp",
            "original_14_bank_verified": True, "phase_1_5_7_code_equal": True,
            "call_target_gates": gates, "symbolic_instructions": rows,
            "raw_original_bytes_published": False, "exact_function_boundary_proven": False,
            "guest_execution_verified": False, "training_approved": False,
        }
    except Abstain as exc:
        # These enumerated codes contain no private paths or native data.
        return {"status": "DIAGNOSTIC_ABSTAIN", "failed_stage": stage,
                "reason_code": str(exc), "training_approved": False}
    except (Exception, KeyboardInterrupt):
        return {"status": "DIAGNOSTIC_ABSTAIN", "failed_stage": stage,
                "reason_code": "UNCLASSIFIED_SOURCE_EXCEPTION",
                "training_approved": False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--segment", choices=sorted(SEGMENTS), required=True)
    args = parser.parse_args(argv)
    report = research(args.segment)
    print(json.dumps(report, separators=(",", ":")))
    return 0 if report["status"].endswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
