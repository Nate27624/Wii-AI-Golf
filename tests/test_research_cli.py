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
from collect_outcome_transition import _build_v1_trace_and_digest


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
             patch.object(research_cli, "v1_clean_boot_args",
                          return_value=["--dolphin", "MOCK-CLEAN-EXE",
                                        "--dolphin-user", "MOCK-ISOLATED-USER",
                                        "--config", "MOCK-LOCAL-CONFIG",
                                        "--catalog", "MOCK-LOCAL-CATALOG"]), \
             patch.object(research_cli, "DATA", Path(folder)), \
             patch.object(research_cli, "publish_summary") as publisher, \
             patch("wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                   return_value={"revision": "V1-neutral-swing-calls",
                                 "safe_for_isolated_legacy_copy": True}), \
             patch.object(research_cli, "_fresh_human_labels",
                          return_value={"capture_status": "sanitized_human_annotation_only",
                                        "settled_screen_observation": "operator_confirmed_before_transition",
                                        "terminal_capture_mode": "result_first_human_prompt",
                                        "terminal_human_category": "on_green",
                                        "human": {"contact_human": "yes"}}), \
             patch.object(research_cli, "_fallback_human_observation",
                          return_value={"human": {"contact_human": "unknown"}}):
            self.assertEqual(research_cli.main(
                ["v1", "--live", "--a-lead", "45", "--speed-scale", "0.9"]), 0)
            command = runner.call_args.args[0]
            self.assertEqual(command[command.index("--a-lead-frames") + 1], "45")
            self.assertEqual(command[command.index("--motion-scale") + 1], "1.0")
            self.assertEqual(command[command.index("--speed-scale") + 1], "0.9")
            self.assertIn("--ask-power", command)
            publisher.assert_called_once()
            self.assertEqual(publisher.call_args.args[0]["requested_motion_scale"], 1.0)
            self.assertEqual(publisher.call_args.args[0]["requested_speed_scale"], 0.9)

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
             patch.object(research_cli, "v1_clean_boot_args",
                          return_value=["--dolphin", "MOCK-CLEAN-EXE",
                                        "--dolphin-user", "MOCK-ISOLATED-USER",
                                        "--config", "MOCK-LOCAL-CONFIG",
                                        "--catalog", "MOCK-LOCAL-CATALOG"]), \
             patch.object(research_cli, "DATA", Path(folder)), \
             patch.object(research_cli, "publish_summary") as publish, \
             patch("wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                   return_value={"revision": "V1-neutral-swing-calls",
                                 "safe_for_isolated_legacy_copy": True}), \
             patch.object(research_cli, "_fresh_human_labels",
                          return_value={"capture_status": "sanitized_human_annotation_only",
                                        "settled_screen_observation": "operator_confirmed_before_transition",
                                        "terminal_capture_mode": "result_first_human_prompt",
                                        "terminal_human_category": "on_green",
                                        "human": {"contact_human": "yes"}}):
            self.assertEqual(research_cli.main(["v1", "--live", "--a-lead", "45",
                                               "--backswing-scale", "0.8"]), 0)
            command = runner.call_args.args[0]
            self.assertEqual(command[command.index("--backswing-scale") + 1], "0.8")
            self.assertEqual(command[command.index("--speed-scale") + 1], "1.0")
            self.assertEqual(command[command.index("--a-lead-frames") + 1], "45")
            self.assertEqual(publish.call_args.args[0]["requested_backswing_scale"], 0.8)

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
                    "finished_on_green_human": "yes",
                    "private_player_name": "MUST NEVER PUBLISH",
                },
                "known_good_swing_request": {
                    "a_lead_requested_frames": 0,
                    "motion_scale": 1.0, "speed_scale": 1.0,
                    "backswing_scale": 1.0, "generated_trace_frames": 89,
                    "trace_sha256": _build_v1_trace_and_digest(
                        motion_scale=1.0, speed_scale=1.0, backswing_scale=1.0)[1],
                    "private_ram_hex": "SECRET_BYTES",
                },
                "run_token": "b" * 32,
                "swing_dispatch": {"state": "complete", "applied_frames": 89},
                "schema_version": 1,
                "candidate_ranking": {"windows": "RAW_RAM_NEVER_PUBLISH"},
                "settled_screen_observation": "operator_confirmed_before_transition",
                "terminal_capture_mode": "result_first_human_prompt",
                "terminal_human_category": "on_green",
            }
            (caps / "outcome-unit-candidates.json").write_text(json.dumps(record))
            with patch.object(research_cli, "CAPTURES", caps):
                result = research_cli._fresh_human_labels(
                    start, run_token="b" * 32,
                    expected_controller={
                        "a_lead_requested_frames": 0, "motion_scale": 1.0,
                        "speed_scale": 1.0, "backswing_scale": 1.0,
                    })
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
                    datetime.now(timezone.utc) - timedelta(seconds=5),
                    run_token="c" * 32, expected_controller={})
            self.assertEqual(result["capture_status"], "none_or_ambiguous")
            self.assertNotIn("human", result)


    def test_unqualified_zero_exit_does_not_publish_or_guess_contact(self):
        from wii_ai_golf.lab.github_sync import SyncReport
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(research_cli, "sync_merged_main",
                          return_value=SyncReport("up_to_date")), \
             patch.object(research_cli, "_run", return_value=0), \
             patch.object(research_cli, "v1_clean_boot_args", return_value=[]), \
             patch.object(research_cli, "DATA", Path(folder)), \
             patch.object(research_cli, "_fresh_human_labels",
                          return_value={"capture_status": "none_or_ambiguous"}), \
             patch.object(research_cli, "_fallback_human_observation") as fallback, \
             patch.object(research_cli, "publish_summary") as publish, \
             patch("wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                   return_value={"revision": "V1-neutral-swing-calls",
                                 "safe_for_isolated_legacy_copy": True}):
            self.assertEqual(research_cli.main(["v1", "--live"]), 2)
            fallback.assert_not_called()
            publish.assert_not_called()
            local = list((Path(folder) / "research-cli").glob("*.json"))
            self.assertEqual(len(local), 1)
            row = json.loads(local[0].read_text())
            self.assertEqual(row["kind"], "v1_attempt")
            self.assertFalse(row["trial_valid_for_action_outcome"])

    def test_canceled_or_failed_child_never_publishes_or_prompts_contact(self):
        from wii_ai_golf.lab.github_sync import SyncReport
        for child_exit in (40, 41, 1, 2):
            with self.subTest(child_exit=child_exit), \
                 tempfile.TemporaryDirectory() as folder, \
                 patch.object(research_cli, "sync_merged_main",
                              return_value=SyncReport("up_to_date")), \
                 patch.object(research_cli, "_run", return_value=child_exit), \
                 patch.object(research_cli, "v1_clean_boot_args", return_value=[]), \
                 patch.object(research_cli, "DATA", Path(folder)), \
                 patch.object(research_cli, "_fresh_human_labels") as labels, \
                 patch.object(research_cli, "_fallback_human_observation") as fallback, \
                 patch.object(research_cli, "publish_summary") as publish, \
                 patch("wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                       return_value={"revision": "V1-neutral-swing-calls",
                                     "safe_for_isolated_legacy_copy": True}):
                self.assertEqual(research_cli.main(["v1", "--live"]), child_exit)
                labels.assert_not_called()
                fallback.assert_not_called()
                publish.assert_not_called()
                row_path, = (Path(folder) / "research-cli").glob("*.json")
                row = json.loads(row_path.read_text())
                self.assertEqual(row["kind"], "v1_attempt")
                self.assertEqual(row["shot_dispatched"], "unknown")
                self.assertFalse(row["trial_valid_for_action_outcome"])

    def test_no_or_unknown_contact_never_publishes_as_action_outcome(self):
        # Fabricated only: completed scheduler + visible terminal result
        # is insufficient without affirmative HUMAN observation of contact.
        from contextlib import ExitStack
        from wii_ai_golf.lab.github_sync import SyncReport
        for contact in ("no", "unknown", None, "yes"):
            with self.subTest(contact=contact), tempfile.TemporaryDirectory() as folder:
                with ExitStack() as stack:
                    stack.enter_context(patch.object(
                        research_cli, "sync_merged_main",
                        return_value=SyncReport("up_to_date")))
                    stack.enter_context(patch.object(
                        research_cli, "_run", return_value=0))
                    stack.enter_context(patch.object(
                        research_cli, "v1_clean_boot_args", return_value=[]))
                    stack.enter_context(patch.object(
                        research_cli, "DATA", Path(folder)))
                    stack.enter_context(patch.object(
                        research_cli, "_fresh_human_labels", return_value={
                            "capture_status": "sanitized_human_annotation_only",
                            "settled_screen_observation": "operator_confirmed_before_transition",
                            "terminal_capture_mode": "result_first_human_prompt",
                            "terminal_human_category": "off_green",
                            "human": {"contact_human": contact}}))
                    publish = stack.enter_context(patch.object(
                        research_cli, "publish_summary"))
                    fallback = stack.enter_context(patch.object(
                        research_cli, "_fallback_human_observation"))
                    stack.enter_context(patch(
                        "wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                        return_value={"revision": "V1-neutral-swing-calls",
                                      "safe_for_isolated_legacy_copy": True}))
                    code = research_cli.main(["v1", "--live"])
                    if contact == "yes":
                        self.assertEqual(code, 0)
                        publish.assert_called_once()
                    else:
                        self.assertEqual(code, 2)
                        publish.assert_not_called()
                    fallback.assert_not_called()
                    (saved,) = (Path(folder) / "research-cli").glob("*.json")
                    row = json.loads(saved.read_text(encoding="utf-8"))
                    self.assertEqual(row["trial_valid_for_action_outcome"], contact == "yes")
                    self.assertEqual(row["kind"], "v1" if contact == "yes" else "v1_attempt")
                    if contact != "yes":
                        self.assertEqual(row["attempt_status"],
                                         "positive_ball_contact_not_observed")

    def test_foreign_run_and_invalid_controls_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            caps = Path(folder)
            start = datetime.now(timezone.utc) - timedelta(seconds=10)
            expected = {"a_lead_requested_frames": 45, "motion_scale": 1.0,
                        "speed_scale": 1.0, "backswing_scale": 1.0}
            row = {
                "source": "live-emulator-read-only-US-Rev1+human-result-label",
                "run_token": "d" * 32,
                "human_observation": {"contact_human": "yes",
                                      "finished_on_green_human": "no",
                                      "displayed_distance_human": 100,
                                      "displayed_unit_human": "ft"},
                "known_good_swing_request": {**expected,
                    "generated_trace_frames": 89, "a_lead_observed_frame_delta": 45,
                    "trace_sha256": _build_v1_trace_and_digest(
                        motion_scale=1.0, speed_scale=1.0, backswing_scale=1.0)[1]},
                "swing_dispatch": {"state": "complete", "applied_frames": 89},
                "settled_screen_observation": "operator_confirmed_before_transition",
                "terminal_capture_mode": "result_first_human_prompt",
                "terminal_human_category": "off_green",
            }
            file = caps / "outcome-test-candidates.json"
            file.write_text(json.dumps(row))
            with patch.object(research_cli, "CAPTURES", caps):
                foreign = research_cli._fresh_human_labels(
                    start, run_token="e" * 32, expected_controller=expected)
                self.assertNotEqual(foreign["capture_status"],
                                    "sanitized_human_annotation_only")
                wrong = research_cli._fresh_human_labels(
                    start, run_token="d" * 32,
                    expected_controller={**expected, "speed_scale": 0.8})
                self.assertEqual(wrong["capture_status"],
                                 "unqualified_child_trace_or_controls")
                good = research_cli._fresh_human_labels(
                    start, run_token="d" * 32, expected_controller=expected)
                self.assertEqual(good["capture_status"],
                                 "sanitized_human_annotation_only")
                self.assertEqual(good["distance_interpretation"],
                                 "censored_offgreen_100ft_penalty")
                self.assertNotIn("run_token", good)
                for observed in (None, 44, True):
                    with self.subTest(observed_a_lead_delta=observed):
                        row["known_good_swing_request"]["a_lead_observed_frame_delta"] = observed
                        file.write_text(json.dumps(row))
                        rejected = research_cli._fresh_human_labels(
                            start, run_token="d" * 32, expected_controller=expected)
                        self.assertEqual(rejected["capture_status"],
                                         "unqualified_child_a_lead_observation")
                row["known_good_swing_request"]["a_lead_observed_frame_delta"] = 45
                file.write_text(json.dumps(row))
                restored = research_cli._fresh_human_labels(
                    start, run_token="d" * 32, expected_controller=expected)
                self.assertEqual(restored["capture_status"], "sanitized_human_annotation_only")
                digest = row["known_good_swing_request"]["trace_sha256"]
                row["known_good_swing_request"]["trace_sha256"] = "f" * 64
                file.write_text(json.dumps(row))
                wrong_hash = research_cli._fresh_human_labels(
                    start, run_token="d" * 32, expected_controller=expected)
                self.assertEqual(wrong_hash["capture_status"],
                                 "unqualified_child_trace_digest")
                self.assertNotIn("human", wrong_hash)
                row["known_good_swing_request"]["trace_sha256"] = digest
                row["known_good_swing_request"]["generated_trace_frames"] = 88
                row["swing_dispatch"]["applied_frames"] = 88
                file.write_text(json.dumps(row))
                wrong_length = research_cli._fresh_human_labels(
                    start, run_token="d" * 32, expected_controller=expected)
                self.assertEqual(wrong_length["capture_status"],
                                 "unqualified_child_trace_digest")
                row["known_good_swing_request"]["generated_trace_frames"] = 89
                row["swing_dispatch"]["applied_frames"] = 89
                row["settled_screen_observation"] = {"private_ram": "SECRET"}
                file.write_text(json.dumps(row))
                leak = research_cli._fresh_human_labels(
                    start, run_token="d" * 32, expected_controller=expected)
                self.assertEqual(leak["capture_status"],
                                 "unqualified_terminal_timing")
                self.assertNotIn("SECRET", json.dumps(leak))

    def test_late_terminal_result_is_private_attempt_not_completed_outcome(self):
        from wii_ai_golf.lab.github_sync import SyncReport
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(research_cli, "sync_merged_main",
                          return_value=SyncReport("up_to_date")), \
             patch.object(research_cli, "_run", return_value=0), \
             patch.object(research_cli, "v1_clean_boot_args", return_value=[]), \
             patch.object(research_cli, "DATA", Path(folder)), \
             patch.object(research_cli, "_fresh_human_labels",
                          return_value={
                              "capture_status": "sanitized_human_annotation_only",
                              "settled_screen_observation":
                                  "screen_had_already_transitioned_before_settled_samples",
                              "terminal_capture_mode": "result_first_human_prompt",
                              "terminal_human_category": "transitioned",
                              "human": {"contact_human": "yes"}}), \
             patch.object(research_cli, "publish_summary") as publish, \
             patch("wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                   return_value={"revision": "V1-neutral-swing-calls",
                                 "safe_for_isolated_legacy_copy": True}):
            self.assertEqual(research_cli.main(["v1", "--live"]), 2)
            publish.assert_not_called()
            row_path, = (Path(folder) / "research-cli").glob("*.json")
            row = json.loads(row_path.read_text())
            self.assertEqual(row["kind"], "v1_attempt")
            self.assertEqual(row["attempt_status"],
                             "terminal_result_missing_or_unqualified")
            self.assertFalse(row["trial_valid_for_action_outcome"])


if __name__ == "__main__":
    unittest.main()
