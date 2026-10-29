"""S003 study-contract regressions: never turn a legacy power-map arm into public evidence.

All actions are mocked. No Dolphin, ROM, RAM, child process, or Git publication.
"""
from __future__ import annotations

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
from wii_ai_golf.lab.github_sync import SyncReport


class S003StudyContractTests(unittest.TestCase):
    def test_frozen_ten_arm_plan_is_not_reinterpreted_as_m15(self):
        self.assertEqual(
            tuple(research_cli.POWER_MAP_STUDY),
            ((1.0, 1.0), (0.8, 1.0), (1.0, 1.2),
             (0.9, 1.0), (1.0, 0.8), (1.0, 1.0),
             (1.0, 0.8), (0.9, 1.0), (1.0, 1.2), (0.8, 1.0)),
        )
        self.assertEqual(len(research_cli.power_map_commands()), 10)

    def test_visual_first_study_id_refuses_before_emulator_or_publication(self):
        # Trial 1 (speed=1, backswing=1) otherwise fits M1.5. It must
        # refuse specifically because a trial-indexed study join is unapproved.
        with patch.object(research_cli, "sync_merged_main",
                          return_value=SyncReport("up_to_date")), \
             patch.object(research_cli, "_run") as runner, \
             patch.object(research_cli, "publish_summary") as publisher, \
             patch.object(research_cli, "v1_clean_boot_args") as boot:
            with self.assertRaises(SystemExit):
                research_cli.main([
                    "v1", "--live", "--visual-first", "--a-lead", "45",
                    "--study-id", research_cli.POWER_MAP_ID,
                    "--trial-index", "1",
                ])
            runner.assert_not_called()
            publisher.assert_not_called()
            boot.assert_not_called()

    def test_legacy_study_arm_preserves_local_metadata_but_cannot_publish(self):
        # Mock a successful child and positive *human-only* contact. Neither
        # this label nor a displayed 100ft penalty proves joined distance.
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(research_cli, "sync_merged_main",
                          return_value=SyncReport("up_to_date")), \
             patch.object(research_cli, "_run", return_value=0) as runner, \
             patch.object(research_cli, "v1_clean_boot_args",
                          return_value=["--dolphin", "MOCK-EXE"]), \
             patch.object(research_cli, "DATA", Path(folder)), \
             patch.object(research_cli, "_head", return_value="a" * 40), \
             patch.object(research_cli, "publish_summary") as publisher, \
             patch("wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                   return_value={
                       "revision": "V1-neutral-swing-calls",
                       "safe_for_isolated_legacy_copy": True,
                   }), \
             patch.object(research_cli, "_fresh_human_labels",
                          return_value={
                              "capture_status": "sanitized_human_annotation_only",
                              "human": {
                                  "contact_human": "yes",
                                  "finished_on_green_human": "no",
                                  "displayed_distance_human": 100.0,
                                  "displayed_unit_human": "ft",
                              },
                          }), \
             patch.object(research_cli, "_fallback_human_observation") as fallback:
            self.assertEqual(research_cli.main([
                "v1", "--live", "--a-lead", "45",
                "--speed-scale", "0.8",
                "--study-id", research_cli.POWER_MAP_ID,
                "--trial-index", "2",
            ]), 0)
            runner.assert_called_once()
            publisher.assert_not_called()
            fallback.assert_not_called()
            outputs = list((Path(folder) / "research-cli").glob("*.json"))
            self.assertEqual(len(outputs), 1)
            result = json.loads(outputs[0].read_text(encoding="utf-8"))
            self.assertEqual(result["study_id"], research_cli.POWER_MAP_ID)
            self.assertEqual(result["trial_index"], 2)
            self.assertEqual(result["trial_count"], 10)
            self.assertEqual(result["kind"], "v1_attempt")
            self.assertEqual(result["capture_status"], "legacy_v1_local_only_unjoined")
            self.assertFalse(result["shot_dispatch_verified_by_collector"])
            self.assertFalse(result["trial_valid_for_action_outcome"])
            self.assertFalse(result["numeric_distance_target_eligible"])
            self.assertFalse(result["train_approved"])
            self.assertFalse(result["verified_game_score"])


if __name__ == "__main__":
    unittest.main()
