"""Synthetic-only source-bound PPC audit tests; NO real DOL, ROM or Dolphin."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_golf_player_code import analyze, _branch_target, UNITS


BASE = UNITS["RPGolMain"][0]
END = UNITS["RPGolPlayerManager"][1]


def dform(op, rt, ra, disp):
    return (op << 26) | (rt << 21) | (ra << 16) | (disp & 0xFFFF)


def bl(pc, target):
    displacement = target - pc
    assert displacement % 4 == 0 and -(1 << 25) <= displacement < (1 << 25)
    return (18 << 26) | (displacement & 0x03FFFFFC) | 1


def mock_dol():
    offset = 0x100
    code_size = END - BASE
    raw = bytearray(offset + code_size)
    # Valid minimal Nintendo DOL section header: first text section.
    struct.pack_into(">I", raw, 0x00, offset)
    struct.pack_into(">I", raw, 0x48, BASE)
    struct.pack_into(">I", raw, 0x90, code_size)

    def instruction(address, word):
        struct.pack_into(">I", raw, offset + address - BASE, word)

    main = UNITS["RPGolMain"][0]
    player = UNITS["RPGolPlayer"][0]
    manager = UNITS["RPGolPlayerManager"][0]
    instruction(main, dform(32, 9, 3, 0x74))       # lwz  r9,  +0x74(r3)
    instruction(main + 4, dform(36, 9, 3, 0x74))   # stw  r9,  +0x74(r3)
    instruction(main + 8, dform(48, 1, 31, 0x58))  # lfs  f1,  +0x58(r31)
    instruction(main + 12, dform(32, 5, 13, -32))  # lwz  r5,  -0x20(r13) static
    instruction(main + 16, bl(main + 16, player))  # direct call into player
    instruction(main + 20, dform(36, 6, 1, 0x74)) # stw r6, r1-stack EXCLUDED
    instruction(player, dform(52, 1, 30, 0x1C))   # stfs f1, +0x1c(r30)
    instruction(player + 4, bl(player + 4, manager))
    instruction(manager, dform(32, 3, 3, 0x9C))   # lwz r3, +0x9c(r3)
    return bytes(raw)


class OfflineGolfPlayerAccessTests(unittest.TestCase):
    def test_opcode_patterns_and_cross_source_calls(self):
        result = analyze(mock_dol())
        self.assertEqual(result["kind"], "offline_rev1_golf_player_ppc_access_atlas")
        self.assertEqual(set(result["source_ranges"]), set(UNITS))
        self.assertFalse(result["confirmed_power_address"])
        self.assertFalse(result["confirmed_club_pose_address"])
        self.assertFalse(result["revision_verified_from_dol_alone"])
        objects = result["object_access_patterns"]
        patterns = {(r["source_unit"], r["base_register"],
                     r["relative_displacement"], r["access_kind"])
                    for r in objects}
        self.assertIn(("RPGolMain", "r3", "+0x074", "load"), patterns)
        self.assertIn(("RPGolMain", "r3", "+0x074", "store"), patterns)
        self.assertIn(("RPGolMain", "r31", "+0x058", "load"), patterns)
        self.assertIn(("RPGolPlayer", "r30", "+0x01C", "store"), patterns)
        self.assertIn(("RPGolPlayerManager", "r3", "+0x09C", "load"), patterns)
        self.assertNotIn(("RPGolMain", "r1", "+0x074", "store"), patterns)
        self.assertEqual(result["r13_static_pattern_count"], 1)
        self.assertEqual(result["r13_static_patterns"][0]["r13_signed_displacement"],
                         "-0x0020")
        edges = {(r["from_source_unit"], r["to_source_unit"]):
                 r["direct_bl_count"] for r in result["cross_source_direct_calls"]}
        self.assertEqual(edges[("RPGolMain", "RPGolPlayer")], 1)
        self.assertEqual(edges[("RPGolPlayer", "RPGolPlayerManager")], 1)
        text = json.dumps(result)
        self.assertNotIn("bytes_hex", text)
        self.assertNotIn("private_path", text)

    def test_non_branch_and_absolute_branch_are_distinct(self):
        start, _ = UNITS["RPGolMain"]
        target, _ = UNITS["RPGolPlayer"]
        self.assertEqual(_branch_target(bl(start, target), start), target)
        self.assertIsNone(_branch_target(0x4E800421, start))  # bctrl indirect
        self.assertIsNone(_branch_target(dform(32, 4, 3, 0), start))

    def test_reject_bad_header_or_short_sections(self):
        with self.assertRaises(ValueError):
            analyze(b"")
        # Well-sized but invalid header must not silently scan zero memory.
        with self.assertRaises(ValueError):
            analyze(bytes(0x1000))
        raw = bytearray(mock_dol())
        struct.pack_into(">I", raw, 0x90, 4)
        with self.assertRaises(ValueError):
            analyze(bytes(raw))

    def test_missing_absolute_player_power_claim(self):
        result = analyze(mock_dol())
        self.assertGreater(result["object_base_candidate_count"], 0)
        self.assertNotIn("RPGolPlayer* confirmed", json.dumps(result))
        self.assertFalse(result["confirmed_power_address"])


if __name__ == "__main__":
    unittest.main()
