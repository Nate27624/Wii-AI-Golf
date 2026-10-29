"""Synthetic, private-data-free cohort tests. Never starts Dolphin."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.audit.environment_cohort import summarize_environment_cohort


def report(hole=1, *, start_count=31, pin_count=6, arrows=True):
    ptrs = ("course", "cup", "map_data", "pin", "start", "wind_object")
    flags = ("green_slope_visible", "minimap_visible", "wind_arrow_visible")
    return {
        "kind": "local-golf-environment-source-candidates",
        "schema_version": 1, "sample_count": 8, "max_non_atomic_frame_span": 22,
        "source_candidate_game_mode": 4,
        "source_candidate_current_hole_raw": hole,
        "hole_value_changed_in_capture": False,
        "map_object_counts": {
            "pin_count": {"distinct_values": 1, "first_observed": pin_count},
            "start_count": {"distinct_values": 1, "first_observed": start_count},
        },
        "object_refs": {
            name: {"present_every_snapshot": True, "changed_during_capture": False}
            for name in ptrs
        },
        "visual_flags": {
            name: {"true_in_all_samples": name != "green_slope_visible" if arrows else False,
                   "changed_during_capture": False}
            for name in flags
        },
        "ball_xyz_verified": False, "pin_xyz_verified": False,
        "wind_speed_direction_verified": False,
    }


class EnvironmentCohortTests(unittest.TestCase):
    def test_two_file_aggregation_counts_and_absence_of_private_values(self):
        a, b = report(1), report(2, pin_count=5, start_count=30)
        b["object_refs"]["pin"]["changed_during_capture"] = True
        r = summarize_environment_cohort([a, b])
        self.assertEqual(r["capture_file_count"], 2)
        self.assertEqual(r["total_snapshot_count"], 16)
        self.assertEqual(r["candidate_hole_file_counts"], {"1": 1, "2": 1})
        self.assertEqual(r["pin_object_count_first_observed"]["distinct_file_values"], 2)
        self.assertEqual(r["reference_changed_within_capture_file_count"]["pin"], 1)
        self.assertEqual(r["max_non_atomic_frame_span"], 22)
        self.assertFalse(r["independent_sessions_verified"])
        self.assertFalse(r["ball_xyz_verified"])
        # Privacy check JSON structure and concrete leaked pointer patterns,
        # not harmless English in the fixed warning (e.g. "addresses").
        def check_public_shape(value):
            if isinstance(value, dict):
                for key, nested in value.items():
                    self.assertNotIn(key, {
                        "address", "bytes_hex", "raw_bytes", "local_path",
                        "runtime_address", "source_path", "file_name",
                    })
                    check_public_shape(nested)
            elif isinstance(value, list):
                for nested in value:
                    check_public_shape(nested)
        check_public_shape(r)
        output = json.dumps(r)
        self.assertNotRegex(output, r"0x[0-9a-fA-F]{8}\b")
        self.assertNotIn("bytes_hex", output)

    def test_same_hole_does_not_imply_independent_replication(self):
        r = summarize_environment_cohort([report(), report()])
        self.assertEqual(r["candidate_hole_file_counts"], {"1": 2})
        self.assertFalse(r["independent_sessions_verified"])

    def test_hole_changed_within_capture_not_attributed_to_single_value(self):
        x = report()
        x["source_candidate_current_hole_raw"] = None
        x["hole_value_changed_in_capture"] = True
        r = summarize_environment_cohort([report(), x])
        self.assertEqual(r["candidate_hole_file_counts"], {"1": 1})
        self.assertEqual(r["hole_changed_within_capture_file_count"], 1)

    def test_missing_provenance_or_false_power_claim_blocks(self):
        for key, value in (("kind", "untrusted"), ("source_candidate_game_mode", 3),
                           ("pin_xyz_verified", True), ("wind_speed_direction_verified", True)):
            x = report()
            x[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                summarize_environment_cohort([report(), x])

    def test_reject_inconsistent_or_malformed_holes(self):
        for hole, changed in ((1, True), (None, False), (999, False), (True, False)):
            x = report()
            x["source_candidate_current_hole_raw"] = hole
            x["hole_value_changed_in_capture"] = changed
            with self.subTest(hole=hole), self.assertRaises(ValueError):
                summarize_environment_cohort([report(), x])

    def test_reject_unbounded_or_invalid_report_shapes(self):
        with self.assertRaises(ValueError):
            summarize_environment_cohort([report()])
        with self.assertRaises(ValueError):
            summarize_environment_cohort([report()] * 65)
        for key, value in (("sample_count", True), ("sample_count", 0),
                           ("max_non_atomic_frame_span", -1),
                           ("max_non_atomic_frame_span", 300)):
            x = report()
            x[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                summarize_environment_cohort([report(), x])

    def test_reject_false_pointer_and_visual_statistics(self):
        x = report()
        x["object_refs"]["pin"]["present_every_snapshot"] = 1
        with self.assertRaises(ValueError):
            summarize_environment_cohort([report(), x])
        x = report()
        x["visual_flags"]["minimap_visible"]["changed_during_capture"] = "false"
        with self.assertRaises(ValueError):
            summarize_environment_cohort([report(), x])
        x = report()
        del x["object_refs"]["wind_object"]
        with self.assertRaises(ValueError):
            summarize_environment_cohort([report(), x])
        x = report()
        x["map_object_counts"]["pin_count"]["first_observed"] = True
        with self.assertRaises(ValueError):
            summarize_environment_cohort([report(), x])


if __name__ == "__main__":
    unittest.main()
