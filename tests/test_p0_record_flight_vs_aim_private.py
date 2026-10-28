"""Entirely synthetic tests of B0–B3 idle/WASD vs private airborne record mask."""
from __future__ import annotations
from copy import deepcopy
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
SCRIPT = HERE / "scripts" / "audit_p0_record_flight_vs_aim_private.py"
spec = importlib.util.spec_from_file_location("record_flight_mask", SCRIPT)
assert spec and spec.loader
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def sample(changed=None, ball=(1, 2, 3), start=(1, 2, 3)):
    record = [0] * 51
    for offset, value in (changed or {}).items():
        record[offset // 4] = value
    return {
        "selected_index": 0,
        "hole": 2,
        "whole_record": record,
        "triplets": {
            "ball_nested_plus_0x4c": tuple(ball),
            "source_current_start": tuple(start),
        },
        "ball_constructor_translation_selfref": True,
        "start_constructor_selfrefs": True,
    }


def cohort():
    return {
        "B0": sample(),
        "B1": sample({0x3C: 1}),
        "B2": sample({0x3C: 2, 0x40: 3}),
        "B3": sample({0x3C: 2, 0x40: 3}),
        "FLIGHT": sample({0x3C: 4, 0x90: 5}, ball=(4, 5, 6)),
    }


class FlightRecordMaskTests(unittest.TestCase):
    def test_real_question_aim_overlap_and_flight_only(self):
        r = audit.summarize(cohort())
        self.assertEqual(r["no_shot_any_changed_offsets"], ["+0x03C", "+0x040"])
        self.assertEqual(r["wasd_aim_B1_to_B2_changed_offsets"], ["+0x03C", "+0x040"])
        self.assertEqual(r["shared_airborne_and_no_shot_changed_offsets"], ["+0x03C"])
        self.assertEqual(r["airborne_only_relative_to_no_shot_offsets"], ["+0x090"])
        self.assertEqual(r["no_shot_only_relative_to_airborne_offsets"], ["+0x040"])
        self.assertEqual(r["airborne_vs_B0_changed_word_count"], 2)
        self.assertTrue(r["no_shot_ball_triplet_stable"])
        self.assertTrue(r["no_shot_start_triplet_stable"])
        self.assertEqual(r["source_ball_B0_vs_airborne_changed_components"], 3)

    def test_no_aim_diffs_but_changed_flight(self):
        p = cohort()
        for phase in ("B1", "B2", "B3"):
            p[phase] = deepcopy(p["B0"])
        r = audit.summarize(p)
        self.assertEqual(r["no_shot_any_changed_offsets"], [])
        self.assertEqual(r["airborne_only_relative_to_no_shot_count"], 2)

    def test_aim_only_but_no_flight(self):
        p = cohort()
        p["FLIGHT"] = deepcopy(p["B0"])
        r = audit.summarize(p)
        self.assertEqual(r["airborne_vs_B0_changed_word_count"], 0)
        self.assertEqual(r["no_shot_only_relative_to_airborne_offsets"], ["+0x03C", "+0x040"])

    def test_idle_flank_change_is_not_flight_only(self):
        p = cohort()
        p["B1"]["whole_record"][0x90 // 4] = 17
        r = audit.summarize(p)
        self.assertEqual(r["airborne_only_relative_to_no_shot_offsets"], [])
        self.assertIn("+0x090", r["idle_flank_changed_offsets"])

    def test_out_of_range_word_and_non_u32_rejected(self):
        for val in (-1, 2**32, 1.5, True, "10"):
            p = cohort()
            p["B2"]["whole_record"][30] = val
            with self.subTest(val=val), self.assertRaises(ValueError):
                audit.summarize(p)

    def test_missing_whole_word_rejected(self):
        p = cohort()
        p["FLIGHT"]["whole_record"].pop()
        with self.assertRaises(ValueError):
            audit.summarize(p)

    def test_selected_slot_and_hole_must_match(self):
        for key, val in [("selected_index", 1), ("hole", 3)]:
            p = cohort()
            p["FLIGHT"][key] = val
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "owner/hole"):
                audit.summarize(p)

    def test_constructor_guard_fails_closed(self):
        for key in ("ball_constructor_translation_selfref", "start_constructor_selfrefs"):
            p = cohort()
            p["FLIGHT"][key] = False
            with self.subTest(key=key), self.assertRaises(ValueError):
                audit.summarize(p)

    def test_no_shot_ball_movement_demotes_control(self):
        p = cohort()
        p["B2"]["triplets"]["ball_nested_plus_0x4c"] = (3, 2, 1)
        r = audit.summarize(p)
        self.assertFalse(r["no_shot_ball_triplet_stable"])
        self.assertFalse(r["source_selected_ball_world_xyz_verified"])

    def test_source_start_difference_stays_confound(self):
        p = cohort()
        p["FLIGHT"]["triplets"]["source_current_start"] = (9, 9, 9)
        r = audit.summarize(p)
        self.assertEqual(r["source_start_B0_vs_airborne_changed_components"], 3)
        self.assertFalse(r["approved_for_training"])

    def test_output_does_not_include_private_words_or_addresses(self):
        text = str(audit.summarize(cohort()))
        self.assertNotIn("whole_record", text)
        self.assertNotIn("selected_index", text)
        self.assertNotIn("0x900", text)
        self.assertNotIn("(4, 5, 6)", text)
        self.assertIn("airborne_only_is_NOT_verified_physical_motion", text)

    def test_all_physics_and_publish_flags_remain_false(self):
        r = audit.summarize(cohort())
        for flag in ("same_guest_physics_frame_verified", "same_boot_verified",
                     "source_selected_ball_world_xyz_verified", "ball_velocity_verified",
                     "shot_power_verified", "approved_for_training",
                     "allowed_to_publish", "raw_private_data_uploaded",
                     "actual_human_contact_joined_to_frames",
                     "pin_control_checked_by_this_study"):
            with self.subTest(flag=flag):
                self.assertIs(r[flag], False)

    def test_missing_or_duplicate_phase_rejected(self):
        p = cohort()
        p["BAD"] = p.pop("FLIGHT")
        with self.assertRaises(ValueError):
            audit.summarize(p)

    def test_python_isolated_import_preflight(self):
        result = subprocess.run(
            [sys.executable, "-I", str(SCRIPT), "--help"], capture_output=True,
            text=True, cwd=str(HERE), timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--baseline", result.stdout)
        self.assertIn("--flight", result.stdout)


if __name__ == "__main__":
    unittest.main()
