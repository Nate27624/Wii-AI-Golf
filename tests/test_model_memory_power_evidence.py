"""S003 memory/power evidence tests: synthetic public summaries, no game access."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.memory_power_evidence import review_memory_power_evidence


def memory(run="memory-A", *, phase="club_motion", region="golf_config", offset="+0x9C"):
    return {
        "kind": "golf-memory-phase-differential",
        "study_id": "S002-GOLF-MEMORY-PHASES", "schema_version": 1,
        "id": run, "scope": "broad", "sample_count": 4,
        "changed_word_count": 1,
        "phase_sample_counts": {"idle": 2, phase: 2},
        "max_non_atomic_frame_span": 3,
        "human_observations": [{"stage": 1, "phase": phase,
                                "observation": "club_moved"}],
        "confirmed_power_address": False,
        "top_changed_relative_words": [{
            "region": region, "relative_offset": offset, "documented_role": "unknown",
            "within_phase_changes": 2, "at_phase_boundary_changes": 1,
            "pointer_like_changes": 0, "float_like_changes": 3}],
        "private_path": "/MUST/NOT/EMIT",
        "windows": {"address": "0xDEADBEEF", "bytes_hex": "AABBCCDD"},
    }


def swing():
    return {"schema": 1, "kind": "v1", "id": "swing-A",
            "scenario_id": "green-first", "bridge_sha256": "a" * 64,
            "process_exit_code": 0,
            "human": {"contact_human": "yes", "initial_club_pose_human": "back",
                      "displayed_distance_human": 100.0,
                      "shot_start_frame_before_controller_trace": 150},
            "controller": {"trace_sha256": "b" * 64,
                           "a_lead_observed_frame_delta": 45}}


def review(runs=None, shots=None, **kwargs):
    return review_memory_power_evidence([memory()] if runs is None else runs,
                                        [swing()] if shots is None else shots,
                                        **kwargs)


class MemoryPowerEvidenceTests(unittest.TestCase):
    def test_existing_memory_schema_cannot_match_power_by_time(self):
        result = review()
        self.assertEqual(result["valid_memory_summaries"], 1)
        self.assertEqual(result["linked_same_run_pairs"], 0)
        self.assertEqual(result["link_refusal_reasons"],
                         {"missing_explicit_same_run_link": 1})
        self.assertFalse(result["training_ready"])
        self.assertIsNone(result["predicted_swing_power"])
        self.assertEqual(result["candidate_relative_words"][0]["relative_offset"], "+0x9C")
        self.assertNotIn("DEADBEEF", str(result))
        self.assertNotIn("/MUST/", str(result))

    def test_linked_record_is_metadata_join_not_power_estimate(self):
        record = memory(phase="shot_attempt")
        record.update({"shot_start_frame_before_controller_trace": 150,
                       "capture_frame_min": 100, "capture_frame_max": 190,
                       "linked_swing_observation_id": "swing-A",
                       "scenario_id": "green-first",
                       "bridge_sha256": "a" * 64, "trace_sha256": "b" * 64,
                       "a_lead_observed_frame_delta": 45})
        result = review([record])
        self.assertEqual(result["linked_same_run_pairs"], 1)
        self.assertFalse(result["verified_swing_power_field"])
        self.assertFalse(result["per_offset_negative_control_discrimination_available"])
        self.assertTrue(result["next_research_action"].startswith("S002:"))

    def test_link_requires_same_shot_frame_coverage_not_just_id(self):
        r = memory(phase="shot_attempt")
        r.update({"linked_swing_observation_id": "swing-A",
                  "scenario_id": "green-first",
                  "bridge_sha256": "a" * 64, "trace_sha256": "b" * 64,
                  "a_lead_observed_frame_delta": 45,
                  "shot_start_frame_before_controller_trace": 150,
                  "capture_frame_min": 151, "capture_frame_max": 200})
        self.assertEqual(review([r])["link_refusal_reasons"],
                         {"no_proven_shot_frame_coverage": 1})

    def test_no_shot_stage_remains_unlinked_even_with_matching_frame(self):
        r = memory(phase="a_hold")
        r.update({"linked_swing_observation_id": "swing-A",
                  "scenario_id": "green-first",
                  "bridge_sha256": "a" * 64, "trace_sha256": "b" * 64,
                  "a_lead_observed_frame_delta": 45,
                  "shot_start_frame_before_controller_trace": 150,
                  "capture_frame_min": 100, "capture_frame_max": 190})
        self.assertEqual(review([r])["link_refusal_reasons"],
                         {"no_proven_shot_frame_coverage": 1})

    def test_scene_and_bridge_mismatch_prevent_join(self):
        a = memory("first")
        a.update({"linked_swing_observation_id": "swing-A", "scenario_id": "wrong",
                  "bridge_sha256": "a" * 64, "trace_sha256": "b" * 64,
                  "a_lead_observed_frame_delta": 45})
        b = copy.deepcopy(a)
        b["id"] = "second"
        b["scenario_id"] = "green-first"
        b["bridge_sha256"] = "c" * 64
        result = review([a, b])
        self.assertEqual(result["linked_same_run_pairs"], 0)
        self.assertEqual(result["link_refusal_reasons"], {
            "bridge_or_trace_mismatch": 1,
            "missing_or_different_verified_scene_id": 1})

    def test_repeated_offsets_count_distinct_runs(self):
        result = review([memory("first"), memory("second")])
        candidate = result["candidate_relative_words"][0]
        self.assertEqual(candidate["independent_capture_runs"], 2)
        self.assertEqual(candidate["within_phase_changes"], 4)
        self.assertFalse(candidate["verified_power_signal"])

    def test_duplicated_run_id_invalidates_both_not_pick_best(self):
        result = review([memory(), memory()])
        self.assertEqual(result["valid_memory_summaries"], 0)
        self.assertEqual(result["memory_rejection_reasons"]["duplicate_memory_id"], 2)

    def test_invalid_offsets_and_counts_rejected(self):
        bad = memory()
        bad["top_changed_relative_words"][0]["relative_offset"] = "+0x9D"
        result = review([bad])
        self.assertEqual(result["valid_memory_summaries"], 0)
        self.assertEqual(result["memory_rejection_reasons"],
                         {"unaligned_out_of_bounds_or_duplicate_offset": 1})
        bad2 = memory("new")
        bad2["top_changed_relative_words"][0]["within_phase_changes"] = 999
        self.assertEqual(review([bad2])["valid_memory_summaries"], 0)

    def test_minimap_region_is_rendering_negative_control_not_ball(self):
        result = review([memory(region="minimap_ball_effect", offset="+0x1EC")])
        candidate = result["candidate_relative_words"][0]
        self.assertEqual(candidate["candidate_class"],
                         "minimap_rendering_negative_control")
        self.assertFalse(result["verified_golfer_state_field"])

    def test_no_memory_prioritizes_offline_data_before_new_swing(self):
        result = review([])
        self.assertEqual(result["linked_same_run_pairs"], 0)
        self.assertIn("offline", result["next_research_action"])

    def test_reject_false_verified_power_claim(self):
        r = memory()
        r["confirmed_power_address"] = True
        result = review([r])
        self.assertEqual(result["memory_rejection_reasons"],
                         {"untrusted_power_address_claim": 1})
        self.assertFalse(result["training_ready"])

    def test_source_error_and_non_atomic_span(self):
        a = memory("a")
        a["max_non_atomic_frame_span"] = 9
        b = memory("b")
        b["phase_sample_counts"] = {"idle": 2, "club_motion": 1}
        result = review([a, b], max_frame_span_for_timing=5)
        self.assertEqual(result["non_atomic_timing_unreliable_runs"], 1)
        self.assertEqual(result["memory_rejection_reasons"], {"invalid_phase_counts": 1})

    def test_duplicate_swing_ids_refuse_join(self):
        r = memory()
        r.update({"linked_swing_observation_id": "swing-A",
                  "scenario_id": "green-first",
                  "bridge_sha256": "a" * 64, "trace_sha256": "b" * 64,
                  "a_lead_observed_frame_delta": 45})
        result = review([r], [swing(), swing()])
        self.assertEqual(result["linked_same_run_pairs"], 0)
        self.assertEqual(result["link_refusal_reasons"],
                         {"linked_swing_not_found_or_ambiguous": 1})

    def test_bounds_block_unbounded_untrusted_payload(self):
        with self.assertRaises(ValueError):
            review([memory()] * 4, max_records=3)
        invalid = memory()
        invalid["top_changed_relative_words"][0]["region"] = ["evil"]
        self.assertEqual(review([invalid])["valid_memory_summaries"], 0)


if __name__ == "__main__":
    unittest.main()
