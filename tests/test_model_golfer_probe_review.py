"""Synthetic tests for S003 negative-control interpretation of S002 #129 output."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.modeling.golfer_probe_review import review_golfer_probe_summaries


def report(name="synthetic-a", *, changed=True):
    words = [{"offset": "+0x030", "within_stage_changes": 1,
              "between_stage_changes": 1, "plausible_float_changes": 2}]
    return {
        "schema_version": 1, "kind": "local-golfer-memory-audit",
        "id": name, "candidate_only": True,
        "source_claim": ("EGG::SceneManager +0xC scene, +0x18 scene ID; "
                         "RPSportsBaseScene +0x54 sport; RPGolScene +0x9C RPGolMain"),
        "game_id": "RSPE01", "revision": 1, "game_mode": 4,
        "global_pointer_candidates": 17, "matched_scene_chains": 1,
        "observed_creator_scene_id_matches_golf": True,
        "samples": 6, "max_non_atomic_frame_span": 4,
        "phase_sample_counts": {"idle": 4, "aim_only": 2},
        "changed_candidate_words": 1 if changed else 0,
        "top_relative_changes": words if changed else [],
        "raw_data": {"runtime_scene_address": "0x80040000",
                     "bytes_hex": "3f800000", "filesystem": "C:\\private"},
    }


class GolferProbeReviewTests(unittest.TestCase):
    def test_camera_change_not_treated_as_power(self):
        result = review_golfer_probe_summaries([report()])
        self.assertEqual(result["accepted_sanitized_candidate_reports"], 1)
        self.assertFalse(result["memory_power_model_ready"])
        self.assertIsNone(result["estimated_power_percent"])
        self.assertEqual(result["observed_real_swing_sample_count"], 0)
        self.assertEqual(result["candidate_offsets"][0]["candidate_class"],
                         "idle_or_camera_confounder_not_club_power")

    def test_private_values_are_not_reemitted(self):
        result = str(review_golfer_probe_summaries([report()]))
        for marker in ("80040000", "3f800000", "C:\\private", "bytes_hex"):
            self.assertNotIn(marker, result)

    def test_zero_changes_moves_to_pointer_member_discovery(self):
        out = review_golfer_probe_summaries([report(changed=False)])
        self.assertEqual(out["unchanged_candidate_window_reports"], 1)
        self.assertEqual(out["candidate_offsets"], [])
        self.assertIn("member pointers", out["next_action"])

    def test_wrong_scene_creator_must_reject_even_if_unique(self):
        candidate = report()
        candidate["observed_creator_scene_id_matches_golf"] = False
        out = review_golfer_probe_summaries([candidate])
        self.assertEqual(out["accepted_sanitized_candidate_reports"], 0)
        self.assertEqual(out["rejection_reasons"],
                         {"scene_chain_not_fully_gated": 1})

    def test_wrong_game_mode_and_disc_revision_rejected(self):
        a = report("bad-mode")
        a["game_mode"] = 9
        b = report("bad-revision")
        b["revision"] = 0
        out = review_golfer_probe_summaries([a, b])
        self.assertEqual(out["rejection_reasons"],
                         {"invalid_source_revision_or_mode": 2})

    def test_nonunique_probe_diagnostic_not_claimed_as_valid(self):
        out = review_golfer_probe_summaries([
            {"diagnostic": "no_unique_golfer_pointer_chain", "candidate_chains": 0},
            {"diagnostic": "no_unique_golfer_pointer_chain", "candidate_chains": 2},
        ])
        self.assertEqual(out["accepted_sanitized_candidate_reports"], 0)
        self.assertEqual(out["no_unique_chain_diagnostics"], {"ambiguous": 1, "zero": 1})
        self.assertIn("source-confirm", out["next_action"])

    def test_deduplicate_report_id_rejects_all_duplicates(self):
        out = review_golfer_probe_summaries([report(), report()])
        self.assertEqual(out["accepted_sanitized_candidate_reports"], 0)
        self.assertEqual(out["rejection_reasons"], {"duplicate_capture_id": 2})

    def test_invalid_relative_words_and_truncated_results_fail_closed(self):
        a = report("unaligned")
        a["top_relative_changes"][0]["offset"] = "+0x031"
        b = report("truncated")
        b["changed_candidate_words"] = 2
        c = report("oob")
        c["top_relative_changes"][0]["offset"] = "+0x100"
        out = review_golfer_probe_summaries([a, b, c])
        self.assertEqual(out["accepted_sanitized_candidate_reports"], 0)
        self.assertEqual(out["rejection_reasons"]["invalid_relative_word"], 2)
        self.assertEqual(out["rejection_reasons"]["truncated_or_invalid_change_rows"], 1)

    def test_bad_counts_do_not_invent_more_transitions_than_samples(self):
        rec = report()
        rec["top_relative_changes"][0]["within_stage_changes"] = 6
        out = review_golfer_probe_summaries([rec])
        self.assertEqual(out["rejection_reasons"], {"invalid_relative_change_counts": 1})

    def test_stage_coverage_needed(self):
        a = report()
        a["phase_sample_counts"] = {"idle": 6}
        out = review_golfer_probe_summaries([a])
        self.assertEqual(out["rejection_reasons"],
                         {"missing_or_invalid_idle_camera_controls": 1})

    def test_slow_snapshots_are_advisory_not_power(self):
        r = report()
        r["max_non_atomic_frame_span"] = 50
        out = review_golfer_probe_summaries([r])
        self.assertEqual(out["slow_frame_span_advisory_reports"], 1)
        self.assertFalse(out["verified_club_angle_signal"])

    def test_recurring_offset_counts_files_not_boots(self):
        out = review_golfer_probe_summaries([report("a"), report("b")])
        self.assertEqual(out["candidate_offsets"][0]["capture_files"], 2)
        self.assertEqual(out["candidate_offsets"][0]["within_stage"], 2)
        self.assertTrue(out["unverified_independent_boot_count"])

    def test_empty_input_and_limits(self):
        self.assertEqual(review_golfer_probe_summaries([])["input_reports"], 0)
        with self.assertRaises(ValueError):
            review_golfer_probe_summaries([report("a"), report("b")], max_reports=1)
        with self.assertRaises(ValueError):
            review_golfer_probe_summaries([], frame_span_advisory=-1)

    def test_invalid_python_data_is_not_injected_into_review(self):
        a = report()
        a["top_relative_changes"][0]["offset"] = ["evil", "0x8004"]
        out = review_golfer_probe_summaries([a])
        self.assertEqual(out["rejection_reasons"], {"invalid_relative_word": 1})

    def test_false_verified_field_cannot_be_promoted(self):
        a = report()
        a["power_verified"] = True  # malicious/unreviewed input claim
        out = review_golfer_probe_summaries([a])
        self.assertFalse(out["verified_game_power_signal"])
        self.assertFalse(out["memory_power_model_ready"])


if __name__ == "__main__":
    unittest.main()
