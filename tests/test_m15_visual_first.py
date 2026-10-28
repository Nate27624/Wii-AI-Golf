"""M1.5 visual outcome first: purely fabricated controls, never launch Dolphin."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for part in (str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")):
    if part not in sys.path:
        sys.path.insert(0, part)

from scripts.collect_outcome_transition import _visual_first_label, run_session
import research_cli

TOKEN = "20261028T220000Z-0123456789"


def child_summary():
    return {
        "run_token": TOKEN,
        "source": "live-emulator-read-only-US-Rev1+human-result-label",
        "outcome_collection_mode": "human_terminal_first_no_ram",
        "raw_data_created": False,
        "candidate_ranking": None,
        "swing_dispatch": {"state": "complete", "applied_frames": 89},
        "known_good_swing_request": {
            "preset": "forward", "generated_trace_frames": 89,
            "trace_sha256": "a" * 64, "motion_scale": 1.0,
            "speed_scale": 1.0, "backswing_scale": 1.0,
            "a_lead_requested_frames": 45,
            "a_lead_observed_frame_delta": 45,
        },
        "human_observation": {
            "contact_human": "yes", "finished_on_green_human": "no",
            "terminal_screen_seen_before_transition_human": True,
            "visible_result_class_human": "offgreen",
            "displayed_distance_human": 100.0,
            "displayed_unit_human": "ft",
            "displayed_distance_source": "offgreen_100ft_penalty",
            "game_distance_verified_by_memory": False,
            "initial_club_pose_human": "back",
            "initial_club_pose_verified_by_memory": False,
            "shot_start_frame_before_controller_trace": 120,
            "displayed_power_percent_human": 75.0,
            "displayed_power_verified_by_memory": False,
            "private_sensitive_ram": "MUST_NOT_PUBLISH",
        },
        "settled_screen_observation": "human_terminal_before_transition",
        "candidate_other_private_data": {"raw_words": "MUST_NOT_PUBLISH"},
    }


class VisualFirstCollectorTests(unittest.TestCase):
    def test_compact_green_result_before_any_additional_rpc_or_ram(self):
        events = []
        responses = iter(["", "", "G:15.2ft", "yes"])
        def get_response(_prompt):
            events.append("prompt")
            return next(responses)
        def swing(_rpc):
            events.append("swing")
            return {"state": "complete", "applied_frames": 89}
        def snapshot(*_):
            self.fail("no RAM snapshots in visual-first mode")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "RAW-PRIVATE.jsonl"
            report = run_session(object(), raw_path=path,
                pre_samples=2, post_samples=2, settled_samples=2,
                interval=0.0, input_fn=get_response, swing_fn=swing,
                snapshot_fn=snapshot, visual_first=True)
            self.assertFalse(path.exists())
        human = report["human_observation"]
        self.assertEqual(events[:4], ["prompt", "prompt", "swing", "prompt"])
        self.assertEqual(human["finished_on_green_human"], "yes")
        self.assertTrue(human["terminal_screen_seen_before_transition_human"])
        self.assertEqual(human["displayed_distance_human"], 15.2)
        self.assertEqual(human["displayed_distance_source"], "ongreen_display_human")
        self.assertEqual(human["contact_human"], "yes")
        self.assertFalse(report["raw_data_created"])
        self.assertIsNone(report["candidate_ranking"])
        self.assertFalse(human["game_distance_verified_by_memory"])

    def test_fixed_offgreen_display_is_censored_not_physical_distance(self):
        response = _visual_first_label(lambda _: "M:100ft")
        self.assertEqual(response["displayed_distance_human"], 100.0)
        self.assertEqual(response["displayed_distance_source"], "offgreen_100ft_penalty")
        self.assertEqual(response["finished_on_green_human"], "no")
        self.assertFalse(response["game_distance_verified_by_memory"])

    def test_transition_and_unknown_abstain(self):
        no_screen = _visual_first_label(lambda _: "T")
        self.assertIs(no_screen["terminal_screen_seen_before_transition_human"], False)
        self.assertIsNone(no_screen["displayed_distance_human"])
        self.assertEqual(no_screen["finished_on_green_human"], "unknown")
        unsure = _visual_first_label(lambda _: "U")
        self.assertIsNone(unsure["terminal_screen_seen_before_transition_human"])
        self.assertEqual(unsure["finished_on_green_human"], "unknown")

    def test_invalid_entry_retries_and_cancel_aborts(self):
        answers = iter(["G:nonsense", "M:100ft"])
        self.assertEqual(_visual_first_label(lambda _: next(answers))[
            "displayed_distance_source"], "offgreen_100ft_penalty")
        with self.assertRaisesRegex(RuntimeError, "canceled"):
            _visual_first_label(lambda _: "q")

    def test_pre_shot_cancel_never_dispatches_or_creates_raw(self):
        answers = iter(["", "q"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "RAW.jsonl"
            out = run_session(object(), raw_path=path, pre_samples=2,
                post_samples=2, settled_samples=2, interval=0,
                visual_first=True, input_fn=lambda _: next(answers),
                swing_fn=lambda _: self.fail("shot must not dispatch"),
                snapshot_fn=lambda *_: self.fail("no RAM expected"))
            self.assertTrue(out["cancelled"])
            self.assertFalse(out["shot_dispatched"])
            self.assertFalse(out["raw_data_created"])
            self.assertFalse(path.exists())


class VisualFirstJoinTests(unittest.TestCase):
    def _check(self, data, *, expect_ok=True, use_token=TOKEN):
        with tempfile.TemporaryDirectory() as directory:
            caps = Path(directory)
            target = caps / f"outcome-{TOKEN}-candidates.json"
            target.write_text(json.dumps(data), encoding="utf-8")
            with patch.object(research_cli, "CAPTURES", caps):
                joined = research_cli._joined_visual_first(
                    use_token, datetime.now(timezone.utc) - timedelta(seconds=3),
                    a_lead=45, speed=1.0, backswing=1.0)
        self.assertEqual(joined["capture_status"] == "visual_first_joined", expect_ok)
        return joined

    def test_exact_token_join_strips_raw_and_preserves_censor_and_trace(self):
        result = self._check(child_summary())
        rendered = json.dumps(result)
        self.assertNotIn("MUST_NOT_PUBLISH", rendered)
        self.assertNotIn("private_sensitive_ram", rendered)
        self.assertTrue(result["shot_dispatch_verified_by_collector"])
        self.assertFalse(result["physical_distance_verified"])
        self.assertFalse(result["verified_game_score"])
        self.assertEqual(result["human"]["displayed_distance_source"],
                         "offgreen_100ft_penalty")
        self.assertEqual(result["controller"]["trace_sha256"], "a" * 64)
        self.assertEqual(result["human"]["initial_club_pose_human"], "back")
        self.assertEqual(result["human"]["displayed_power_percent_human"], 75.0)
        self.assertEqual(result["human"]["shot_start_bridge_tick_before_trace"], 120)

    def test_exact_token_mismatch_fails_closed(self):
        data = child_summary()
        data["run_token"] = "20261028T220000Z-deadbeef00"
        self._check(data, expect_ok=False)
        self._check(child_summary(), use_token="20261028T220000Z-feedfeed00",
                    expect_ok=False)

    def test_wrong_action_settings_or_incomplete_dispatch_fail_closed(self):
        for key, bad in (
            ("speed_scale", 0.8),
            ("backswing_scale", 1.2),
            ("a_lead_requested_frames", 0),
            ("a_lead_observed_frame_delta", 44),
            ("generated_trace_frames", 88),
            ("trace_sha256", "not-a-hash"),
        ):
            with self.subTest(key=key):
                data = child_summary()
                data["known_good_swing_request"][key] = bad
                self._check(data, expect_ok=False)
        for key, value in (("state", "scheduled"), ("applied_frames", 88)):
            with self.subTest(key=key):
                data = child_summary()
                data["swing_dispatch"][key] = value
                self._check(data, expect_ok=False)

    def test_unreviewed_numeric_ram_or_human_schema_fails_closed(self):
        mutations = (
            lambda x: x.__setitem__("raw_data_created", True),
            lambda x: x.__setitem__("candidate_ranking", {"value": 100}),
            lambda x: x["human_observation"].__setitem__(
                "displayed_distance_human", "PRIVATE_PLAYER_ADDRESS"),
            lambda x: x["human_observation"].__setitem__(
                "visible_result_class_human", "actual_game_verified"),
            lambda x: x["human_observation"].__setitem__(
                "game_distance_verified_by_memory", True),
            lambda x: x["human_observation"].__setitem__(
                "terminal_screen_seen_before_transition_human", 1),
            lambda x: x["human_observation"].__setitem__(
                "displayed_power_percent_human", "SECRET_WORDS"),
            lambda x: x["human_observation"].__setitem__(
                "initial_club_pose_human", "FORGED"),
            lambda x: x["human_observation"].__setitem__(
                "shot_start_frame_before_controller_trace", True),
            lambda x: x.__setitem__("settled_screen_observation", {"private": 123}),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                data = deepcopy(child_summary())
                mutate(data)
                self._check(data, expect_ok=False)

    def test_not_seen_before_transition_remains_unknown(self):
        data = child_summary()
        data["human_observation"].update({
            "finished_on_green_human": "unknown",
            "terminal_screen_seen_before_transition_human": False,
            "visible_result_class_human": "transitioned",
            "displayed_distance_human": None,
            "displayed_unit_human": "not-visible",
            "displayed_distance_source": "unseen_or_not_recorded",
        })
        data["settled_screen_observation"] = "human_terminal_unseen_or_unknown"
        joined = self._check(data)
        self.assertIsNone(joined["human"]["displayed_distance_human"])
        self.assertFalse(joined["human"]["terminal_screen_seen_before_transition_human"])

    def test_unregistered_visual_first_settings_refused_before_launch(self):
        # Fabricated only: reject a run that the B1/B2/X1 protocol cannot compare.
        from wii_ai_golf.lab.github_sync import SyncReport
        bad = (
            ("--a-lead", "0"),
            ("--a-lead", "44"),
            ("--a-lead", "46"),
            ("--a-lead", "45", "--speed-scale", "0.9"),
            ("--a-lead", "45", "--backswing-scale", "0.8"),
        )
        with patch.object(research_cli, "sync_merged_main",
                          return_value=SyncReport("up_to_date")), \
             patch.object(research_cli, "_run") as launch:
            for settings in bad:
                with self.subTest(settings=settings), self.assertRaises(SystemExit) as outcome:
                    research_cli.main(["v1", "--live", "--visual-first", "--no-upload",
                                       *settings])
                self.assertEqual(outcome.exception.code, 2)
            launch.assert_not_called()

    def test_preregistered_visual_first_variants_reach_mock_launcher(self):
        # Positive controls for B1/B2 and X1; mock launch still returns nonzero.
        from wii_ai_golf.lab.github_sync import SyncReport
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(research_cli, "sync_merged_main",
                              return_value=SyncReport("up_to_date")), \
                 patch.object(research_cli, "DATA", Path(directory)), \
                 patch.object(research_cli, "_run", return_value=4) as launch, \
                 patch.object(research_cli, "publish_summary") as publish, \
                 patch("wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                       return_value={"revision": "V1-neutral-swing-calls",
                                     "safe_for_isolated_legacy_copy": True}):
                for backswing in ("1.0", "1.2"):
                    result = research_cli.main([
                        "v1", "--live", "--visual-first", "--no-upload",
                        "--a-lead", "45", "--speed-scale", "1.0",
                        "--backswing-scale", backswing])
                    self.assertEqual(result, 4)
                self.assertEqual(launch.call_count, 2)
                publish.assert_not_called()

    def test_child_nonzero_prevents_publication_and_fallback(self):
        from wii_ai_golf.lab.github_sync import SyncReport
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(research_cli, "sync_merged_main",
                              return_value=SyncReport("up_to_date")), \
                 patch.object(research_cli, "DATA", Path(directory)), \
                 patch.object(research_cli, "_run", return_value=4), \
                 patch.object(research_cli, "_fresh_human_labels") as stale, \
                 patch.object(research_cli, "_fallback_human_observation") as fallback, \
                 patch.object(research_cli, "_joined_visual_first") as join, \
                 patch.object(research_cli, "publish_summary") as publish, \
                 patch("wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                       return_value={"revision": "V1-neutral-swing-calls",
                                     "safe_for_isolated_legacy_copy": True}):
                result = research_cli.main(["v1", "--live", "--a-lead", "45",
                                            "--visual-first"])
                self.assertEqual(result, 4)
                stale.assert_not_called()
                fallback.assert_not_called()
                join.assert_not_called()
                publish.assert_not_called()
                records = list((Path(directory) / "research-cli").glob("*.json"))
                self.assertEqual(len(records), 1)
                status = json.loads(records[0].read_text())
                self.assertEqual(status["capture_status"], "failed_or_cancelled_action")
                self.assertFalse(status["shot_dispatch_verified_by_collector"])

    def test_malicious_legacy_nested_screen_label_not_published(self):
        with tempfile.TemporaryDirectory() as directory:
            caps = Path(directory)
            record = {
                "source": "live-emulator-read-only-US-Rev1+human-result-label",
                "human_observation": {},
                "known_good_swing_request": {},
                "settled_screen_observation": {
                    "private_ram": "MUST_NOT_PUBLISH"
                },
            }
            (caps / "outcome-fake-candidates.json").write_text(json.dumps(record))
            with patch.object(research_cli, "CAPTURES", caps):
                result = research_cli._fresh_human_labels(
                    datetime.now(timezone.utc) - timedelta(seconds=5))
            self.assertEqual(result["settled_screen_observation"], "unknown")
            self.assertNotIn("MUST_NOT_PUBLISH", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
