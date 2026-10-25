"""Research CLI: no Dolphin on sync/test and no private RAM to GitHub."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import research_cli


class ResearchCliTests(unittest.TestCase):
    def test_source_sync_only_does_not_start_golf_or_publish(self):
        from wii_ai_golf.lab.github_sync import SyncReport
        with patch.object(research_cli, "sync_merged_main",
                          return_value=SyncReport("up_to_date", note="already current")), \
             patch.object(research_cli, "_run") as runner, \
             patch.object(research_cli, "publish_summary") as publish:
            self.assertEqual(research_cli.main(["sync"]), 0)
            runner.assert_not_called()
            publish.assert_not_called()

    def test_unapproved_live_run_never_launches_dolphin(self):
        from wii_ai_golf.lab.github_sync import SyncReport
        with patch.object(research_cli, "sync_merged_main",
                          return_value=SyncReport("up_to_date")), \
             patch.object(research_cli, "_run") as runner:
            with self.assertRaises(SystemExit):
                research_cli.main(["v1", "--a-lead", "12"])
            runner.assert_not_called()

    def test_dirty_sync_blocks_tests_and_publish(self):
        from wii_ai_golf.lab.github_sync import SyncReport
        with patch.object(research_cli, "sync_merged_main",
                          return_value=SyncReport("blocked", note="Dirty tree")), \
             patch.object(research_cli, "_run") as runner, \
             patch.object(research_cli, "publish_summary") as publish:
            self.assertEqual(research_cli.main(["test"]), 2)
            runner.assert_not_called()
            publish.assert_not_called()

    def test_only_new_sanitized_human_labels_reach_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            caps = root / "captures"
            caps.mkdir()
            start = datetime.now(timezone.utc) - timedelta(seconds=3)
            record = {
                "source": "live-emulator-read-only-US-Rev1+human-result-label",
                "human_observation": {
                    "contact_human": "yes",
                    "initial_club_pose_human": "back",
                    "displayed_distance_human": 2.1,
                    "private_player_name": "MUST NEVER PUBLISH",
                },
                "known_good_swing_request": {
                    "a_lead_requested_frames": 0,
                    "trace_sha256": "a" * 64,
                    "private_ram_hex": "SECRET_BYTES",
                },
                "candidate_ranking": {"windows": "RAW_RAM_NEVER_PUBLISH"},
                "settled_screen_observation": "already transitioned",
            }
            (caps / "outcome-unit-candidates.json").write_text(json.dumps(record))
            with patch.object(research_cli, "CAPTURES", caps):
                result = research_cli._fresh_human_labels(start)
            published = json.dumps(result)
            self.assertEqual(result["human"]["initial_club_pose_human"], "back")
            self.assertNotIn("MUST NEVER PUBLISH", published)
            self.assertNotIn("SECRET_BYTES", published)
            self.assertNotIn("RAW_RAM_NEVER_PUBLISH", published)
            self.assertNotIn("candidate_ranking", published)

    def test_missing_collector_summary_retains_human_miss_without_score(self):
        values = iter(["back", "no", "late"])
        result = research_cli._fallback_human_observation(answer=lambda _p: next(values))
        self.assertEqual(result["capture_status"], "human_fallback_after_missing_collector_summary")
        self.assertEqual(result["human"]["initial_club_pose_human"], "back")
        self.assertEqual(result["human"]["contact_human"], "no")
        self.assertEqual(result["human"]["motion_timing_human"], "late")
        self.assertFalse(result["verified_game_score"])
        self.assertTrue(research_cli._missing_capture_needs_fallback(
            {"capture_status": "none_or_ambiguous"}))
        self.assertFalse(research_cli._missing_capture_needs_fallback(
            {"capture_status": "sanitized_human_annotation_only"}))

    def test_invalid_fallback_answers_are_unknown_not_inferred_hit(self):
        result = research_cli._fallback_human_observation(answer=lambda _p: "")
        self.assertEqual(result["human"]["contact_human"], "unknown")
        self.assertEqual(result["human"]["motion_timing_human"], "unknown")

    def test_ambiguous_capture_summary_does_not_guess_result(self):
        with tempfile.TemporaryDirectory() as folder:
            caps = Path(folder)
            for i in (1, 2):
                (caps / f"outcome-{i}-candidates.json").write_text("{}")
            with patch.object(research_cli, "CAPTURES", caps):
                result = research_cli._fresh_human_labels(
                    datetime.now(timezone.utc) - timedelta(seconds=5))
            self.assertEqual(result["capture_status"], "none_or_ambiguous")
            self.assertNotIn("human", result)


if __name__ == "__main__":
    unittest.main()
