"""Synthetic-only tests: never touch Dolphin, a game image or private RAM."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from audit_selected_player_state_word_private import (
    _SOURCE_WRITERS, source_state_writer_gate, summarize
)


def encode_dform(opcode, rt, ra, displacement):
    return ((opcode << 26) | (rt << 21) | (ra << 16)
            | (displacement & 0xFFFF))


def entries(states=(1, 1, 2, 2)):
    return [
        {"state": v, "slot": 0, "hole": 1, "record": 0x90010000,
         "source_gate": True}
        for v in states
    ]


class StateWordTests(unittest.TestCase):
    def test_source_five_literal_writer_gate_exact(self):
        words = {}
        for li, literal, stw, base in _SOURCE_WRITERS:
            words[li] = encode_dform(14, 0, 0, literal)
            words[stw] = encode_dform(36, 0, base, 0x24)
        self.assertTrue(source_state_writer_gate(words.__getitem__))
        words[_SOURCE_WRITERS[2][2]] ^= 1
        self.assertFalse(source_state_writer_gate(words.__getitem__))

    def test_no_shot_aim_word_can_change_without_contact_promotion(self):
        report = summarize(entries(), all_bank_pairs_changed=True)
        self.assertEqual(report["candidate_state_change_by_transition"],
                         [False, True, False])
        self.assertTrue(report["candidate_state_changed_during_aim_without_shot"])
        self.assertFalse(report["candidate_state_has_verified_gameplay_semantics"])
        self.assertFalse(report["active_ball_world_xyz_verified"])
        self.assertFalse(report["training_allowed"])
        self.assertFalse(report["allowed_to_publish"])

    def test_no_shot_stable_word_is_not_motion_proof(self):
        report = summarize(entries((3, 3, 3, 3)),
                           all_bank_pairs_changed=True)
        self.assertTrue(report["candidate_state_stable_all_four_no_shot_phases"])
        self.assertFalse(report["observed_contact_or_ball_motion"])

    def test_unknown_literal_reported_without_leak(self):
        report = summarize(entries((0, 0xAABBCCDD, 4, 99)),
                           all_bank_pairs_changed=True)
        self.assertEqual(
            report["candidate_state_in_five_source_literals_each_phase"],
            [False, False, True, False])
        rendered = str(report)
        self.assertNotIn("2864434397", rendered)
        self.assertNotIn("AABBCCDD", rendered)
        self.assertNotIn("0x90010000", rendered)
        self.assertFalse(report["candidate_state_exhaustive_enum_verified"])

    def test_reject_wrong_slot_record_hole(self):
        for field, value in (("slot", 1), ("record", 0x90050000),
                             ("hole", 2), ("source_gate", False)):
            e = entries()
            e[2][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                summarize(e, all_bank_pairs_changed=True)

    def test_reject_wrong_phase_count_and_bad_unsigned_word(self):
        with self.assertRaises(ValueError):
            summarize(entries()[:3], all_bank_pairs_changed=True)
        for value in (-1, 1 << 33, "4", True):
            e = entries()
            e[2]["state"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                summarize(e, all_bank_pairs_changed=True)

    def test_all_flags_conservative_even_when_changed(self):
        report = summarize(entries((1, 5, 3, 2)),
                           all_bank_pairs_changed=False)
        self.assertFalse(report["all_three_transitions_have_distinct_full_banks"])
        for key in ("same_boot_independently_proven",
                    "guest_frame_alignment_verified",
                    "power_verified", "velocity_verified", "training_allowed",
                    "allowed_to_publish"):
            self.assertFalse(report[key])


if __name__ == "__main__":
    unittest.main()
