"""Synthetic-only source-object phase JSON triage, no game RAM required."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/triage_private_object_windows_summary.py"
spec = importlib.util.spec_from_file_location("private_window_summary", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture():
    words = {}
    sizes = {**{f"ball_object_{i}": 0x1AC for i in range(4)},
             **{f"player_record_{i}": 0x0CC for i in range(4)},
             "selected_start": 0x50, "selected_pin": 0x50}
    for name, size in sizes.items():
        rows = [["0x00000000"] * (size // 4) for _ in range(4)]
        words[name] = {"guest_base_stable": True, "size_bytes": size,
                       "all_words_by_phase_hex": rows,
                       "guest_bases_by_phase_hex": ["0x91ABCDEF"] * 4}
    vec = {"word_u32_hex": ["0x3F800000", "0x00000000", "0x40000000"]}
    return {"kind": mod.GAME_KIND, "schema_version": 1,
            "game_id": "RSPE01", "revision": 1, "phase_names": list(mod.PHASES),
            "all_bank_pairs_distinct": True, "selected_slot_and_hole_stable": True,
            "windows": words,
            "vec3_by_phase": [
                {name: copy.deepcopy(vec) for name in mod.VECTOR_KEYS}
                for _ in range(4)],
            "private_raw_coordinate_marker": 9876.543}


class PrivateWindowTriageTests(unittest.TestCase):
    def test_static_ball_and_start_no_motion_claim(self):
        out = mod.safe_object_summary(fixture())
        self.assertEqual(out["source_selected_vector_component_changes"]["selected_ball"], [0,0,0])
        self.assertEqual(out["source_selected_vector_component_changes"]["selected_start"], [0,0,0])
        self.assertTrue(out["selected_ball_vs_start_same_words_in_all_phases"])
        self.assertFalse(out["physical_ball_movement_verified"])
        self.assertFalse(out["training_allowed"])
        self.assertNotIn("9876.543", json.dumps(out))
        self.assertNotIn("0x91ABCDEF", json.dumps(out))

    def test_different_aim_record_without_ball_changes(self):
        fake = fixture()
        fake["windows"]["player_record_0"]["all_words_by_phase_hex"][2][15] = "0x41200000"
        fake["windows"]["player_record_0"]["all_words_by_phase_hex"][3][15] = "0x41200000"
        out = mod.safe_object_summary(fake)
        self.assertEqual(out["player_record_window_word_changes"]["player_record_0"]["total_changed_words_by_transition"], [0,1,0])
        self.assertTrue(all(sum(x["total_changed_words_by_transition"]) == 0
                            for x in out["ball_object_window_changes_and_cache_components"].values()))
        self.assertFalse(out["physical_ball_movement_verified"])

    def test_cache_triplet_change_count_can_be_reported_without_xyz_claim(self):
        fake = fixture()
        words = fake["windows"]["ball_object_0"]["all_words_by_phase_hex"]
        words[2][0xF0 // 4] = "0x3F000000"
        words[3][0xF0 // 4] = "0x3F000000"
        out = mod.safe_object_summary(fake)
        self.assertEqual(out["ball_object_window_changes_and_cache_components"]["ball_object_0"]
                         ["triplet_component_changes_by_transition"]["conditional_cache_f0"], [0,1,0])
        self.assertFalse(out["physical_ball_movement_verified"])
        self.assertTrue(out["does_not_identify_selected_ball_object_slot"])

    def test_source_selected_vector_change_reported_cautiously(self):
        fake = fixture()
        for idx in (2,3):
            fake["vec3_by_phase"][idx]["selected_ball"]["word_u32_hex"][1] = "0x3F800000"
        out = mod.safe_object_summary(fake)
        self.assertEqual(out["source_selected_vector_component_changes"]["selected_ball"], [0,1,0])
        self.assertFalse(out["selected_ball_vs_start_same_words_in_all_phases"])
        self.assertFalse(out["vertical_velocity_verified"])

    def test_reject_moved_object(self):
        fake = fixture()
        fake["windows"]["ball_object_0"]["guest_base_stable"] = False
        with self.assertRaises(mod.InvalidStudy):
            mod.safe_object_summary(fake)

    def test_reject_invalid_game_revision(self):
        fake = fixture()
        fake["revision"] = 0
        with self.assertRaises(mod.InvalidStudy):
            mod.safe_object_summary(fake)

    def test_reject_corrupt_cache_word(self):
        fake = fixture()
        fake["windows"]["ball_object_0"]["all_words_by_phase_hex"][2][0xCC//4] = "not a word"
        with self.assertRaises(mod.InvalidStudy):
            mod.safe_object_summary(fake)

    def test_reject_short_ball_window(self):
        fake = fixture()
        fake["windows"]["ball_object_0"]["size_bytes"] = 0x0CC
        fake["windows"]["ball_object_0"]["all_words_by_phase_hex"] = [
            row[:0xCC//4] for row in fake["windows"]["ball_object_0"]["all_words_by_phase_hex"]]
        with self.assertRaises(mod.InvalidStudy):
            mod.safe_object_summary(fake)

    def test_reject_partial_pin_vector_phases(self):
        fake = fixture()
        fake["vec3_by_phase"][2].pop("selected_pin")
        with self.assertRaises(mod.InvalidStudy):
            mod.safe_object_summary(fake)

    def test_counts_correctly_deduplicate_reverted_and_persistent_change(self):
        x = [["0x00000001"],["0x00000002"],["0x00000003"],["0x00000003"]]
        self.assertEqual(mod.counts(x),[1,1,0])


if __name__ == "__main__":
    unittest.main()
