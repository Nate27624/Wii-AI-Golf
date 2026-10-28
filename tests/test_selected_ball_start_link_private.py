"""Synthetic selected-record→ball-related VEC3→start link, no private RAM."""
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
import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_start_link_private as link
from test_golf_two_bank_roster_private import synthetic, source_flow_fixture


def fixture(*, start_equals_ball=True, start_selfref=True):
    words, refs = synthetic()
    source_flow_fixture(words)
    pm = refs["pm"]
    words[refs["config"] + 0x98] = 1
    field = words[roster.GOLF_FIELD_STATIC]
    start = 0x91040000
    start_vec = start + 0x30
    words[field + 0x50] = start
    words[start + 0x48] = start + 0x0C if start_selfref else 0
    words[start + 0x4C] = start_vec
    current_record = pm + 4
    selected_ball = words[current_record + 0x88]
    ball_vec = words[selected_ball + 0x4C]
    for i in range(3):
        words[start_vec + 4*i] = (
            words[ball_vec + 4*i] if start_equals_ball else 0x40A00000 + i
        )
    # The mock's source code windows always include complete bounded opcodes
    # from the existing S002 #160 synthetic witness.
    return words, refs


def inspect(words, *, header=b"RSPE01\x00\x01"):
    def rd(addr):
        if (roster.PLAYER_MANAGER_CODE[0] <= addr < roster.PLAYER_MANAGER_CODE[1]
                or 0x8029E62C <= addr < 0x802A2210):
            return words.get(addr, 0)
        if addr not in words:
            raise ValueError("Synthetic undefined mapped word")
        return words[addr]
    return link.analyze_one(rd, header)


class SelectedBallStartLinkTests(unittest.TestCase):
    def test_three_way_equality_and_source_gates(self):
        words, _ = fixture()
        public, private = inspect(words)
        self.assertEqual(public["selected_record_relative_index_candidate"], 0)
        self.assertEqual(public["selected_record_vs_nested_ball_component_equal_count"], 3)
        self.assertEqual(public["selected_record_vs_current_start_component_equal_count"], 3)
        self.assertEqual(public["selected_nested_ball_vs_current_start_component_equal_count"], 3)
        self.assertTrue(public["all_three_candidate_triplets_bitwise_equal"])
        self.assertTrue(public["source_current_start_constructor_selfrefs_match"])
        self.assertTrue(public["selected_ball_translation_pointer_is_mem2"])
        self.assertTrue(public["record_candidate_triplet_finite_bounded"])
        self.assertTrue(public["nested_ball_candidate_triplet_finite_bounded"])
        self.assertTrue(public["source_current_start_triplet_finite_bounded"])
        self.assertFalse(public["source_candidate_is_dynamic_ball_world_xyz_verified"])
        self.assertEqual(private["record"], private["ball"])
        self.assertEqual(private["start"], private["ball"])

    def test_start_mismatch_does_not_claim_ball_movement(self):
        words, _ = fixture(start_equals_ball=False)
        public, _ = inspect(words)
        self.assertEqual(public["selected_record_vs_nested_ball_component_equal_count"], 3)
        self.assertEqual(public["selected_record_vs_current_start_component_equal_count"], 0)
        self.assertEqual(public["selected_nested_ball_vs_current_start_component_equal_count"], 0)
        self.assertFalse(public["all_three_candidate_triplets_bitwise_equal"])
        self.assertFalse(public["source_candidate_is_dynamic_ball_world_xyz_verified"])

    def test_start_constructor_mismatch_is_reported_not_promoted(self):
        words, _ = fixture(start_selfref=False)
        public, _ = inspect(words)
        self.assertFalse(public["source_current_start_constructor_selfrefs_match"])
        self.assertEqual(public["selected_record_vs_current_start_component_equal_count"], 3)
        self.assertFalse(public["source_candidate_is_dynamic_ball_world_xyz_verified"])

    def test_missing_selected_index_fails_closed(self):
        words, refs = fixture()
        words[refs["pm"] + 0x334] = 0x90009990
        with self.assertRaises(ValueError):
            inspect(words)

    def test_selected_ball_bad_data_interval_fails_closed(self):
        words, refs = fixture()
        ball = words[refs["pm"] + roster.BALL_CANDIDATE_MEMBER]
        words[ball] = roster.PLAYER_DATA[0]
        with self.assertRaises(ValueError):
            inspect(words)

    def test_ball_translation_pointer_unmapped_fails_closed(self):
        words, refs = fixture()
        ball = words[refs["pm"] + roster.BALL_CANDIDATE_MEMBER]
        words[ball + 0x4C] = 0xDEADBEEF
        with self.assertRaises(ValueError):
            inspect(words)

    def test_source_code_corruption_blocks_selected_link(self):
        words, _ = fixture()
        words[0x802A31F8] = 0
        with self.assertRaises(ValueError):
            inspect(words)

    def test_wrong_game_revision_mode_and_hole_block(self):
        words, _ = fixture()
        with self.assertRaises(ValueError):
            inspect(words, header=b"RSPE01\x00\x00")
        words, refs = fixture()
        words[refs["config"] + 0x94] = 3
        with self.assertRaises(ValueError):
            inspect(words)
        words, refs = fixture()
        words[refs["config"] + 0x98] = 99
        with self.assertRaises(ValueError):
            inspect(words)

    def test_summary_redacts_private_words_and_never_claims_motion(self):
        public, private = inspect(fixture()[0])
        summary = link.summarize_two_pairs([(public, private)])
        text = json.dumps(summary, sort_keys=True)
        for forbidden in ("0x910", "bytes_hex", "private_dir", "runtime_pointer",
                          '"record":', '"ball":', "file_path"):
            self.assertNotIn(forbidden, text)
        for key in ("ball_world_xyz_verified", "visual_ball_motion_verified",
                    "approved_for_model_training", "different_boots_or_phases_proven"):
            self.assertFalse(summary[key])
        self.assertFalse(summary["allowed_to_publish"])

    def test_two_pairs_identical_content_is_not_independent_physics(self):
        a = inspect(fixture()[0])
        b = inspect(fixture()[0])
        result = link.summarize_two_pairs([a, b], same_mem1=True, same_mem2=True)
        self.assertTrue(result["between_pairs"]["both_banks_bitwise_identical"])
        self.assertTrue(result["between_pairs"]["ball_related_triplet_words_equal"])
        self.assertFalse(result["between_pairs"]["triplet_difference_is_ball_motion_verified"])
        self.assertFalse(result["different_boots_or_phases_proven"])

    def test_two_pairs_distinct_ball_words_are_not_verified_motion(self):
        first = inspect(fixture()[0])
        other, refs = fixture()
        ball = other[refs["pm"] + roster.BALL_CANDIDATE_MEMBER]
        vec = other[ball + 0x4C]
        other[vec] = 0x40C00000
        second = inspect(other)
        result = link.summarize_two_pairs([first, second], same_mem1=True, same_mem2=False)
        self.assertFalse(result["between_pairs"]["ball_related_triplet_words_equal"])
        self.assertTrue(result["between_pairs"]["raw_hole_index_candidates_equal"])
        self.assertFalse(result["visual_ball_motion_verified"])
        self.assertFalse(result["ball_world_xyz_verified"])

    def test_source_pair_duplicate_comparisons_must_be_real_booleans(self):
        a = inspect(fixture()[0])
        with self.assertRaises(ValueError):
            link.summarize_two_pairs([a, a])
        with self.assertRaises(ValueError):
            link.summarize_two_pairs([])
        with self.assertRaises(ValueError):
            link.summarize_two_pairs([a] * 3)

    def test_cli_missing_pair_never_prints_private_paths(self):
        stderr = StringIO()
        with redirect_stderr(stderr):
            self.assertEqual(link.main(["--first-dir", "DO-NOT-REVEAL"]), 1)
        self.assertNotIn("DO-NOT-REVEAL", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
