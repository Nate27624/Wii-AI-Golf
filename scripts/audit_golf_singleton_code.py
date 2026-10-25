"""Offline, bounded Wii Sports USA Rev1 PowerPC symbol-reference audit.

Input: local extracted main.dol ONLY, never an ISO/WBFS, ROM upload, or RPC.
Examines three source-anchored callsites that access RPSysSceneMgr and
reports common r13-relative load offsets. These are UNVERIFIED candidates
for singleton pointer storage, not a safe address to dereference.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys

MAX_DOL_BYTES = 32 * 1024 * 1024
# Start addresses and exact function sizes documented in kiwi515/ogws_info
# RSPE_r1.map for NTSC-U Rev1. Never change these for a different disc.
TARGETS = {
    "RPSysSceneCreator::changeSceneAfterFade": (0x80184BA4, 0x26C),
    "RPSysScene::setSceneFadeColor": (0x80185484, 0x48),
    "RPSysScene::setFadeColor": (0x801854CC, 0x48),
}


def sections(dol: bytes):
    if not 0x100 <= len(dol) <= MAX_DOL_BYTES:
        raise ValueError("DOL header missing or file outside 32 MiB bound")
    entries = []
    # Nintendo DOL header: 7 text sections then 11 data sections.
    for count, foff, voff, soff in ((7, 0, 0x48, 0x90),
                                   (11, 0x1C, 0x64, 0xAC)):
        for i in range(count):
            offset = struct.unpack_from(">I", dol, foff + 4 * i)[0]
            address = struct.unpack_from(">I", dol, voff + 4 * i)[0]
            size = struct.unpack_from(">I", dol, soff + 4 * i)[0]
            if not size:
                continue
            if offset < 0x100 or offset + size > len(dol) or size > MAX_DOL_BYTES:
                raise ValueError("invalid DOL section bounds")
            if address % 4 or not (0x80000000 <= address < 0x94000000):
                raise ValueError("invalid DOL mapped address")
            entries.append((address, address + size, offset))
    return entries


def get_code(dol: bytes, addr: int, size: int) -> bytes:
    if size < 4 or size % 4 or addr % 4:
        raise ValueError("invalid code range")
    for low, high, file_offset in sections(dol):
        if low <= addr and addr + size <= high:
            begin = file_offset + (addr - low)
            return dol[begin:begin + size]
    raise ValueError("Rev1 function range not mapped: code source or disc version differs")


def load_references(code: bytes):
    # Big-endian PPC D-form: lwz is opcode 32; RA == 13 is the EABI
    # mutable small-data area base. Static pointers commonly use it,
    # but other globals do as well; never auto-identify a singleton.
    offsets = set()
    for pos in range(0, len(code), 4):
        word = struct.unpack_from(">I", code, pos)[0]
        op = word >> 26
        ra = (word >> 16) & 31
        if op == 32 and ra == 13:
            disp = struct.unpack(">h", struct.pack(">H", word & 0xFFFF))[0]
            offsets.add(disp)
    return offsets


def analyze(dol: bytes) -> dict:
    refs = {name: load_references(get_code(dol, *position))
            for name, position in TARGETS.items()}
    cross = {}
    for name, displacements in refs.items():
        for displacement in displacements:
            cross.setdefault(displacement, []).append(name)
    shared = [
        {"sda_displacement": f"{'+' if d >= 0 else '-'}0x{abs(d):X}",
         "independent_callsite_count": len(names),
         "callsite_names": sorted(names)}
        for d, names in cross.items() if len(names) >= 2
    ]
    shared.sort(key=lambda e: (-e["independent_callsite_count"],
                               e["sda_displacement"]))
    return {
        "schema_version": 1,
        "kind": "offline_rev1_scene_singleton_code_reference_triage",
        "inspected_callsites": list(TARGETS),
        "r13_load_counts": {name: len(offsets) for name, offsets in refs.items()},
        "shared_r13_displacements": shared,
        "scene_manager_singleton_storage_address": None,
        "game_revision_verified_from_dol_alone": False,
        "runtime_pointer_verified": False,
        "warning": (
            "Shared offsets are candidates only: other globals may share callsites. "
            "No singleton address or object type is established without disassembly "
            "and independent Rev1 validation. No memory is read or modified."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dol", type=Path, required=True,
                        help="Locally extracted main.dol from legally held RSPE01 Rev1 disc")
    args = parser.parse_args(argv)
    try:
        if not args.dol.is_file() or not 0 < args.dol.stat().st_size <= MAX_DOL_BYTES:
            raise ValueError("DOL file missing or oversized")
        result = analyze(args.dol.read_bytes())
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print(f"Offline Rev1 singleton triage failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
