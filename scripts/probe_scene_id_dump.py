#!/usr/bin/env python3
"""Read-only, source-derived P0 scene_id candidates in *private* RSPE01 rev1 RAM dumps.

This tool never starts Dolphin, writes memory, or uploads data. A matching snapshot
is a corroborated candidate, NOT independently verified live RAM behavior.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys

MEM1_BASE = 0x80000000
MEM1_SIZE = 0x01800000  # Wii MEM1 physical 24 MiB
MEM2_BASE = 0x90000000
MEM2_SIZE = 0x04000000  # Wii MEM2 physical 64 MiB
SCENE_MGR_SINGLETON_SLOTS = (0x804BF4D8, 0x804BF4DC)  # entire 8-byte .sbss section
MGR_CURRENT_SCENE_PTR_OFF = 0x0C
MGR_CURRENT_SCENE_ID_OFF = 0x18
SCENE_SCENE_ID_OFF = 0x1C  # US Rev1 EGG::Scene
SCENE_MGR_BACKPTR_OFF = 0x20
SCENE_GOLF = 5

class DumpError(ValueError):
    pass

class Banks:
    def __init__(self, mem1: Path, mem2: Path):
        self.mem1 = Path(mem1)
        self.mem2 = Path(mem2)
        for p, size, label in ((self.mem1, MEM1_SIZE, "MEM1"), (self.mem2, MEM2_SIZE, "MEM2")):
            actual = p.stat().st_size
            if actual != size:
                raise DumpError(f"{label} must be exactly {size} bytes; found {actual} bytes")
        self._f1 = None
        self._f2 = None

    def __enter__(self):
        self._f1 = self.mem1.open('rb')
        try:
            self._f2 = self.mem2.open('rb')
        except Exception:
            self._f1.close()
            raise
        return self

    def __exit__(self, *exc):
        self._f1.close()
        self._f2.close()

    def read(self, addr: int, length: int) -> bytes:
        if not isinstance(addr, int) or addr < 0 or length < 1:
            raise DumpError("invalid address or length")
        if MEM1_BASE <= addr and addr + length <= MEM1_BASE + MEM1_SIZE:
            handle, base = self._f1, MEM1_BASE
        elif MEM2_BASE <= addr and addr + length <= MEM2_BASE + MEM2_SIZE:
            handle, base = self._f2, MEM2_BASE
        else:
            raise DumpError(f"address 0x{addr:08X} not inside captured MEM1/MEM2")
        handle.seek(addr - base)
        raw = handle.read(length)
        if len(raw) != length:
            raise DumpError("truncated RAM dump")
        return raw

    def u32(self, addr: int) -> int:
        if addr & 3:
            raise DumpError(f"unaligned u32 at 0x{addr:08X}")
        return struct.unpack('>I', self.read(addr, 4))[0]


def examine(banks: Banks, expect: int | None = SCENE_GOLF) -> dict:
    game = banks.read(0x80000000, 4)
    revision = banks.read(0x80000007, 1)[0]
    if game != b'RSPE' or revision != 1:
        raise DumpError(f"requires RSPE01 US Rev1 header (RSPE, disc revision 1); observed {game!r}, rev {revision}")
    candidates = []
    for slot in SCENE_MGR_SINGLETON_SLOTS:
        candidate = {"slot": f"0x{slot:08X}", "status": "rejected"}
        try:
            manager = banks.u32(slot)
            candidate["manager_pointer"] = f"0x{manager:08X}"
            if manager == 0:
                raise DumpError("null singleton pointer")
            scene_ptr = banks.u32(manager + MGR_CURRENT_SCENE_PTR_OFF)
            manager_id = banks.u32(manager + MGR_CURRENT_SCENE_ID_OFF)
            if not 0 <= manager_id <= 14:
                raise DumpError(f"out-of-range manager scene ID {manager_id}")
            if scene_ptr == 0:
                raise DumpError("null current scene")
            scene_id = banks.u32(scene_ptr + SCENE_SCENE_ID_OFF)
            backptr = banks.u32(scene_ptr + SCENE_MGR_BACKPTR_OFF)
            candidate.update({"scene_pointer": f"0x{scene_ptr:08X}",
                              "scene_id_field_address": f"0x{manager + MGR_CURRENT_SCENE_ID_OFF:08X}",
                              "manager_scene_id": manager_id,
                              "scene_object_scene_id": scene_id,
                              "scene_manager_backptr": f"0x{backptr:08X}"})
            if scene_id != manager_id:
                raise DumpError("scene object's scene ID differs from manager ID")
            if backptr != manager:
                raise DumpError("scene object does not point back to manager")
            candidate["status"] = "source_layout_consistent"
            if expect is not None and manager_id != expect:
                candidate["status"] = "expected_scene_mismatch"
                candidate["reason"] = f"expected scene {expect}, observed {manager_id}"
        except (DumpError, ValueError) as exc:
            candidate["reason"] = str(exc)
        candidates.append(candidate)
    valid = [x for x in candidates if x["status"] == "source_layout_consistent"]
    if len(valid) > 1:
        outcome = "ambiguous_multiple_slots"
    elif len(valid) == 1:
        outcome = "snapshot_consistent_not_runtime_verified"
    else:
        outcome = "no_consistent_slot"
    return {"kind": "PRIVATE-offline-rspe01-rev1-scene-id-diagnostic", "expected_scene_id": expect,
            "status": outcome, "candidate_slots": candidates,
            "verified_live": False, "approved_for_model_training": False,
            "note": "Requires independent fresh-boot and non-Golf negative controls before declaring RAM variable verified."}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mem1', required=True, type=Path, help='private raw 24 MiB MEM1 dump')
    parser.add_argument('--mem2', required=True, type=Path, help='private raw 64 MiB MEM2 dump')
    parser.add_argument('--expect', type=int, default=SCENE_GOLF, help='expected scene ID (Golf=5, main menu=9)')
    args = parser.parse_args(argv)
    try:
        with Banks(args.mem1, args.mem2) as banks:
            result = examine(banks, args.expect)
    except (DumpError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'snapshot_consistent_not_runtime_verified' else 1

if __name__ == '__main__':
    raise SystemExit(main())
