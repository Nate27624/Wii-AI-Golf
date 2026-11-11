"""Verify a Wii Sports RSPE01 Rev1 scene-manager singleton-storage candidate.

Offline code pattern check only. Does not read RAM, run Dolphin, or prove a
live scene pointer. The DOL alone does not independently prove disc revision.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("golf_singleton_code", HERE / "audit_golf_singleton_code.py")
_audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_audit)

R13_SETUP = 0x80006314
MANAGER_CTOR = 0x80186108
MANAGER_CTOR_SIZE = 0x104


def _words(data: bytes):
    return [struct.unpack_from(">I", data, i)[0] for i in range(0, len(data), 4)]


def _dform(word: int, opcode: int, reg: int, ra: int, displacement: int) -> bool:
    return (word >> 26) == opcode and ((word >> 21) & 31) == reg and ((word >> 16) & 31) == ra and (word & 65535) == (displacement & 65535)


def verify(dol: bytes) -> dict:
    common = None
    for name, (address, length) in _audit.TARGETS.items():
        refs = _audit.load_references(_audit.get_code(dol, address, length))
        common = refs if common is None else common.intersection(refs)
    common = common or set()
    if len(common) != 1:
        raise ValueError("cannot identify one unique r13 load common to all three callsites")
    displacement = next(iter(common))
    hi, lo = _words(_audit.get_code(dol, R13_SETUP, 8))
    # addis r13,r0,HI ; ori r13,r13,LO
    if hi >> 16 != 0x3DA0 or lo >> 16 != 0x61AD:
        raise ValueError("r13 initializer instruction pattern does not match Rev1")
    r13_base = (((hi & 0xFFFF) << 16) | (lo & 0xFFFF)) & 0xFFFFFFFF
    location = (r13_base + displacement) & 0xFFFFFFFF
    ctor = _words(_audit.get_code(dol, MANAGER_CTOR, MANAGER_CTOR_SIZE))
    load_indices = [i for i, word in enumerate(ctor) if _dform(word, 32, 0, 13, displacement)]
    store_indices = [i for i, word in enumerate(ctor) if _dform(word, 36, 30, 13, displacement)]
    if len(load_indices) != 1 or len(store_indices) != 1 or load_indices[0] >= store_indices[0]:
        raise ValueError("scene manager constructor load/store signature absent or ambiguous")
    if not (0x80000000 <= location < 0x94000000) or location % 4:
        raise ValueError("derived static location outside aligned Wii memory")
    bss_start = struct.unpack_from(">I", dol, 0xD8)[0]
    bss_size = struct.unpack_from(">I", dol, 0xDC)[0]
    if not (bss_start <= location <= bss_start + bss_size - 4):
        raise ValueError("derived static pointer storage is not inside declared BSS")
    return {
        "schema_version": 1,
        "kind": "offline_golf_scene_manager_singleton_slot_verification",
        "candidate_storage_address": f"0x{location:08X}",
        "r13_base": f"0x{r13_base:08X}",
        "shared_r13_offset": ("+" if displacement >= 0 else "-") + f"0x{abs(displacement):X}",
        "independent_load_callsites": len(_audit.TARGETS),
        "ctor_r13_load_confirmed": True,
        "ctor_r13_store_confirmed": True,
        "candidate_inside_declared_bss": True,
        "scene_manager_runtime_pointer": None,
        "active_golf_scene_pointer": None,
        "golf_main_pointer": None,
        "revision_proven_by_executable_alone": False,
        "warning": "Source-anchored candidate static storage only, not a live object or verified golf state; corroborate Rev1 and runtime before dereferencing.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dol", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if not args.dol.is_file() or not 0 < args.dol.stat().st_size <= _audit.MAX_DOL_BYTES:
            raise ValueError("DOL missing or oversized")
        print(json.dumps(verify(args.dol.read_bytes()), sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print(f"Scene manager slot verification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
