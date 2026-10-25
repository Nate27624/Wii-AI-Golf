"""Offline, provenance-conservative S003 analysis tests; no Dolphin imports."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.modeling.power_map_analysis import analyze_power_map

STUDY = "S003-POWER-MAP-10-V1"
BRIDGE = "f" * 64
PLAN = ((1.0, 1.0), (0.8, 1.0), (1.0, 1.2), (0.9, 1.0), (1.0, 0.8),
        (1.0, 1.0), (1.0, 0.8), (0.9, 1.0), (1.0, 1.2), (0.8, 1.0))


def trial(i, *, contact="yes", green="no", score=100.0):
    speed, back = PLAN[i - 1]
    return {"study_id": STUDY, "trial_index": i, "trial_count": 10,
            "schema": 1, "kind": "v1", "bridge_sha256": BRIDGE,
            "capture_status": "sanitized_human_annotation_only", "process_exit_code": 0,
            "requested_a_lead_frames": 45, "requested_motion_scale": 1.0,
            "requested_speed_scale": speed, "requested_backswing_scale": back,
            "controller": {"a_lead_observed_frame_delta": 45,
                           "generated_trace_frames": 89, "trace_sha256": "a" * 64,
                           "speed_scale": speed, "backswing_scale": back},
            "human": {"contact_human": contact, "finished_on_green_human": green,
                      "initial_club_pose_human": "back",
                      "displayed_distance_human": score,
                      "displayed_unit_human": "ft",
                      "displayed_power_percent_human": 75.0},
            "untrusted_extras": {"RAW-PRIVATE": "never echo me"}}


def review(rows):
    return analyze_power_map(rows, PLAN, study_id=STUDY, expected_bridge_sha256=BRIDGE)


class PowerMapAnalysisTests(unittest.TestCase):
    def test_off_green_penalty_is_not_carry(self):
        result = review([trial(1), trial(6)])
        control = result["conditions"][0]
        self.assertEqual(control["off_green_penalty_labels"], 2)
        self.assertEqual(control["human_on_green_displayed_ft_count"], 0)
        self.assertEqual(result["physical_carry_measurement_count"], 0)
        self.assertFalse(result["power_response_identified"])
        self.assertEqual(control["contact_wilson_95"]["n"], 2)
        self.assertLess(control["contact_wilson_95"]["lower"], 0.35)
        self.assertNotIn("never echo", str(result))

    def test_green_display_is_not_ball_flight(self):
        result = review([trial(1, green="yes", score=2.1)])
        control = result["conditions"][0]
        self.assertEqual(control["human_on_green_displayed_ft_count"], 1)
        self.assertEqual(control["off_green_penalty_labels"], 0)
        self.assertEqual(result["physical_carry_measurement_count"], 0)

    def test_unknown_label_never_counts_as_miss(self):
        result = review([trial(1, contact="unknown", green="unknown")])
        row = result["conditions"][0]
        self.assertEqual((row["contact_no"], row["contact_unknown"]), (0, 1))
        self.assertIsNone(row["contact_wilson_95"])

    def test_duplicate_index_excludes_all_versions(self):
        result = review([trial(1), trial(1, contact="no"), trial(2)])
        self.assertEqual(result["duplicate_indices"], [1])
        self.assertEqual(result["eligible_attempts"], 1)
        self.assertIn({"trial_index": 1, "reason": "duplicate_trial_index"},
                      result["excluded_trials"])

    def test_exclude_controller_pose_and_bridge_confounders(self):
        a = trial(1)
        a["human"]["initial_club_pose_human"] = "forward"
        b = trial(2)
        b["controller"]["speed_scale"] = 1.0
        c = trial(3)
        c["bridge_sha256"] = "a" * 64
        d = trial(4)
        d["process_exit_code"] = 1
        result = review([a, b, c, d])
        self.assertEqual(result["eligible_attempts"], 0)
        self.assertEqual({x["reason"] for x in result["excluded_trials"]},
                         {"initial_pose_not_comparable", "controller_requested_setting_conflict",
                          "unmatched_bridge_or_capture_provenance", "process_failed_outcome_unknown"})

    def test_reject_bad_scale_and_unobserved_a_lead(self):
        a = trial(1)
        a["requested_speed_scale"] = 0.9
        b = trial(2)
        b["controller"].pop("a_lead_observed_frame_delta")
        result = review([a, b])
        self.assertEqual(result["eligible_attempts"], 0)
        self.assertEqual(len(result["excluded_trials"]), 2)

    def test_strict_numeric_validity_and_plan(self):
        x = trial(1)
        x["human"]["displayed_power_percent_human"] = float("nan")
        x["human"]["displayed_distance_human"] = float("inf")
        result = review([x])
        row = result["conditions"][0]
        self.assertEqual(row["human_power_estimates_count"], 0)
        self.assertEqual(row["off_green_penalty_labels"], 0)
        with self.assertRaises(ValueError):
            analyze_power_map([], ((True, 1.0),), study_id=STUDY, expected_bridge_sha256=BRIDGE)

    def test_missing_and_nonmatching_study_records_are_visible(self):
        outside = trial(1)
        outside["study_id"] = "OTHER"
        result = review([trial(1), outside, {"study_id": STUDY, "trial_index": True}])
        self.assertEqual(result["ignored_other_study_records"], 1)
        self.assertEqual(result["unindexed_study_records"], 1)
        self.assertEqual(len(result["missing_indices"]), 9)
        self.assertFalse(result["exploratory_contact_comparison_ready"])


if __name__ == "__main__":
    unittest.main()
