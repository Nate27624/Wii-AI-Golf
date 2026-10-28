"""Synthetic-only checks for private S002 player aim offset inspection."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import inspect_golf_aim_offsets_private as inspect


def fixture():
    words = ["0x00000000"] * (0xCC // 4)
    main = ["0x00000000"] * (0x80 // 4)
    return {
        "kind": "PRIVATE-golf-source-object-windows-four-phase",
        "game_id": "RSPE01",
        "revision": 1,
        "phase_names": list(inspect.PHASES),
        "selected_slot_and_hole_stable": True,
        "model_training_allowed": False,
        "windows": {
            "player_record_0": {
                "guest_base_stable": True,
                "size_bytes": 0xCC,
                "all_words_by_phase_hex": [words.copy() for _ in range(4)],
            },
            "main": {
                "guest_base_stable": True,
                "size_bytes": 0x80,
                "all_words_by_phase_hex": [main.copy() for _ in range(4)],
            },
        },
    }


class AimInspectionTests(unittest.TestCase):
    def test_unique_aim_offsets_are_marked_candidates_not_verified_physics(self):
        report = fixture()
        record = report["windows"]["player_record_0"]["all_words_by_phase_hex"]
        record[2][0x40 // 4] = "0x3F800000"
        record[3][0x40 // 4] = "0x3F800000"
        out = inspect.analyze(report)
        self.assertEqual(out["aim_changed_count"], 1)
        self.assertEqual(out["aim_only_count"], 1)
        row = out["selected_record_changed_offsets"][0]
        self.assertEqual(row["offset_hex"], "+0x040")
        self.assertEqual(row["class"], "aim-only candidate")
        self.assertEqual(row["b2_possible_f32"], "1")
        self.assertFalse(out["ball_motion_verified"])
        self.assertFalse(out["training_allowed"])
        self.assertIn("NOT proof", inspect.format_results(out))

    def test_idle_background_and_aim_confound(self):
        report = fixture()
        record = report["windows"]["player_record_0"]["all_words_by_phase_hex"]
        record[1][1] = "0x00000001"
        record[2][1] = "0x00000002"
        record[3][1] = "0x00000003"
        record[1][2] = "0x00000001"
        record[2][2] = "0x00000001"
        record[3][2] = "0x00000001"
        main = report["windows"]["main"]["all_words_by_phase_hex"]
        main[1][0x74 // 4] = "0x00000001"
        main[2][0x74 // 4] = "0x00000002"
        main[3][0x74 // 4] = "0x00000003"
        out = inspect.analyze(report)
        self.assertEqual(out["aim_changed_count"], 1)
        self.assertEqual(out["aim_only_count"], 0)
        self.assertEqual([r["class"] for r in out["selected_record_changed_offsets"]],
                         ["aim+idle confound", "idle/background"])
        self.assertEqual(out["main_changed_offsets"], ["+0x074"])

    def test_reject_unstable_objects_and_wrong_dimensions(self):
        report = fixture()
        report["windows"]["player_record_0"]["guest_base_stable"] = False
        with self.assertRaises(ValueError):
            inspect.analyze(report)
        report = fixture()
        report["windows"]["player_record_0"]["size_bytes"] = 0x80
        with self.assertRaises(ValueError):
            inspect.analyze(report)

    def test_reject_unapproved_schema_and_unstable_slot(self):
        for field, bad in (("kind", "synthetic"), ("game_id", "OTHER"),
                           ("revision", 0), ("selected_slot_and_hole_stable", False),
                           ("model_training_allowed", True)):
            report = fixture()
            report[field] = bad
            with self.subTest(field=field), self.assertRaises(ValueError):
                inspect.analyze(report)

    def test_reject_malformed_hex_and_nan_reports(self):
        report = fixture()
        report["windows"]["player_record_0"]["all_words_by_phase_hex"][1][0] = "0xNOPE"
        with self.assertRaises(ValueError):
            inspect.analyze(report)
        self.assertEqual(inspect._float_guess(0x7FC00000), "nonfinite")
        self.assertEqual(inspect._float_guess(0x90010000), "unlikely")

    def test_never_claims_contact_just_from_changed_offset(self):
        report = fixture()
        record = report["windows"]["player_record_0"]["all_words_by_phase_hex"]
        record[2][0x54 // 4] = "0x40000000"
        record[3][0x54 // 4] = "0x40000000"
        out = inspect.analyze(report)
        self.assertEqual(out["selected_record_changed_offsets"][0]["source_hint"],
                         "record translation copy component 0")
        self.assertFalse(out["ball_motion_verified"])
        self.assertFalse(out["training_allowed"])


if __name__ == "__main__":
    unittest.main()
