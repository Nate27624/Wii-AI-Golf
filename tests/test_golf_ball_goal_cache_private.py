"""Entirely fabricated source words and MEM2 objects; NO game or ROM."""
from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import audit_golf_ball_goal_cache_private as c
import audit_golf_two_bank_roster_private as roster
from test_selected_ball_start_link_private import fixture
from test_golf_two_bank_roster_private import dform, mr, bl, bc


def b(pc, target):
    return (18 << 26) | ((target - pc) & 0x03FFFFFC)


def fabricate(*, target_count=0):
    words, refs = fixture()
    field = words[roster.GOLF_FIELD_STATIC]
    pm = refs["pm"]
    # Source Ball objects are 0x1AC bytes, never 0x100. The reused fixture
    # places synthetic objects 0x100 apart, so extending caches clobbers
    # the next fake object's first word unless disjoint full-size slots used.
    for slot in range(roster.ROSTER_SLOTS):
        record = pm + 4 + slot * roster.ROSTER_STRIDE
        old_ball = words[record + 0x88]
        new_ball = 0x91100000 + slot * 0x400
        words[record + 0x88] = new_ball
        words[new_ball] = words[old_ball]
        words[new_ball + 0x4C] = words[old_ball + 0x4C]
    pin = 0x91065000
    words[field + 0x30] = target_count
    words[field + 0x44] = pin
    words[pin + 0x4C] = pin + 0x30
    for i, v in enumerate((0x43300000, 0xC0200000, 0xC2D00000)):
        words[pin + 0x30 + 4*i] = v
    selected = pm + 4
    ball = words[selected + 0x88]
    current = words[ball + 0x4C]
    for base in c.CACHE_TRIPLES:
        for i in range(3):
            words[ball + base + i * 4] = words[current + i * 4]

    # Deliberately synthetic PPC WORD SHAPES, not original Wii code bytes.
    instructions = {
        0x80292294: dform(32, 0, 3, 0x30),
        0x80292298: dform(11, 0, 0, 0),
        0x8029229C: bc(0x8029229C, 0x802922A8),
        0x802922A0: dform(32, 3, 3, 0x34),
        0x802922A4: b(0x802922A4, 0x802B6F24),
        0x802922A8: dform(32, 3, 3, 0x44),
        0x802922AC: dform(32, 3, 3, 0x4C),
        0x80299C90: mr(27, 3),
        0x80299CD4: dform(32, 3, 3, 0x4C),
        0x80299CD8: dform(48, 0, 3, 0),
        0x80299CDC: dform(52, 0, 27, 0xCC),
        0x80299CE0: dform(48, 0, 3, 4),
        0x80299CE4: dform(52, 0, 27, 0xD0),
        0x80299CE8: dform(48, 0, 3, 8),
        0x80299CEC: dform(52, 0, 27, 0xD4),
        0x80299EE4: dform(32, 3, 13, -23320),
        0x80299EE8: bl(0x80299EE8, 0x80292294),
        0x80299EEC: dform(48, 4, 27, 0xD4),
        0x80299EF0: dform(48, 1, 3, 8),
        0x80299EF4: dform(48, 0, 27, 0xF8),
        0x80299EFC: dform(48, 3, 27, 0xCC),
        0x80299F04: dform(48, 2, 3, 0),
        0x80299F08: dform(48, 0, 27, 0xF0),
        0x80299F38: bc(0x80299F38, 0x80299F54),
        0x80299F44: dform(52, 3, 27, 0xF0),
        0x80299F48: dform(52, 0, 27, 0xF4),
        0x80299F4C: dform(52, 4, 27, 0xF8),
        0x80299F60: dform(48, 1, 27, 0xD0),
        0x80299F64: dform(48, 0, 27, 0x100),
        0x80299F6C: bc(0x80299F6C, 0x80299F90),
        0x80299F80: dform(52, 2, 27, 0xFC),
        0x80299F84: dform(52, 1, 27, 0x100),
        0x80299F88: dform(52, 0, 27, 0x104),
    }
    for pc in (0x80299EF8, 0x80299F00, 0x80299F0C, 0x80299F10,
               0x80299F18, 0x80299F1C, 0x80299F24, 0x80299F2C):
        instructions[pc] = 59 << 26
    words.update(instructions)
    return words, dict(refs, field=field, ball=ball, pin=pin), instructions


def read_words(words):
    def rd(addr):
        if (0x80290B44 <= addr < 0x80294184
                or 0x80296FD8 <= addr < 0x8029B240
                or roster.PLAYER_MANAGER_CODE[0] <= addr < roster.PLAYER_MANAGER_CODE[1]
                or 0x8029E62C <= addr < 0x802A2210):
            return words.get(addr, 0)
        return words[addr]
    return rd


def analyze(words):
    return c.analyze_one(read_words(words), b"RSPE01\x00\x01")


class BallGoalCacheSourceTests(unittest.TestCase):
    def test_source_getter_fallback_and_three_cache_init_equality(self):
        words, _, _ = fabricate()
        out = analyze(words)
        self.assertTrue(out["static_PPC_source_proofs"]
                        ["field_goal_getter_target_else_pin_source_supported"])
        self.assertTrue(out["field_goal_getter_uses_pin_branch_for_this_snapshot"])
        self.assertEqual(out["selected_ball_nested_current_vector_vs_start_equal_words"], 3)
        self.assertEqual(out["selected_cc_cache_vs_current_ball_equal_components"], 3)
        self.assertEqual(out["selected_f0_cache_vs_start_equal_components"], 3)
        self.assertEqual(out["selected_fc_cache_vs_start_equal_components"], 3)
        self.assertTrue(out["all_three_cache_triplets_equal_each_other"])
        self.assertFalse(out["source_cache_is_verified_closest_approach_or_score"])
        self.assertFalse(out["approved_for_training"])

    def test_nonzero_target_count_uses_other_getter_arm_not_pin(self):
        words, _, _ = fabricate(target_count=2)
        out = analyze(words)
        self.assertFalse(out["source_field_target_count_is_zero"])
        self.assertFalse(out["field_goal_getter_uses_pin_branch_for_this_snapshot"])
        self.assertTrue(out["static_PPC_source_proofs"]
                        ["field_goal_getter_target_else_pin_source_supported"])

    def test_getter_field_offset_mismatch_blocks(self):
        words, _, _ = fabricate()
        words[0x802922A8] = dform(32, 3, 3, 0x48)
        with self.assertRaises(ValueError):
            analyze(words)

    def test_target_selection_branch_mismatch_blocks(self):
        words, _, _ = fabricate()
        words[0x8029229C] = bc(0x8029229C, 0x802922AC)
        with self.assertRaises(ValueError):
            analyze(words)

    def test_dynamic_current_source_vector_offset_mismatch_blocks(self):
        words, _, _ = fabricate()
        words[0x80299CD4] = dform(32, 3, 3, 0x48)
        with self.assertRaises(ValueError):
            analyze(words)

    def test_conditional_f0_writer_changed_register_blocks(self):
        words, _, _ = fabricate()
        words[0x80299F44] = dform(52, 3, 30, 0xF0)
        with self.assertRaises(ValueError):
            analyze(words)

    def test_conditional_fc_writer_changed_offset_blocks(self):
        words, _, _ = fabricate()
        words[0x80299F88] = dform(52, 0, 27, 0x108)
        with self.assertRaises(ValueError):
            analyze(words)

    def test_wrong_goal_callsite_refuses(self):
        words, _, _ = fabricate()
        words[0x80299EE8] = bl(0x80299EE8, 0x802922EC)
        with self.assertRaises(ValueError):
            analyze(words)

    def test_wrong_planar_arithmetic_primary_opcode_refuses(self):
        words, _, _ = fabricate()
        words[0x80299F24] = 52 << 26
        with self.assertRaises(ValueError):
            analyze(words)

    def test_source_immutable_start_cache_mismatch_is_not_ball_motion(self):
        words, refs, _ = fabricate()
        words[refs["ball"] + 0xF0] += 1
        result = analyze(words)
        self.assertEqual(result["selected_f0_cache_vs_start_equal_components"], 2)
        self.assertFalse(result["all_three_cache_triplets_equal_each_other"])
        self.assertFalse(result["gameplay_ball_world_xyz_verified"])

    def test_bad_pin_constructor_selfptr_fails(self):
        words, refs, _ = fabricate()
        words[refs["pin"] + 0x4C] += 4
        with self.assertRaises(ValueError):
            analyze(words)

    def test_unmapped_ball_cache_or_nonfinite_refuses(self):
        words, refs, _ = fabricate()
        words[refs["ball"] + 0xF0] = 0x7FC00000  # fabricated NaN
        with self.assertRaises(ValueError):
            analyze(words)

    def test_wrong_disc_source_and_selector_fail_closed(self):
        words, refs, _ = fabricate()
        with self.assertRaises(ValueError):
            c.analyze_one(read_words(words), b"RSPE01\x00\x00")
        words[refs["pm"] + 0x334] = 0
        with self.assertRaises(ValueError):
            analyze(words)

    def test_report_is_counts_and_bool_only_no_raw_private_data(self):
        words, refs, _ = fabricate()
        result = analyze(words)
        body = json.dumps(result, sort_keys=True)
        for literal in ("0x910", "91065000", "43300000",
                        "private-dir", "ball_ptr", "raw_float",
                        "model_training_allowed"):
            self.assertNotIn(literal, body)
        for key in ("source_selected_goal_is_physically_verified_pin",
                    "source_cache_is_verified_closest_approach_or_score",
                    "gameplay_ball_world_xyz_verified",
                    "swing_contact_velocity_power_verified", "approved_for_training",
                    "allowed_to_publish"):
            self.assertFalse(result[key])

    def test_cli_bad_private_root_redacts_error(self):
        err = StringIO()
        with redirect_stderr(err):
            status = c.main(["--first-dir", "SECRET-PRIVATE-DIR"])
        self.assertEqual(status, 1)
        self.assertNotIn("SECRET-PRIVATE-DIR", err.getvalue())


if __name__ == "__main__":
    unittest.main()
