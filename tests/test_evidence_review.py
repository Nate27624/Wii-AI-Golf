"""Evidence-review gates: actual human labels are not scores or RPC-only hits."""
from __future__ import annotations
from datetime import datetime
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from wii_ai_golf.evidence_review import (
    load_public_observations, review_public_observations)
import research_cli


def record_v1(identifier: str, *, lead: int = 45, contact="yes",
              bridge="f" * 64, trace="b" * 64,
              distance=100.0) -> dict:
    return {
        "id": identifier, "kind": "v1", "schema": 1,
        "process_exit_code": 0, "verified_game_score": False,
        "capture_status": "sanitized_human_annotation_only",
        "bridge_sha256": bridge,
        "human": {
            "contact_human": contact,
            "initial_club_pose_human": "back",
            "displayed_distance_human": distance,
            "displayed_unit_human": "ft",
        },
        "controller": {"a_lead_observed_frame_delta": lead,
                       "trace_sha256": trace},
    }


class EvidenceReviewTests(unittest.TestCase):
    def test_actual_one_hit_45_frame_and_empty_zero_frame_are_not_a_comparison(self):
        a = record_v1("20261025T014552Z-db2d3d790b")
        b = {"id": "20261025T013459Z-b6de90e7b2", "kind": "v1",
             "process_exit_code": 0, "capture_status": "none_or_ambiguous",
             "requested_a_lead_frames": 0}
        review = review_public_observations([a, b])
        self.assertEqual(review["v1_incomplete_or_failed_runs"], 1)
        g = review["v1_by_bridge_trace_and_observed_a_lead"]
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0]["observed_a_lead_frames"], 45)
        self.assertEqual(g[0]["human_labeled_trials"], 1)
        self.assertEqual(g[0]["human_hit_yes"], 1)
        self.assertEqual(g[0]["human_distances"], [{"distance": 100.0, "unit": "ft"}])
        self.assertFalse(review["gates"]["three_matched_human_trials_any_v1_condition"])
        self.assertEqual(review["verified_game_scores"], 0)
        self.assertFalse(review["gates"]["controller_power_calibrated"])

    def test_minimap_one_idle_one_motion_does_not_verify_ball(self):
        idle = {"id": "20261025T014015Z-idle-automated-minimap",
                "kind": "automated-minimap-effect", "condition": "idle_control",
                "samples": 25, "adjacent_changes": 0, "changed_byte_offsets": []}
        swing = {"id": "20261025T014057Z-swing-automated-minimap",
                 "kind": "automated-minimap-effect", "condition": "swing",
                 "samples": 25, "adjacent_changes": 1,
                 "changed_byte_offsets": [123, 126, 127]}
        result = review_public_observations([idle, swing])
        self.assertEqual(result["minimap_by_condition"]["idle_control"]["with_no_adjacent_changes"], 1)
        self.assertEqual(result["minimap_by_condition"]["swing"]["changed_byte_offsets_union"],
                         [123, 126, 127])
        self.assertFalse(result["gates"]["three_independent_runs_each_minimap_condition"])
        self.assertFalse(result["gates"]["physics_ball_or_score_identity_verified"])
        self.assertIn("not", result["limitations"])

    def test_separates_bridge_trace_and_lead_provenance(self):
        first = record_v1("20261025T014552Z-db2d3d790b")
        second = record_v1("20261025T014553Z-bb2d3d790b", bridge="a" * 64)
        third = record_v1("20261025T014554Z-bb2d3d790b", lead=0, contact="no")
        result = review_public_observations([first, second, third])
        self.assertEqual(len(result["v1_by_bridge_trace_and_observed_a_lead"]), 3)
        self.assertFalse(result["gates"]["three_matched_human_trials_any_v1_condition"])

    def test_raw_or_untrusted_inputs_never_reach_output(self):
        secret = "RAW_PRIVATE_RAM_DO_NOT_EXPOSE"
        r = record_v1("20261025T014552Z-db2d3d790b", distance=float("nan"))
        r["raw_ram_hex"] = secret
        r["human"]["initial_club_pose_human"] = secret
        r["human"]["displayed_unit_human"] = secret
        r["human"]["contact_human"] = "maybe"
        summary = review_public_observations([r])
        rendered = json.dumps(summary, allow_nan=False)
        self.assertNotIn(secret, rendered)
        self.assertEqual(summary["v1_incomplete_or_failed_runs"], 1)
        self.assertEqual(summary["verified_game_scores"], 0)

    def test_duplicate_ids_cannot_inflate_human_contact(self):
        item = record_v1("20261025T014552Z-db2d3d790b")
        s = review_public_observations([item, item, item])
        self.assertEqual(s["duplicate_or_unsupported_records"], 2)
        self.assertEqual(s["v1_by_bridge_trace_and_observed_a_lead"][0]["human_hit_yes"], 1)

    def test_test_pass_and_process_success_are_not_live_results(self):
        ok = {"id": "20261025T012930Z-cf31bc55a7", "kind": "test",
              "outcome": "pass", "process_exit_code": 0}
        bad = {"id": "20261025T012937Z-a1d01e1a22", "kind": "test",
               "outcome": "fail", "process_exit_code": 1}
        data = review_public_observations([ok, bad])
        self.assertEqual(data["offline_unit_test_exits"]["pass"], 1)
        self.assertEqual(data["offline_unit_test_exits"]["fail"], 1)
        self.assertEqual(data["v1_by_bridge_trace_and_observed_a_lead"], [])
        self.assertEqual(data["verified_game_scores"], 0)

    def test_public_folder_only_never_scan_raw_ram_and_fail_closed_shape(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "research" / "observations"
            path.mkdir(parents=True)
            valid = record_v1("20261025T014552Z-db2d3d790b")
            (path / (valid["id"] + ".json")).write_text(json.dumps(valid))
            (path / "outcome-RAW-PRIVATE.json").write_text('{"kind":"v1"}')
            (path / "20261025T014559Z-too-big.json").write_text("X" * 40_000)
            (path / "20261025T015000Z-bad-input.json").write_text("{bad")
            rows = load_public_observations(path)
            self.assertEqual([r["id"] for r in rows], [valid["id"]])
            with self.assertRaisesRegex(ValueError, "isolated public"):
                load_public_observations(root)

    def test_cli_review_does_not_publish_or_start_dolphin(self):
        from wii_ai_golf.lab.github_sync import SyncReport
        calls = []
        record = record_v1("20261025T014552Z-db2d3d790b")

        def mock_git(cmd, *, cwd):
            calls.append(tuple(cmd))
            if cmd[:3] == ["remote", "get-url", "origin"]:
                return "https://github.com/Nate27624/Wii-AI-Golf.git"
            if cmd[0] == "clone":
                return ""
            raise AssertionError("unexpected git operation")
        with patch.object(research_cli, "sync_merged_main",
                          return_value=SyncReport("up_to_date")), \
             patch.object(research_cli, "_git", side_effect=mock_git), \
             patch("wii_ai_golf.evidence_review.load_public_observations",
                   return_value=[record]), \
             patch.object(research_cli, "_run") as spawn, \
             patch.object(research_cli, "publish_summary") as publish, \
             redirect_stdout(io.StringIO()) as out:
            self.assertEqual(research_cli.main(["review"]), 0)
        self.assertEqual(len(calls), 2)
        spawn.assert_not_called()
        publish.assert_not_called()
        data = out.getvalue()
        self.assertIn('"observed_a_lead_frames": 45', data)
        self.assertIn('"verified_game_scores": 0', data)


if __name__ == "__main__":
    unittest.main()
