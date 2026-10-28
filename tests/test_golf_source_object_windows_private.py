"""Offline fixtures for expanded B0..B3 gameplay-object window analysis."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import audit_golf_two_bank_roster_private as roster
import audit_golf_source_object_windows_private as expanded
from test_selected_ball_start_link_private import fixture


def synthetic_observation():
    data, refs = fixture()
    # Original #160 synthetic fixture uses 0x100-spaced ball references and
    # separate synthetic vec destinations. For bounded source object windows,
    # instantiate the source-backed 0x1AC ball layout without overlap and
    # give each base constructor its +0x4C -> +0x30 self reference.
    pm = refs["pm"]
    for i in range(roster.ROSTER_SLOTS):
        record = pm + 4 + i * roster.ROSTER_STRIDE
        old_ball = data[record + 0x88]
        old_vec = data[old_ball + 0x4C]
        ball = 0x91010000 + i * 0x200
        data[record + 0x88] = ball
        data[ball] = data[old_ball]
        data[ball + 0x4C] = ball + 0x30
        for j in range(3):
            data[ball + 0x30 + 4*j] = data[old_vec + 4*j]
    return expanded.sample_one(lambda address: data.get(address, 0),
                               b"RSPE01\x00\x01"), data, refs


class ExpandedSourceWindowTests(unittest.TestCase):
    def test_source_gated_object_windows_and_vec3(self):
        obs, _, _ = synthetic_observation()
        self.assertEqual(obs["selected_slot_index"], 0)
        for name in ("scene", "main", "config", "field",
                     "selected_start", "wind_direction_table",
                     "wind_speed_table", "player_record_0",
                     "player_record_3", "ball_object_0", "ball_object_3"):
            self.assertIn(name, obs["windows"])
        self.assertEqual(len(obs["windows"]["player_record_0"]["word_u32_hex"]),
                         roster.ROSTER_STRIDE // 4)
        self.assertEqual(len(obs["windows"]["ball_object_0"]["word_u32_hex"]),
                         expanded.BALL_BYTES // 4)
        self.assertEqual(len(
            obs["source_linked_vec3_candidates"]["selected_ball"]["be_f32"]), 3)
        self.assertFalse(obs["ball_motion_verified"])

    def test_changed_byte_offsets_and_actual_private_words(self):
        first, _, _ = synthetic_observation()
        phases = [copy.deepcopy(first) for _ in range(4)]
        phases[2]["windows"]["player_record_0"]["word_u32_hex"][9] = "0x00000001"
        phases[3]["windows"]["player_record_0"]["word_u32_hex"][9] = "0x00000001"
        console, private = expanded.combine(phases, distinct_banks=True)
        self.assertEqual(
            console["window_change_counts"]["player_record_0"]
            ["changed_u32_count_per_transition"], [0, 1, 0])
        self.assertEqual(
            private["windows"]["player_record_0"]["changed_byte_offsets_by_transition"],
            [[], ["+0x024"], []])
        self.assertEqual(private["windows"]["player_record_0"]
                         ["all_words_by_phase_hex"][2][9], "0x00000001")
        self.assertFalse(console["candidate_position_world_xyz_verified"])
        self.assertFalse(private["model_training_allowed"])
        self.assertFalse(private["automatic_publication_allowed"])

    def test_pointer_shift_keeps_data_but_rejects_unstable_comparison(self):
        first, _, _ = synthetic_observation()
        phases = [copy.deepcopy(first) for _ in range(4)]
        phases[2]["windows"]["main"]["guest_base_hex"] = "0x910A0000"
        console, private = expanded.combine(phases, distinct_banks=True)
        self.assertFalse(console["window_change_counts"]["main"]
                         ["object_address_stable"])
        self.assertEqual(console["window_change_counts"]["main"]
                         ["changed_u32_count_per_transition"], [None, None, None])
        self.assertEqual(private["windows"]["main"]
                         ["changed_byte_offsets_by_transition"], [None, None, None])

    def test_fail_malformed_disc_scene_and_selected_ball_link(self):
        source, _, _ = synthetic_observation()
        self.assertTrue(source["windows"])
        with self.assertRaises(ValueError):
            expanded.sample_one(lambda _address: 0, b"FAIL00\x00\x01")
        words, refs = fixture()
        selected_record = refs["pm"] + 4
        ball = words[selected_record + 0x88]
        words[ball + 0x4C] = 0xDEADBEEF
        with self.assertRaises(ValueError):
            expanded.sample_one(lambda address: words.get(address, 0),
                                b"RSPE01\x00\x01")

    def test_only_source_bounded_game_objects(self):
        with self.assertRaises(ValueError):
            expanded._gated_window(lambda _: 0, 0xA0000000, 16)
        with self.assertRaises(ValueError):
            expanded._gated_window(lambda _: 0, 0x90000000, 1 << 22)
        with self.assertRaises(ValueError):
            expanded._gated_window(lambda _: 0, 0x80000000, 12)

    def test_finite_vec3_decoding_and_nan_refusal(self):
        words = [0x3F800000, 0x40000000, 0x40400000]
        def read(addr):
            return words[(addr - 0x90000400) // 4]
        triple = expanded._vector(read, 0x90000400)
        self.assertEqual(triple["be_f32"], [1.0, 2.0, 3.0])
        self.assertFalse(triple["world_xyz_verified"])
        words[1] = 0x7FC00000
        with self.assertRaises(ValueError):
            expanded._vector(read, 0x90000400)

    def test_phase_set_mismatch_or_hole_switch_abstains(self):
        first, _, _ = synthetic_observation()
        phases = [copy.deepcopy(first) for _ in range(4)]
        phases[1]["raw_hole_index"] += 1
        with self.assertRaises(ValueError):
            expanded.combine(phases, distinct_banks=True)
        phases[1]["raw_hole_index"] -= 1
        phases[3]["windows"].pop("ball_object_2")
        with self.assertRaises(ValueError):
            expanded.combine(phases, distinct_banks=True)


if __name__ == "__main__":
    unittest.main()
