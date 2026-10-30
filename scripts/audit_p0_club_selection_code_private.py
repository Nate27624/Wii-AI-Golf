#!/usr/bin/env python3
"""Static read-only PowerPC triage for the selected Golf club state.

Consumes ONLY the original SHA-verified private seven-pair Rev1 archive,
scans published Rev1 Golf .text source units, and reports CODE-relative
candidate stores. No live emulator, controller input, memory writes, native
game bytes in stdout, or claim of an identified club index.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import json
import mmap
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
MEM1 = 0x80000000
MEM1_LEN = 0x01800000
INDEX = ROOT / "research/source_maps/RSPE01_01_public_text_units.json"
SOURCE_UNITS = (
    "Pack/RPSports/RPGolScene/RPGolMain.cpp",
    "Pack/RPSports/RPGolScene/RPGolConfig.cpp",
    "Pack/RPSports/RPGolScene/RPGolPlayer.cpp",
    "Pack/RPSports/RPGolScene/RPGolPlayerManager.cpp",
    "Pack/RPSports/RPGolScene/RPGolScene_unsplit.o",
)
CONTROLLERS = (
    "Pack/RPKernel/RPSysController.cpp",
    "Pack/RPKernel/RPSysControllerMgr.cpp",
)
STORES = {36: "stw", 38: "stb", 44: "sth"}
LOADS = {32: "lwz", 34: "lbz", 40: "lhz", 42: "lha"}

class Abstain(Exception):
    """Sanitized failure; never print private native paths or bytes."""

def require(value, reason="INPUT_UNQUALIFIED"):
    if not value:
        raise Abstain(reason)

def signed16(value):
    return (value & 65535) - 65536 if value & 32768 else value & 65535

def signed26(value):
    value &= 0x03FFFFFC
    return value - 0x04000000 if value & 0x02000000 else value

def op(word):
    return word >> 26

def decode_access(word):
    name = STORES.get(op(word)) or LOADS.get(op(word))
    if name is None:
        return None
    return {"op": name, "reg": (word >> 21) & 31,
            "base": (word >> 16) & 31, "disp": signed16(word)}

def decode_branch(pc, word):
    if op(word) != 18:
        return None
    target = signed26(word) + (0 if word & 2 else pc)
    return {"target": target & 0xffffffff, "link": bool(word & 1)}

def small_compare(word):
    return op(word) in (10, 11) and 0 <= signed16(word) <= 8

def ordinal_step(word):
    return op(word) == 14 and ((word >> 16) & 31) != 0 and signed16(word) in (-1, 1)

def button_mask_shape(word):
    # andi./andis. shape. Button meaning NOT established.
    return op(word) in (28, 29) and bool(word & 0xffff)

def source_units(payload):
    require(isinstance(payload, dict)
            and payload.get("kind") == "PUBLIC-RSPE01-REV1-TEXT-OBJECT-SPLITS"
            and payload.get("game_id") == "RSPE01"
            and payload.get("disc_revision") == 1,
            "PUBLIC_SOURCE_MAP_INVALID")
    rows = payload.get("intervals")
    require(isinstance(rows, list) and len(rows) >= 100,
            "PUBLIC_SOURCE_MAP_INCOMPLETE")
    units = {}
    last = 0
    for row in rows:
        require(isinstance(row, list) and len(row) == 3,
                "PUBLIC_SOURCE_MAP_BAD_INTERVAL")
        lo, hi, name = row
        require(type(lo) is int and type(hi) is int
                and isinstance(name, str) and lo % 4 == hi % 4 == 0
                and lo >= last and lo < hi <= MEM1 + MEM1_LEN,
                "PUBLIC_SOURCE_MAP_BAD_INTERVAL")
        units[name] = (lo, hi)
        last = hi
    require(all(name in units for name in SOURCE_UNITS + CONTROLLERS),
            "PUBLIC_SOURCE_MAP_MISSING_GOLF_UNIT")
    return units

def candidate_sites(code, origin, unit, controller_ranges):
    """Heuristic store sites, not traced club setters or receiver roots."""
    require(origin % 4 == 0 and len(code) % 4 == 0
            and 0 < len(code) <= 0x40000, "BAD_CODE_WINDOW")
    words = struct.unpack(">" + "I" * (len(code) // 4), code)
    found = []
    for i, word in enumerate(words):
        a = decode_access(word)
        if a is None or a["op"] not in STORES.values():
            continue
        if a["base"] in (0, 1) or not 0 <= a["disp"] <= 0x1FF:
            continue
        lo, hi = max(0, i - 24), min(len(words), i + 9)
        around = words[lo:hi]
        compare = sum(small_compare(w) for w in around)
        step = sum(ordinal_step(w) for w in around)
        mask = sum(button_mask_shape(w) for w in around)
        cond = sum(op(w) == 16 for w in around)
        branches = (decode_branch(origin + 4*j, words[j]) for j in range(lo, hi))
        calls = sum(b is not None and b["link"] and
                    any(p <= b["target"] < q for p, q in controller_ranges)
                    for b in branches)
        if not (compare or step or mask or calls):
            continue
        score = (3 * min(compare, 2) + 3 * min(step, 2)
                 + 2 * min(mask, 2) + min(cond, 2)
                 + 4 * min(calls, 2) + int(a["disp"] < 0xCC))
        found.append({
            "public_source_unit": unit,
            "source_relative_code_offset": "+0x%05X" % (4*i),
            "store_opcode": a["op"],
            "receiver_base_register_not_proven": "r%d" % a["base"],
            "written_register": "r%d" % a["reg"],
            "candidate_object_field_offset": "+0x%03X" % a["disp"],
            "nearby_ordinal_compares": compare,
            "nearby_plus_or_minus_one": step,
            "nearby_bit_mask_tests": mask,
            "nearby_conditional_branches": cond,
            "nearby_direct_controller_calls": calls,
            "heuristic_score": score,
            "club_selector_verified": False,
        })
    found.sort(key=lambda x: (-x["heuristic_score"],
                              x["public_source_unit"],
                              x["source_relative_code_offset"]))
    return found

def inspect_mem1_bank(bank, source_index, limit=25):
    require(len(bank) == MEM1_LEN, "MEM1_SIZE_INVALID")
    require(bytes(bank[0:6]) == b"RSPE01" and bank[7] == 1,
            "REV1_EXECUTABLE_HEADER_INVALID")
    units = source_units(source_index)
    controller_ranges = [units[name] for name in CONTROLLERS]
    hits = []
    counts = {}
    for name in SOURCE_UNITS:
        lo, hi = units[name]
        begin, end = lo - MEM1, hi - MEM1
        require(0 <= begin < end <= len(bank), "SOURCE_CODE_NOT_IN_MEM1")
        local = candidate_sites(bytes(bank[begin:end]), lo, name, controller_ranges)
        counts[name] = len(local)
        hits.extend(local)
    hits.sort(key=lambda x: (-x["heuristic_score"],
                              x["public_source_unit"],
                              x["source_relative_code_offset"]))
    return {
        "status": "SOURCE_STATIC_CLUB_SELECTOR_TRIAGE",
        "disc_id": "RSPE01", "revision": 1,
        "original_archive_sha_preflight_passed": True,
        "public_code_map": "doldecomp/ogws RSPE01_01 splits.txt",
        "source_units": list(SOURCE_UNITS),
        "candidate_sites_by_unit": counts,
        "total_candidate_store_sites": len(hits),
        "ranked_sites": hits[:limit],
        "sites_omitted": max(0, len(hits)-limit),
        "executed_dpad_path_verified": False,
        "receiver_pointer_chain_verified": False,
        "native_club_index_verified": False,
        "training_approved": False,
        "warning": "Static nearby-code heuristics only. D-pad meaning, function boundaries, indirect calls and selected receiver remain unknown.",
    }

def sealed_bank(archive, capture_number):
    # Canonical original seven-pair SHA and layout verifier; no new evidence
    # format, new private-root finder or arbitrary native-address dump.
    sys.path.insert(0, str(ROOT / "scripts"))
    import audit_p0_seven_numbered_source_pairs_private as original
    require(capture_number in range(1, 8), "CAPTURE_INVALID")
    original._check_archive(archive)
    file = archive.resolve(strict=True) / ("%d.1.raw" % capture_number)
    require(file.is_file() and not file.is_symlink()
            and file.stat().st_size == MEM1_LEN, "SEALED_MEM1_INVALID")
    return file

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path)
    p.add_argument("--capture", type=int, default=5, choices=range(1, 8))
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args(argv)
    if a.selftest:
        w = [0x2C030003, 0x38630001, 0x41820008, 0x90630020]
        result = candidate_sites(struct.pack(">4I", *w),
                                 0x8029e62c, SOURCE_UNITS[2], [])
        require(len(result) == 1
                and result[0]["candidate_object_field_offset"] == "+0x020",
                "SELFTEST_FAILURE")
        print(json.dumps({"status": "SELFTEST_PASS", "native_access": False}))
        return 0
    if a.archive is None or not 1 <= a.limit <= 50:
        print(json.dumps({"status": "ABSTAIN_ARGS", "training_approved": False}))
        return 2
    try:
        file = sealed_bank(a.archive, a.capture)
        source_index = json.loads(INDEX.read_text("utf-8"))
        with file.open("rb") as fd, closing(mmap.mmap(fd.fileno(), 0, access=mmap.ACCESS_READ)) as mm:
            report = inspect_mem1_bank(mm, source_index, a.limit)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (Abstain, ValueError, OSError, TypeError, KeyError, IndexError, ImportError):
        print(json.dumps({"status": "ABSTAIN_PRIVATE_SOURCE_OR_ARCHIVE",
                          "training_approved": False}))
        return 3

if __name__ == "__main__":
    raise SystemExit(main())
