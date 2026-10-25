"""In-memory synthetic guardrail tests; never runs an emulator."""
import unittest
from wii_ai_golf.research_power_identifiability import audit_power_identifiability
A = "a" * 64
B = "b" * 64

def trial(name="trial", *, speed=None, backswing=None, pose="back",
          green="no", contact="yes", power=75., distance=100.,
          bridge=A, trace=B, scene=None, exit_code=0):
    controller = {"trace_sha256": trace,
                  "a_lead_observed_frame_delta": 45,
                  "generated_trace_frames": 89, "motion_scale": 1.}
    if speed is not None:
        controller["speed_scale"] = speed
    if backswing is not None:
        controller["backswing_scale"] = backswing
    record = {
        "id": name, "kind": "v1", "schema": 1,
        "capture_status": "sanitized_human_annotation_only",
        "process_exit_code": exit_code, "bridge_sha256": bridge,
        "controller": controller, "human": {
            "initial_club_pose_human": pose, "contact_human": contact,
            "finished_on_green_human": green,
            "displayed_power_percent_human": power,
            "displayed_distance_human": distance,
            "displayed_unit_human": "ft"}}
    if scene is not None:
        record["scenario_id"] = scene
    return record

class CensoredPowerTest(unittest.TestCase):
    def test_three_separate_arms_not_a_response_curve(self):
        r = audit_power_identifiability([
            trial("a", speed=.8), trial("b", speed=.9),
            trial("c", speed=1., backswing=.8)])
        self.assertEqual(len(r["arms"]), 3)
        self.assertEqual(r["counts"]["eligible_human_trials"], 3)
        self.assertEqual(sum(a["off_green_displayed_100ft_count"]
                             for a in r["arms"]), 3)
        self.assertEqual(r["observed_distinct_human_power_estimates"], [75.])
        self.assertFalse(r["gates"]["power_model_identifiable"])
        self.assertEqual(r["same_scene_cross_arm_comparison_count"], 0)

    def test_unknown_parameter_is_not_imputed_baseline(self):
        r = audit_power_identifiability([
            trial("a"), trial("b", speed=1., backswing=1.)])
        self.assertEqual(len(r["arms"]), 2)
        self.assertIn("some_motion_parameters_not_published", r["stop_reasons"])

    def test_explicit_matched_scene_is_not_verified_physics(self):
        r = audit_power_identifiability([
            trial("a", speed=.8, backswing=1., scene="tee1"),
            trial("b", speed=1., backswing=1., scene="tee1", power=55.)])
        self.assertEqual(r["same_scene_cross_arm_comparison_count"], 1)
        self.assertTrue(r["gates"]["same_scene_cross_arm_comparison_available"])
        self.assertFalse(r["gates"]["power_model_identifiable"])

    def test_green_human_score_not_carry_distance(self):
        r = audit_power_identifiability([trial("a", green="yes", distance=2.1)])
        self.assertEqual(r["arms"][0]["other_human_displayed_score_count"], 1)
        self.assertFalse(r["gates"]["continuous_ball_carry_measurements_available"])

    def test_dedup_and_failure_provenance(self):
        good = trial("good")
        r = audit_power_identifiability([
            good, good, {"kind": "test"}, trial("failed", exit_code=1)])
        self.assertEqual(r["counts"]["eligible_human_trials"], 1)
        self.assertEqual(r["counts"]["duplicate_ids"], 1)
        self.assertEqual(r["counts"]["non_v1_ignored"], 1)
        self.assertEqual(r["counts"]["noncomparable_v1"], 1)

    def test_negative_contact_and_missing_power_kept(self):
        r = audit_power_identifiability([
            trial("a", contact="no", power=None, distance=None)])
        self.assertEqual(r["arms"][0]["human_contact"]["no"], 1)
        self.assertEqual(r["arms"][0]["missing_power_estimate_count"], 1)
        self.assertIn("some_power_gauge_estimates_missing", r["stop_reasons"])

    def test_malformed_sha_and_private_field_not_emitted(self):
        bad = trial("bad", bridge="not-a-sha")
        bad["private_blob"] = "SECRET_BYTES"
        good = trial("good")
        good["local_path"] = "SECRET_FOLDER"
        import json
        r = audit_power_identifiability([bad, good])
        self.assertEqual(r["counts"]["invalid_v1"], 1)
        s = json.dumps(r)
        self.assertNotIn("SECRET_BYTES", s)
        self.assertNotIn("SECRET_FOLDER", s)

    def test_different_scene_bridge_never_pool(self):
        r = audit_power_identifiability([
            trial("a", speed=.8, backswing=1., scene="tee1"),
            trial("b", speed=1., backswing=1., scene="tee2"),
            trial("c", speed=1., backswing=1., scene="tee1", bridge="c" * 64)])
        self.assertEqual(r["same_scene_cross_arm_comparison_count"], 0)

    def test_bool_nan_power_are_not_measurements(self):
        r = audit_power_identifiability([
            trial("a", power=True), trial("b", power=float("nan"))])
        self.assertEqual(r["observed_distinct_human_power_estimates"], [])
        self.assertEqual(sum(a["missing_power_estimate_count"] for a in r["arms"]), 2)

    def test_empty_input_stop(self):
        r = audit_power_identifiability([])
        self.assertIn("no_comparable_human_labeled_v1_trials", r["stop_reasons"])

if __name__ == "__main__":
    unittest.main()
