"""Synthetic fail-closed v2 S002 live-golfer summary triage for S003."""
from pathlib import Path
import sys
import unittest
from itertools import repeat

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.modeling.golfer_probe_review import review_golfer_probe_summaries


def report(run="test-a", *, changed=True, child=False):
    rows = ([{"region": "child_at_main+0x024" if child else "main",
              "offset": "+0x030", "within_stage_changes": 1,
              "between_stage_changes": 1, "plausible_float_changes": 2}]
            if changed else [])
    return {"schema_version": 2, "kind": "local-golfer-memory-audit",
            "id": run, "candidate_only": True,
            "source_claim": ("RPSysSceneMgr .sbss 0x804BF4D8..0x804BF4DF; "
                             "EGG::SceneManager +0xC/+0x18; "
                             "EGG::Scene +0x1C/+0x20; "
                             "RPSportsBaseScene +0x54; RPGolScene +0x9C"),
            "game_id": "RSPE01", "revision": 1, "game_mode": 4,
            "global_pointer_candidates": 1, "source_static_slot_count": 2,
            "census_frame_span": 2, "matched_scene_chains": 1,
            "actual_scene_id_verified": True, "manager_backlink_verified": True,
            "creator_scene_id_not_used_for_identity": True,
            "creator_scene_id_role": "previous_scene_not_current_scene_id",
            "samples": 6, "max_non_atomic_frame_span": 4,
            "phase_sample_counts": {"idle": 4, "aim_only": 2},
            "first_level_child_watch_count": 1 if child else 0,
            "first_level_child_watch_truncated": False,
            "first_level_child_batch_start": 0,
            "first_level_child_parent_offsets": ["+0x024"] if child else [],
            "changed_candidate_words": len(rows), "top_relative_changes": rows,
            "power_verified": False, "club_rotation_verified": False}


class CandidateReviewTests(unittest.TestCase):
    def test_v2_candidate_is_not_a_power_observation(self):
        result = review_golfer_probe_summaries([report()])
        self.assertEqual(result["accepted_candidate_reports"], 1)
        self.assertEqual(result["real_swing_observations"], 0)
        self.assertIsNone(result["estimated_power_percent"])
        self.assertFalse(result["confirmed_game_power"])
        self.assertFalse(result["ready_for_power_regression"])

    def test_previous_creator_scene_can_differ_from_current_golf(self):
        row = report()
        self.assertTrue(row["creator_scene_id_not_used_for_identity"])
        self.assertEqual(review_golfer_probe_summaries([row])["accepted_candidate_reports"], 1)

    def test_unique_chain_actual_scene_id_and_backlink_required(self):
        r = report("scene")
        r["actual_scene_id_verified"] = False
        n = report("backlink")
        n["manager_backlink_verified"] = False
        v = report("nonunique")
        v["matched_scene_chains"] = 2
        x = review_golfer_probe_summaries([r, n, v])
        self.assertEqual(x["accepted_candidate_reports"], 0)
        self.assertEqual(x["invalid_report_reasons"],
                         {"scene_source_or_backlink_not_verified": 3})

    def test_wrong_revision_or_mode_rejected(self):
        x, y = report("x"), report("y")
        x["revision"] = 0
        y["game_mode"] = 3
        a = review_golfer_probe_summaries([x, y])
        self.assertEqual(a["invalid_report_reasons"],
                         {"invalid_source_revision_or_mode": 2})

    def test_child_and_parent_same_offset_are_distinct(self):
        a, b = report("a"), report("b", child=True)
        x = review_golfer_probe_summaries([a, b])
        self.assertEqual(len(x["candidate_regions"]), 2)
        self.assertEqual(x["candidate_regions"][0]["relative_offset"], "+0x030")
        self.assertEqual(set(y["region"] for y in x["candidate_regions"]),
                         {"main", "child_at_main+0x024"})

    def test_child_offset_must_be_bounded_to_0x80(self):
        a = report(child=True)
        a["top_relative_changes"][0]["offset"] = "+0x080"
        z = review_golfer_probe_summaries([a])
        self.assertEqual(z["invalid_report_reasons"],
                         {"invalid_region_or_offset": 1})

    def test_child_parent_pointer_must_be_aligned(self):
        a = report(child=True)
        a["top_relative_changes"][0]["region"] = "child_at_main+0x025"
        z = review_golfer_probe_summaries([a])
        self.assertEqual(z["invalid_report_reasons"],
                         {"invalid_child_batch_provenance": 1})

    def test_missing_child_watch_makes_child_unverifiable(self):
        a = report(child=True)
        a["first_level_child_watch_count"] = 0
        self.assertEqual(review_golfer_probe_summaries([a])["accepted_candidate_reports"], 0)

    def test_privacy_first_rejects_raw_nested_artifacts(self):
        a = report("bad")
        a["runtime_golf_main_address"] = "0x80030000"
        b = report("bad2")
        b["top_relative_changes"][0]["bytes_hex"] = "deadbeef"
        result = review_golfer_probe_summaries([a, b])
        self.assertEqual(result["invalid_report_reasons"],
                         {"raw_or_private_input_rejected": 2})
        for marker in ("80030000", "deadbeef", "bytes_hex"):
            self.assertNotIn(marker, str(result))

    def test_unverified_no_unique_chain_diagnostics(self):
        result = review_golfer_probe_summaries([
            {"diagnostic": "no_unique_golfer_pointer_chain", "candidate_chains": 0},
            {"diagnostic": "no_unique_golfer_pointer_chain", "candidate_chains": 2}])
        self.assertEqual(result["nonunique_root_diagnostics"], {"zero": 1, "ambiguous": 1})
        self.assertEqual(result["accepted_candidate_reports"], 0)
        self.assertIn("singleton", result["next_action"])

    def test_zero_changes_only_means_this_window_was_static(self):
        result = review_golfer_probe_summaries([report(changed=False)])
        self.assertEqual(result["unchanged_candidate_reports"], 1)
        self.assertEqual(result["candidate_regions"], [])
        self.assertFalse(result["confirmed_club_position"])

    def test_slow_snapshot_keeps_advisory_and_no_power(self):
        a = report()
        a["max_non_atomic_frame_span"] = 20
        result = review_golfer_probe_summaries([a])
        self.assertEqual(result["slow_non_atomic_frame_reports"], 1)
        self.assertFalse(result["ready_for_power_regression"])

    def test_timing_counts_and_duplicate_ids(self):
        x=review_golfer_probe_summaries([report("same"), report("same")])
        self.assertEqual(x["invalid_report_reasons"], {"duplicate_capture_id": 2})
        bad=report("bad")
        bad["top_relative_changes"][0]["within_stage_changes"] = 20
        self.assertEqual(review_golfer_probe_summaries([bad])["accepted_candidate_reports"], 0)

    def test_outdated_version_one_is_not_mistaken_for_new_schema(self):
        a = report()
        a["schema_version"] = 1
        x = review_golfer_probe_summaries([a])
        self.assertEqual(x["invalid_report_reasons"],
                         {"invalid_identity_or_outdated_schema": 1})

    def test_no_phases_no_camera_contrast(self):
        a = report()
        a["phase_sample_counts"] = {"idle": 6}
        x = review_golfer_probe_summaries([a])
        self.assertEqual(x["invalid_report_reasons"],
                         {"missing_idle_or_camera_controls": 1})

    def test_actual_20_snapshot_shape_flags_all_four_as_continuous(self):
        # S002 first observed source-gated scene graph: 20 snapshots,
        # 17 within-stage + 2 boundary changes for all four candidate words.
        a = report("synthetic-live-20")
        a["samples"] = 20
        a["phase_sample_counts"] = {"idle": 12, "aim_only": 8}
        a["max_non_atomic_frame_span"] = 18
        a["first_level_child_watch_count"] = 3
        a["first_level_child_watch_truncated"] = True
        a["first_level_child_parent_offsets"] = [
            "+0x008", "+0x020", "+0x044"
        ]
        a["changed_candidate_words"] = 4
        a["top_relative_changes"] = [
            {"region": region, "offset": off, "within_stage_changes": 17,
             "between_stage_changes": 2, "plausible_float_changes": 0}
            for region, off in (
                ("main", "+0x074"), ("child_at_main+0x008", "+0x050"),
                ("child_at_main+0x020", "+0x038"),
                ("child_at_main+0x044", "+0x060"))
        ]
        review = review_golfer_probe_summaries([a])
        self.assertEqual(review["accepted_candidate_reports"], 1)
        self.assertEqual(review["continuous_change_candidates"], 4)
        self.assertEqual(review["slow_non_atomic_frame_reports"], 1)
        self.assertEqual(review["candidate_changes_truncated_reports"], 1)
        self.assertTrue(all(r["candidate_class"] ==
                            "continuous_idle_aim_clock_like_not_power"
                            for r in review["candidate_regions"]))
        self.assertFalse(review["confirmed_game_power"])

    def test_batch_provenance_must_list_each_child_region(self):
        a = report(child=True)
        a["first_level_child_parent_offsets"] = ["+0x030"]
        review = review_golfer_probe_summaries([a])
        self.assertEqual(review["accepted_candidate_reports"], 0)
        self.assertEqual(review["invalid_report_reasons"],
                         {"invalid_region_or_offset": 1})

    def test_missing_provenance_rejected(self):
        a = report(child=True)
        del a["creator_scene_id_not_used_for_identity"]
        b = report("batch", child=True)
        b["first_level_child_parent_offsets"] = ["+0x025"]
        result = review_golfer_probe_summaries([a, b])
        self.assertEqual(result["invalid_report_reasons"],
                         {"scene_source_or_backlink_not_verified": 1,
                          "invalid_child_batch_provenance": 1})

    def test_infinite_generator_is_bounded(self):
        with self.assertRaises(ValueError):
            review_golfer_probe_summaries(repeat(report()), max_reports=2)

    def test_truncated_child_watchlist_does_not_verify_power(self):
        a = report(child=True)
        a["first_level_child_watch_truncated"] = True
        x = review_golfer_probe_summaries([a])
        self.assertEqual(x["candidate_changes_truncated_reports"], 1)
        self.assertFalse(x["ready_for_power_regression"])


if __name__ == "__main__":
    unittest.main()
