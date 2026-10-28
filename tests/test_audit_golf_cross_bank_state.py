"""Synthetic source-based MEM1/MEM2 checks; no game files or emulator."""
from __future__ import annotations
import json
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.audit.golf_cross_bank_state import audit_pair


def example_banks():
    mem1 = bytearray(0x4BF8D4)
    mem2 = bytearray(0x5000)
    mem1[:8] = b"RSPE01\x00\x01"
    def put(buffer, off, value):
        struct.pack_into(">I", buffer, off, value)
    put(mem1, 0x4BF4D8, 0x80001000)
    put(mem1, 0x4BF8C4, 0x90001000)
    put(mem1, 0x4BF868, 0x90001100)
    put(mem1, 0x4BF8D0, 0x90001200)
    put(mem1, 0x1000 + 0x18, 5)
    put(mem1, 0x1000 + 0x0C, 0x90000100)
    put(mem2, 0x100 + 0x1C, 5)
    put(mem2, 0x100 + 0x20, 0x80001000)
    put(mem2, 0x100 + 0x54, 2)
    put(mem2, 0x100 + 0x9C, 0x90000300)
    put(mem2, 0x300, 0x803C77A8)
    put(mem2, 0x304, 0x90000100)
    put(mem2, 0x1000 + 0x94, 4)
    put(mem2, 0x1000 + 0x98, 1)
    put(mem2, 0x1100 + 0x3C, 6)
    put(mem2, 0x1100 + 0x48, 31)
    for off, ptr in (
        (0x18, 0x90001800), (0x44, 0x90001880),
        (0x50, 0x90001900), (0x54, 0x90001980),
        (0x68, 0x90001A00), (0x70, 0x90001A80)):
        put(mem2, 0x1100 + off, ptr)
    put(mem2, 0x1200, 0x803C7DD0)
    return mem1, mem2


class PairedMemorySourceTests(unittest.TestCase):
    def test_valid_source_chain_and_course_metadata(self):
        a, b = example_banks()
        record = audit_pair(a, b, strict_size=False)
        self.assertTrue(record["source_chain"]["scene_backlink_matches_manager"])
        self.assertEqual(record["conditions"]["game_mode"], 4)
        self.assertEqual(record["conditions"]["raw_current_hole_index"], 1)
        self.assertEqual(record["field_manager"]["pin_object_count"], 6)
        self.assertEqual(record["other_managers"]["player_manager_candidate_region"], "MEM2")
        self.assertFalse(record["main_object"]["power_verified"])
        self.assertFalse(record["provenance"]["same_boot_proven"])

    def test_wrong_disc_revision_fails_closed(self):
        a, b = example_banks()
        a[7] = 0
        with self.assertRaises(ValueError):
            audit_pair(a, b, strict_size=False)

    def test_wrong_manager_backlink_fails_closed(self):
        a, b = example_banks()
        struct.pack_into(">I", b, 0x120, 0)
        with self.assertRaises(ValueError):
            audit_pair(a, b, strict_size=False)

    def test_wrong_sport_fails_closed(self):
        a, b = example_banks()
        struct.pack_into(">I", b, 0x154, 1)
        with self.assertRaises(ValueError):
            audit_pair(a, b, strict_size=False)

    def test_wrong_game_mode_fails_closed(self):
        a, b = example_banks()
        struct.pack_into(">I", b, 0x1094, 2)
        with self.assertRaises(ValueError):
            audit_pair(a, b, strict_size=False)

    def test_missing_static_scene_manager_fails_closed(self):
        a, b = example_banks()
        struct.pack_into(">I", a, 0x4BF4D8, 0)
        with self.assertRaises(ValueError):
            audit_pair(a, b, strict_size=False)

    def test_no_private_runtime_values_leak(self):
        a, b = example_banks()
        payload = json.dumps(audit_pair(a, b, strict_size=False))
        for value in ("0x90000300", "0x80001000", "bytes_hex",
                      "runtime_scene_address", "private_raw"):
            self.assertNotIn(value, payload)

    def test_real_binary_lengths_are_mandatory_by_default(self):
        a, b = example_banks()
        with self.assertRaises(ValueError):
            audit_pair(a, b)


if __name__ == "__main__":
    unittest.main()
