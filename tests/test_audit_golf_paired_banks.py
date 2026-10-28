"""Synthetic sparse-bank tests; no private RAM or emulator."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import struct
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_golf_paired_banks.py"
SPEC = importlib.util.spec_from_file_location("bank_audit", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class SparseBank:
    def __init__(self, size):
        self.size = size
        self.data = {}

    def __len__(self):
        return self.size

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, end, step = key.indices(self.size)
            return bytes(self.data.get(i, 0) for i in range(start, end, step))
        return self.data.get(key, 0)

    def put(self, location, value):
        for i, byte in enumerate(value):
            self.data[location + i] = byte

    def word(self, address, value, base):
        self.put(address - base, struct.pack(">I", value))


def source_pair():
    a = SparseBank(AUDIT.MEM1_BYTES)
    b = SparseBank(AUDIT.MEM2_BYTES)
    a.put(0, b"RSPE01\x00\x01")
    mgr = 0x80001000
    scene, main, config, field = 0x90002000, 0x90004000, 0x90005000, 0x90006000
    for address, value in (
        (AUDIT.SCENE_MANAGER_SLOT, mgr), (mgr + 0x18, 5),
        (mgr + 0x0C, scene), (AUDIT.CONFIG_SLOT, config),
        (AUDIT.FIELD_SLOT, field)
    ):
        a.word(address, value, AUDIT.MEM1_BASE)
    for address, value in (
        (scene + 0x1C, 5), (scene + 0x20, mgr), (scene + 0x54, 2),
        (scene + 0x9C, main), (config + 0x94, 4), (config + 0x98, 1),
        (field + 0x3C, 6), (field + 0x48, 31),
        (field + 0x44, 0x90007100), (field + 0x50, 0x90007200),
        (field + 0x54, 0x90007300), (field + 0x68, 0x90007400),
        (field + 0x70, 0x90007500), (field + 0x18, 0x90007600),
        (main, 0x803C7798), (main + 4, 0x90007700),
        (main + 8, 0x80007000)
    ):
        b.word(address, value, AUDIT.MEM2_BASE)
    return a, b


class PairSourceTests(unittest.TestCase):
    def test_valid_cross_bank_candidate_is_not_claimed_as_physics(self):
        report = AUDIT.inventory(*source_pair())
        self.assertEqual(report["object_banks"]["golf_scene"], "MEM2")
        self.assertEqual(report["object_banks"]["scene_manager"], "MEM1")
        self.assertEqual(report["object_banks"]["candidate_golf_main"], "MEM2")
        self.assertEqual(report["field_member_refs"]["wind_object"]["bank"], "MEM2")
        self.assertEqual(report["candidate_main_first_256_bytes_pointer_shaped_by_bank"],
                         {"MEM1": 2, "MEM2": 1})
        self.assertTrue(report["main_first_word_in_source_module_data_range"])
        self.assertFalse(report["swing_power_verified"])
        self.assertFalse(report["same_frame_verified"])
        self.assertNotIn("0x9000", str(report))
        self.assertNotIn("0x8000", str(report))

    def test_revision_and_scene_backlink_reject(self):
        a, b = source_pair()
        a.put(7, b"\x00")
        with self.assertRaisesRegex(AUDIT.UnsupportedPair, "revision"):
            AUDIT.inventory(a, b)
        a, b = source_pair()
        b.word(0x90002000 + 0x20, 0x80002000, AUDIT.MEM2_BASE)
        with self.assertRaisesRegex(AUDIT.UnsupportedPair, "backlink"):
            AUDIT.inventory(a, b)

    def test_invalid_bank_pointer_rejected(self):
        a, b = source_pair()
        b.word(0x90002000 + 0x9C, 0x94000000, AUDIT.MEM2_BASE)
        with self.assertRaisesRegex(AUDIT.UnsupportedPair, "pointer"):
            AUDIT.inventory(a, b)

    def test_wrong_dimensions_or_game_mode_rejected(self):
        a, b = source_pair()
        with self.assertRaisesRegex(AUDIT.UnsupportedPair, "size"):
            AUDIT.inventory(a, b"too short")
        b.word(0x90005000 + 0x94, 3, AUDIT.MEM2_BASE)
        with self.assertRaisesRegex(AUDIT.UnsupportedPair, "mode"):
            AUDIT.inventory(a, b)

    def test_unmapped_pointer_and_optional_absent_field(self):
        a, b = source_pair()
        b.word(0x90006000 + 0x68, 0, AUDIT.MEM2_BASE)
        output = AUDIT.inventory(a, b)
        self.assertEqual(output["field_member_refs"]["wind_object"],
                         {"present": False, "bank": "absent"})
        b.word(0x90006000 + 0x68, 0x94000000, AUDIT.MEM2_BASE)
        with self.assertRaisesRegex(AUDIT.UnsupportedPair, "pointer"):
            AUDIT.inventory(a, b)


if __name__ == "__main__":
    unittest.main()
