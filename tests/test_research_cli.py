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
    def test_ten_trial_plan_has_two_repeats_each_and_no_emulator(self):
        from collections import Counter
        from wii_ai_golf.lab.github_sync import SyncReport
        self.assertEqual(len(research_cli.POWER_MAP_STUDY), 10)
        self.assertEqual(set(Counter(research_cli.POWER_MAP_STUDY).values()), {2})
        with patch.object(research_cli, "sync_merged_main",
                          return_value=SyncReport("up_to_date")), \
             patch.object(research_cli, "_run") as run, \
             patch.object(research_cli, "publish_summary") as upload:
            self.assertEqual(research_cli.main(["study"]), 0)
            run.assert_not_called()
            upload.assert_not_called()
        commands = research_cli.power_map_commands()
        self.assertEqual(len(commands), 10)
        self.assertIn("--trial-index 10", commands[-1])
        self.assertTrue(all("--a-lead 45" in command for command in commands))

    def test_study_rejects_non_preregistered_settings(self):
        from wii_ai_golf.lab.github_sync import SyncReport
        with patch.object(research_cli, "sync_merged_main",
                          return_value=SyncReport("up_to_date")), \
             patch.object(research_cli, "_run") as run:
            with self.assertRaises(SystemExit):
                research_cli.main(["v1", "--live", "--a-lead", "45",
                    "--study-id", research_cli.POWER_MAP_ID, "--trial-index", "1",
                    "--speed-scale", "0.8"])
            run.assert_not_called()

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

    def test_motion_calibration_forwards_single_bounded_scale_and_lead(self):
        from wii_ai_golf.lab.github_sync import SyncReport
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(research_cli, "sync_merged_main",
                          return_value=SyncReport("up_to_date")), \
             patch.object(research_cli, "_run", return_value=0) as runner, \
             patch.object(research_cli, "v1_clean_boot_args", return_value=["--dolphin", "MOCK-CLEAN-EXE", "--dolphin-user", "MOCK-CLEAN-USER", "--config", "MOCK-LOCAL-CONFIG", "--catalog", "MOCK-LOCAL-CATALOG"]), \
             patch.object(research_cli, "DATA", Path(folder)), \
             patch.object(research_cli, "publish_summary") as publisher, \
             patch("wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                   return_value={"revision": "V1-neutral-swing-calls",
                                 "safe_for_isolated_legacy_copy": True}), \
             patch.object(research_cli, "_fresh_human_labels",
                          return_value={"capture_status": "none_or_ambiguous"}), \
             patch.object(research_cli, "_fallback_human_observation",
                          return_value={"human": {"contact_human": "unknown"}}):
            self.assertEqual(research_cli.main(
                ["v1", "--live", "--a-lead", "45", "--speed-scale", "0.9"]), 0)
            command = runner.call_args.args[0]
            self.assertEqual(command[command.index("--a-lead-frames") + 1], "45")
            self.assertEqual(command[command.index("--motion-scale") + 1], "1.0")
            self.assertEqual(command[command.index("--speed-scale") + 1], "0.9")
            self.assertIn("--ask-power", command)
            publisher.assert_not_called()
            local = list((Path(folder) / "research-cli").glob("*.json"))
            self.assertEqual(len(local), 1)
            report = json.loads(local[0].read_text(encoding="utf-8"))
            self.assertEqual(report["requested_motion_scale"], 1.0)
            self.assertEqual(report["requested_speed_scale"], 0.9)
            self.assertEqual(report["kind"], "v1_attempt")
            self.assertFalse(report["trial_valid_for_action_outcome"])
            self.assertFalse(report["train_approved"])

    def test_legacy_v1_contact_cancel_and_ambiguous_child_never_publish(self):
        from wii_ai_golf.lab.github_sync import SyncReport
        cases = (
            (0, {"capture_status": "sanitized_human_annotation_only",
                 "human": {"contact_human": "yes",
                           "finished_on_green_human": "yes",
                           "displayed_distance_human": 15.2,
                           "displayed_unit_human": "ft"},
                 "settled_screen_observation": "operator_confirmed_before_transition"}),
            (0, {"capture_status": "sanitized_human_annotation_only",
                 "human": {"contact_human": "no"}}),
            (0, {"capture_status": "sanitized_human_annotation_only",
                 "human": {"contact_human": "unknown"}}),
            (0, {"capture_status": "none_or_ambiguous"}),
            (0, {"capture_status": "sanitized_human_annotation_only",
                 "human": {"contact_human": "yes"},
                 "settled_screen_observation":
                     "screen_had_already_transitioned_before_settled_samples"}),
            (2, {"capture_status": "sanitized_human_annotation_only",
                 "human": {"contact_human": "yes"}}),
        )
        for exit_code, candidate in cases:
            with self.subTest(exit_code=exit_code, candidate=candidate), \
                 tempfile.TemporaryDirectory() as folder, \
                 patch.object(research_cli, "sync_merged_main",
                              return_value=SyncReport("up_to_date")), \
                 patch.object(research_cli, "_run", return_value=exit_code), \
                 patch.object(research_cli, "v1_clean_boot_args",
                              return_value=["--dolphin", "MOCK-CLEAN-EXE"]), \
                 patch.object(research_cli, "DATA", Path(folder)), \
                 patch.object(research_cli, "publish_summary") as publish, \
                 patch("wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                       return_value={"revision": "V1-neutral-swing-calls",
                                     "safe_for_isolated_legacy_copy": True}), \
                 patch.object(research_cli, "_fresh_human_labels",
                              return_value=candidate), \
                 patch.object(research_cli, "_fallback_human_observation",
                              return_value={"human": {"contact_human": "unknown"}}):
                self.assertEqual(research_cli.main(
                    ["v1", "--live", "--a-lead", "45"]), exit_code)
                publish.assert_not_called()
                files = list((Path(folder) / "research-cli").glob("*.json"))
                self.assertEqual(len(files), 1)
                report = json.loads(files[0].read_text(encoding="utf-8"))
                self.assertEqual(report["kind"], "v1_attempt")
                self.assertFalse(report["trial_valid_for_action_outcome"])
                self.assertFalse(report["shot_dispatch_verified_by_collector"])
                self.assertFalse(report["train_approved"])
                self.assertFalse(report["numeric_distance_target_eligible"])
                self.assertEqual(report["shot_dispatched"], "unknown")
                self.assertEqual(
                    report["legacy_candidate_capture_status_unverified"],
                    candidate["capture_status"] if exit_code == 0
                    else "failed_or_cancelled_action")
                self.assertEqual(
                    report["attempt_status"],
                    "failed_or_cancelled_action" if exit_code
                    else "legacy_child_identity_unverified")

    def test_offline_test_command_retains_existing_publisher_behavior(self):
        from wii_ai_golf.lab.github_sync import SyncReport
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(research_cli, "sync_merged_main",
                          return_value=SyncReport("up_to_date")), \
             patch.object(research_cli, "_run", return_value=0), \
             patch.object(research_cli, "DATA", Path(folder)), \
             patch.object(research_cli, "publish_summary") as publish:
            self.assertEqual(research_cli.main(["test", "--pattern", "test_example.py"]), 0)
            publish.assert_called_once()
            self.assertEqual(publish.call_args.args[0]["kind"], "test")

    def test_direct_publisher_rejects_unqualified_and_unsafe_without_git(self):
        base = {
            "schema": 1, "id": "20261029T120000Z-abcdef1234",
            "kind": "test", "started_utc": "2026-10-29T12:00:00+00:00",
            "git_commit": "a" * 40, "process_exit_code": 0,
            "verified_game_score": False, "outcome": "pass",
            "test_pattern": "test_*.py",
        }
        invalid = (
            {"kind": "v1_attempt"},
            {"kind": "v1", "visual_first": True},
            {"kind": "v1", "visual_first": True,
             "capture_status": "visual_first_joined",
             "informative_action_outcome_trial": True},
            {"id": "../private-file"},
            {"id": "20261029T120000Z-..\\..\\evil"},
            {"process_exit_code": True},
            {"process_exit_code": 1},
            {"verified_game_score": True},
            {"outcome": "fail"},
            {"test_pattern": "../../private.txt"},
            {"test_pattern": "secret/path.py"},
            {"git_commit": "private-local-path"},
        )
        with patch.object(research_cli, "_git") as git:
            for mutation in invalid:
                with self.subTest(mutation=mutation):
                    record = dict(base, **mutation)
                    with self.assertRaises(ValueError):
                        research_cli.publish_summary(record)
            git.assert_not_called()

    def test_passing_offline_test_publishes_projection_not_private_payload(self):
        record = {
            "schema": 1, "id": "20261029T120000Z-abcdef1234",
            "kind": "test", "started_utc": "2026-10-29T12:00:00+00:00",
            "git_commit": "a" * 40, "process_exit_code": 0,
            "verified_game_score": False, "outcome": "pass",
            "test_pattern": "test_*.py",
            "private_ram": "MUST_NOT_PUBLISH",
            "candidate_ranking": {"raw_bytes": "MUST_NOT_PUBLISH"},
        }
        published = []

        def fake_git(args, *, cwd):
            if args[:3] == ["remote", "get-url", "origin"]:
                return research_cli.REPO_URL
            if args[0] == "clone":
                Path(args[-1]).mkdir()
            if args[0] == "add":
                published.append(json.loads((Path(cwd) / args[-1]).read_text()))
            return ""

        with patch.object(research_cli, "_git", side_effect=fake_git) as git:
            url = research_cli.publish_summary(record)
        self.assertIn("research/observations", url)
        self.assertEqual(len(published), 1)
        self.assertEqual(published[0]["outcome"], "pass")
        self.assertEqual(published[0]["test_pattern"], "test_*.py")
        self.assertEqual(published[0]["kind"], "test")
        self.assertNotIn("private_ram", published[0])
        self.assertNotIn("candidate_ranking", published[0])
        self.assertNotIn("MUST_NOT_PUBLISH", json.dumps(published))
        self.assertEqual(len([c for c in git.call_args_list
                              if c.args[0][0] == "push"]), 1)

    def test_direct_v1_publisher_rejoins_child_and_bridge_before_git(self):
        joined = {
            "capture_status": "visual_first_joined",
            "shot_dispatch_verified_by_collector": True,
            "informative_action_outcome_trial": True,
            "hitting_green_first_ball_context_human_confirmed": True,
            "game_id_revision_mode_machine_verified": False,
            "controller": {"a_lead_atomic_bridge_callback": True,
                           "trace_sha256": "c" * 64},
            "human": {"contact_human": "yes", "finished_on_green_human": "no",
                      "displayed_distance_human": 100.0,
                      "displayed_distance_source": "offgreen_100ft_penalty"},
            "settled_screen_observation": "human_terminal_before_transition",
            "outcome_is_censored_penalty": True,
            "numeric_distance_target_eligible": False,
            "train_approved": False, "verified_game_score": False,
            "physical_distance_verified": False,
        }
        record = {
            "schema": 1, "id": "20261029T120000Z-abcdef1234",
            "kind": "v1", "started_utc": "2026-10-29T12:00:00+00:00",
            "git_commit": "a" * 40, "process_exit_code": 0,
            "visual_first": True, "bridge_sha256": "b" * 64,
            "requested_a_lead_frames": 45, "requested_motion_scale": 1.0,
            "requested_speed_scale": 1.0, "requested_backswing_scale": 1.0,
            "private_ram_words": "MUST_NOT_PUBLISH",
            **joined,
        }
        with patch.object(research_cli, "_joined_visual_first",
                          return_value=joined) as child, \
             patch("wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                   return_value={"revision": "V1-atomic-a45",
                                 "sha256": "b" * 64}), \
             patch.object(research_cli, "_git") as git:
            expected = research_cli._public_observation_record(record)
            self.assertEqual(expected["human"], joined["human"])
            self.assertNotIn("private_ram_words", expected)
            self.assertFalse(expected["numeric_distance_target_eligible"])
            self.assertFalse(expected["train_approved"])
            self.assertTrue(expected["outcome_is_censored_penalty"])
            child.assert_called_once()
            # A changed child or bridge must refuse before opening a clone.
            with patch.object(research_cli, "_joined_visual_first",
                              return_value={"capture_status": "visual_first_join_refused"}):
                with self.assertRaisesRegex(ValueError, "child identity"):
                    research_cli.publish_summary(record)
            with patch("wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                       return_value={"revision": "V1-atomic-a45",
                                     "sha256": "d" * 64}):
                with self.assertRaisesRegex(ValueError, "bridge provenance"):
                    research_cli.publish_summary(record)
            git.assert_not_called()

        malformed = dict(record)
        malformed["informative_action_outcome_trial"] = False
        with patch.object(research_cli, "_git") as git:
            with self.assertRaisesRegex(ValueError, "unjoined or ineligible"):
                research_cli.publish_summary(malformed)
            git.assert_not_called()

    def test_multidimensional_motion_scale_is_not_allowed_in_v1_cli(self):
        from wii_ai_golf.lab.github_sync import SyncReport
        with patch.object(research_cli, "sync_merged_main", return_value=SyncReport("up_to_date")):
            with self.assertRaises(SystemExit):
                research_cli.main(["v1", "--live", "--motion-scale", "0.8"])

    def test_backswing_only_is_forwarded_and_reported(self):
        from wii_ai_golf.lab.github_sync import SyncReport
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(research_cli, "sync_merged_main", return_value=SyncReport("up_to_date")), \
             patch.object(research_cli, "_run", return_value=0) as runner, \
             patch.object(research_cli, "v1_clean_boot_args", return_value=["--dolphin", "MOCK-CLEAN-EXE", "--dolphin-user", "MOCK-CLEAN-USER", "--config", "MOCK-LOCAL-CONFIG", "--catalog", "MOCK-LOCAL-CATALOG"]), \
             patch.object(research_cli, "DATA", Path(folder)), \
             patch.object(research_cli, "publish_summary") as publish, \
             patch("wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                   return_value={"revision": "V1-neutral-swing-calls",
                                 "safe_for_isolated_legacy_copy": True}), \
             patch.object(research_cli, "_fresh_human_labels",
                          return_value={"capture_status": "sanitized_human_annotation_only"}):
            self.assertEqual(research_cli.main(["v1", "--live", "--a-lead", "45",
                                               "--backswing-scale", "0.8"]), 0)
            command = runner.call_args.args[0]
            self.assertEqual(command[command.index("--backswing-scale") + 1], "0.8")
            self.assertEqual(command[command.index("--speed-scale") + 1], "1.0")
            self.assertEqual(command[command.index("--a-lead-frames") + 1], "45")
            publish.assert_not_called()
            local = list((Path(folder) / "research-cli").glob("*.json"))
            self.assertEqual(len(local), 1)
            report = json.loads(local[0].read_text(encoding="utf-8"))
            self.assertEqual(report["requested_backswing_scale"], 0.8)
            self.assertEqual(report["kind"], "v1_attempt")
            self.assertFalse(report["shot_dispatch_verified_by_collector"])

    def test_reject_simultaneous_backswing_and_speed_change(self):
        from wii_ai_golf.lab.github_sync import SyncReport
        with patch.object(research_cli, "sync_merged_main", return_value=SyncReport("up_to_date")):
            with self.assertRaises(SystemExit):
                research_cli.main(["v1", "--live", "--backswing-scale", "0.8",
                                   "--speed-scale", "0.9"])

    def test_unapproved_motion_scale_is_rejected(self):
        with self.assertRaises(SystemExit):
            research_cli.main(["v1", "--live", "--motion-scale", "0.9"])

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
