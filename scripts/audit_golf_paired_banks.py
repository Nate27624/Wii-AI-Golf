"""Read-only source-gated, one-pair MEM1/MEM2 structural inventory.

Inputs are native copies in sibling Wii-AI-Golf-Data; no Dolphin/RPC, RAM
writes, network, publication, physics labels or runtime pointer output.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import struct
import sys

MEM1_BASE, MEM1_BYTES = 0x80000000, 24 * 1024 * 1024
MEM2_BASE, MEM2_BYTES = 0x90000000, 64 * 1024 * 1024
SCENE_MANAGER_SLOT = 0x804BF4D8
CONFIG_SLOT = 0x804BF8C4
FIELD_SLOT = 0x804BF868
SOURCE_MAIN_DATA = (0x803C7798, 0x803C77C0)
FIELD_POINTERS = {
    "map_data": 0x18, "current_pin": 0x44, "current_start": 0x50,
    "cup": 0x54, "wind_object": 0x68, "course_object": 0x70,
}


class UnsupportedPair(ValueError):
    """Raw source identity, format, or memory range was not verified."""


class Banks:
    def __init__(self, mem1, mem2):
        if len(mem1) != MEM1_BYTES or len(mem2) != MEM2_BYTES:
            raise UnsupportedPair("bad bank size")
        self.regions = (("MEM1", MEM1_BASE, mem1),
                        ("MEM2", MEM2_BASE, mem2))

    def which(self, address, length=4):
        if (type(address) is not int or type(length) is not int
                or length <= 0 or address % 4):
            return None
        for label, base, memory in self.regions:
            if base <= address and address + length <= base + len(memory):
                return label
        return None

    def read(self, address, size):
        found = self.which(address, size)
        if found is None:
            raise UnsupportedPair("unmapped source member")
        for label, base, memory in self.regions:
            if label == found:
                return bytes(memory[address - base:address - base + size])
        raise UnsupportedPair("unmapped bank")

    def u32(self, address):
        return struct.unpack(">I", self.read(address, 4))[0]

    def pointer(self, address, size=4, *, nullable=False):
        value = self.u32(address)
        if nullable and value == 0:
            return 0
        if self.which(value, size) is None:
            raise UnsupportedPair("invalid pointer range")
        return value


def inventory(mem1, mem2):
    """One-bank-pair diagnostic, NOT a same-frame, typed object or power proof."""
    b = Banks(mem1, mem2)
    if bytes(mem1[:8]) != b"RSPE01\x00\x01":
        raise UnsupportedPair("wrong Wii Sports revision")
    manager = b.pointer(SCENE_MANAGER_SLOT, 0x1C)
    if b.u32(manager + 0x18) != 5:
        raise UnsupportedPair("wrong scene ID")
    scene = b.pointer(manager + 0x0C, 0xA0)
    if (b.u32(scene + 0x1C) != 5 or b.u32(scene + 0x20) != manager
            or b.u32(scene + 0x54) != 2):
        raise UnsupportedPair("scene ID/sport/backlink mismatch")
    main = b.pointer(scene + 0x9C, 0x100)
    config = b.pointer(CONFIG_SLOT, 0x9C)
    if b.u32(config + 0x94) != 4:
        raise UnsupportedPair("wrong golf mode")
    hole = b.u32(config + 0x98)
    if hole > 31:
        raise UnsupportedPair("hole index out of bounds")
    field = b.pointer(FIELD_SLOT, 0x8C)
    pins, starts = b.u32(field + 0x3C), b.u32(field + 0x48)
    if pins > 256 or starts > 256:
        raise UnsupportedPair("implausible map object counts")
    refs = {}
    for label, offset in FIELD_POINTERS.items():
        value = b.pointer(field + offset, nullable=True)
        refs[label] = {
            "present": bool(value), "bank": b.which(value) if value else "absent"
        }
    data = b.read(main, 0x100)
    pointer_counts = {"MEM1": 0, "MEM2": 0}
    for (value,) in struct.iter_unpack(">I", data):
        label = b.which(value)
        if label:
            pointer_counts[label] += 1
    initial_word = struct.unpack_from(">I", data)[0]
    return {
        "schema_version": 1,
        "kind": "local_golf_paired_bank_source_inventory",
        "game_id": "RSPE01", "disc_revision": 1,
        "bank_lengths": {"MEM1": MEM1_BYTES, "MEM2": MEM2_BYTES},
        "scene_id": 5, "sport_id": 2, "game_mode_raw": 4,
        "current_hole_raw": hole,
        "source_scene_chain_verified_in_combined_images": True,
        "object_banks": {
            "scene_manager": b.which(manager),
            "golf_scene": b.which(scene),
            "candidate_golf_main": b.which(main),
            "golf_config": b.which(config),
            "field_manager": b.which(field),
        },
        "field_object_counts": {"pin": pins, "start": starts},
        "field_member_refs": refs,
        "candidate_main_first_256_bytes_pointer_shaped_by_bank": pointer_counts,
        "main_first_word_in_source_module_data_range": (
            SOURCE_MAIN_DATA[0] <= initial_word < SOURCE_MAIN_DATA[1]
        ),
        "same_frame_verified": False, "same_boot_verified": False,
        "golf_main_type_verified": False, "player_pose_verified": False,
        "club_pose_verified": False, "ball_xyz_verified": False,
        "ball_velocity_verified": False, "pin_xyz_verified": False,
        "wind_vector_verified": False, "swing_power_verified": False,
        "warning": (
            "Source-derived pointer structure only; sequential RAM exports are "
            "not proven same-frame or same-boot. Pointer-shaped words and "
            "source module data hints do not verify gameplay object type, "
            "ball/club physics, wind, power, or score. No private memory, "
            "addresses, file paths or hashes are included."
        ),
    }


def _private(path, root, size):
    if (not path.is_file() or path.is_symlink()
            or path.stat().st_size != size
            or not path.resolve().is_relative_to(root.resolve())):
        raise UnsupportedPair("invalid private bank file")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mem1", type=Path, required=True)
    parser.add_argument("--mem2", type=Path, required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1].parent / "Wii-AI-Golf-Data"
    try:
        if not root.is_dir() or root.is_symlink():
            raise UnsupportedPair("missing private Data root")
        _private(args.mem1, root, MEM1_BYTES)
        _private(args.mem2, root, MEM2_BYTES)
        if args.mem1.resolve() == args.mem2.resolve():
            raise UnsupportedPair("duplicate bank input")
        with ExitStack() as stack:
            files = [stack.enter_context(p.open("rb")) for p in
                     (args.mem1, args.mem2)]
            views = [stack.enter_context(
                mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ))
                for f in files]
            result = inventory(*views)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (UnsupportedPair, OSError, ValueError, struct.error):
        print("Paired-bank audit stopped: unsupported or inconsistent private "
              "images. Raw values were not printed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
