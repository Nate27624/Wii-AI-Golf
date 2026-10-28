"""Entirely synthetic source-literal PPC aim-offset scan tests."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_golf_aim_ppc_offsets_private as scan


def dform(op, reg, base, disp):
    return (op << 26) | (reg << 21) | (base << 16) | (disp & 0xFFFF)


class AimPPCSourceTests(unittest.TestCase):
    def test_float_store_and_load_targets_exact(self):
        pc = scan.PLAYER_CODE_START
        hit = scan.decode_dform(dform(52, 7, 29, 0x3C), pc)
        self.assertEqual(hit["relative_displacement_hex"], "+0x03C")
        self.assertEqual(hit["mnemonic"], "stfs")
        self.assertEqual(hit["base_reg"], "r29")
        self.assertEqual(hit["source_or_destination_reg"], "f7")
        self.assertFalse(hit["selected_player_record_receiver_proven"])
        hit = scan.decode_dform(dform(48, 2, 3, 0xA0), pc)
        self.assertEqual(hit["mnemonic"], "lfs")
        self.assertEqual(hit["access_kind"], "read")
        self.assertEqual(hit["source_or_destination_reg"], "f2")

    def test_written_offset_counts_with_source_bounded_pc(self):
        base = scan.PLAYER_CODE_START
        words = {
            base: dform(52, 1, 29, 0x3C),
            base+4: dform(52, 2, 29, 0x40),
            base+8: dform(48, 3, 30, 0xA4),
            base+12: dform(36, 0, 29, 0x90),
            base+16: dform(52, 6, 29, 0x10),
        }
        result = scan.scan(lambda pc: words.get(pc, 0), start=base, end=base+20)
        self.assertEqual(result["instruction_count_examined"], 5)
        self.assertEqual(len(result["matched_dform_instructions"]), 4)
        self.assertEqual(result["target_offset_reads_writes"]["+0x03C"]["writes"], 1)
        self.assertEqual(result["target_offset_reads_writes"]["+0x0A4"]["reads"], 1)
        self.assertEqual(result["target_offset_reads_writes"]["+0x090"]["writes"], 1)
        self.assertFalse(result["gameplay_aim_angle_verified"])
        self.assertFalse(result["model_training_approved"])

    def test_nonliteral_and_wrong_opcode_not_reported(self):
        pc = scan.PLAYER_CODE_START
        self.assertIsNone(scan.decode_dform(dform(52, 1, 29, 0x74), pc))
        self.assertIsNone(scan.decode_dform(dform(14, 1, 29, 0x40), pc))
        self.assertIsNone(scan.decode_dform(dform(52, 1, 29, -4), pc))
        self.assertIsNone(scan.decode_dform(0, pc))

    def test_target_displacements_are_unique_source_offsets(self):
        self.assertEqual(len(set(scan.TARGETS)), len(scan.TARGETS))
        self.assertTrue(all(0 <= offset < 0xCC for offset in scan.TARGETS))

    def test_refuses_out_of_code_and_invalid_alignment(self):
        with self.assertRaises(ValueError):
            scan.scan(lambda pc: 0, start=scan.PLAYER_CODE_START-4,
                      end=scan.PLAYER_CODE_START+4)
        with self.assertRaises(ValueError):
            scan.scan(lambda pc: 0, start=scan.PLAYER_CODE_START,
                      end=scan.PLAYER_CODE_END+4)
        with self.assertRaises(ValueError):
            scan.decode_dform(dform(52, 0, 3, 0x40), 3)

    def test_refuses_invalid_ppc_words(self):
        for word in (-1, 2**32, None, "0"):
            with self.subTest(word=word), self.assertRaises(ValueError):
                scan.decode_dform(word, scan.PLAYER_CODE_START)


if __name__ == "__main__":
    unittest.main()
