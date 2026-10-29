"""M1.5 visual outcome first: purely fabricated controls, never launch Dolphin."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for part in (str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")):
    if part not in sys.path:
        sys.path.insert(0, part)

from scripts.collect_outcome_transition import (
    _build_v1_trace_and_digest, _visual_first_label, run_session)
import research_cli

TOKEN = "20261028T220000Z-0123456789"


def child_summary():
    return {
        "run_token": TOKEN,
        "source": "human-terminal-result-no-ram-game-context-unverified",
        "outcome_collection_mode": "human_terminal_first_no_ram",
        "raw_data_created": False,
        "candidate_ranking": None,
        "swing_dispatch": {"state": "complete", "applied_frames": 89},
        "known_good_swing_request": {
            "preset": "forward", "generated_trace_frames": 89,
            "trace_sha256": _build_v1_trace_and_digest(
                motion_scale=1.0, speed_scale=1.0, backswing_scale=1.0)[1],
            "motion_scale": 1.0,
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
            "hitting_green_first_ball_context_human_confirmed": True,
            "game_context_verified_by_memory": False,
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
        self.assertTrue(human["hitting_green_first_ball_context_human_confirmed"])
        self.assertFalse(human["game_context_verified_by_memory"])
        self.assertEqual(report["source"],
                         "human-terminal-result-no-ram-game-context-unverified")

    def test_setup_narrative_reprompts_and_only_explicit_enter_dispatches(self):
        # Reproduces the operator's aborted B1: a descriptive setup sentence
        # must not be silently interpreted as q or as permission to swing.
        replies = iter([
            "We are at the starting position, with 0 wind and aligned aim",
            "",  # explicit ready confirmation
            "The club is around halfway back",
            "",  # separate explicit swing permission
            "M:100ft", "yes",
        ])
        prompts = []
        swings = []
        def answer(prompt):
            prompts.append(prompt)
            return next(replies)
        def swing(_rpc):
            swings.append("one")
            return {"state": "complete", "applied_frames": 89}
        with tempfile.TemporaryDirectory() as folder:
            private = Path(folder) / "RAW-PRIVATE.jsonl"
            result = run_session(object(), raw_path=private, pre_samples=2,
                post_samples=2, settled_samples=2, interval=0,
                input_fn=answer, swing_fn=swing, visual_first=True,
                snapshot_fn=lambda *_: self.fail("visual-first may not sample RAM"))
            self.assertFalse(private.exists())
        self.assertEqual(swings, ["one"])
        self.assertEqual(len(prompts), 6)
        self.assertEqual(prompts[0], prompts[1])
        self.assertEqual(prompts[2], prompts[3])
        self.assertFalse(result.get("cancelled", False))
        self.assertTrue(result["human_observation"]["terminal_screen_seen_before_transition_human"])
        self.assertEqual(result["human_observation"]["contact_human"], "yes")

    def test_invalid_setup_text_then_q_never_dispatches(self):
        for replies in (
            ["A is not pressed; pin appears far away", "Q"],
            ["", "A is not pressed; pin appears far away", " q "],
        ):
            with self.subTest(replies=replies), tempfile.TemporaryDirectory() as folder:
                raw = Path(folder) / "RAW-PRIVATE.jsonl"
                answers = iter(replies)
                result = run_session(object(), raw_path=raw, pre_samples=2,
                    post_samples=2, settled_samples=2, interval=0,
                    visual_first=True, input_fn=lambda _: next(answers),
                    swing_fn=lambda _: self.fail("no explicit swing approval"),
                    snapshot_fn=lambda *_: self.fail("no RAM sampling"))
                self.assertTrue(result["cancelled"])
                self.assertFalse(result["raw_data_created"])
                self.assertFalse(raw.exists())

    def test_a45_receipt_records_46_button_requests_not_one(self):
        # The actual helper issues one initial A plus one per observed tick.
        # A completed 89-sample trace does NOT prove A game-side recognition.
        replies = iter(["", "", "U", "no"])
        with tempfile.TemporaryDirectory() as folder:
            private = Path(folder) / "RAW-PRIVATE.jsonl"
            with patch("scripts.collect_outcome_transition.hold_a_for_observed_frames") as hold, \
                 patch("scripts.collect_outcome_transition.SwingTraceClient") as trace, \
                 patch("scripts.collect_outcome_transition.release_buttons") as release:
                hold.return_value = {
                    "a_button_only_requests": 46,
                    "per_observed_frame_a_reasserted": True,
                    "observed_frame_delta": 45,
                    "start_frame_after_a_request": 100,
                    "last_observed_frame": 145,
                    "game_a_recognition_verified": False,
                }
                trace.return_value.run.return_value = {
                    "state": "complete", "applied_frames": 89,
                }
                result = run_session(object(), raw_path=private,
                    pre_samples=2, post_samples=2, settled_samples=2,
                    interval=0, visual_first=True, a_lead_frames=45,
                    input_fn=lambda _: next(replies),
                    snapshot_fn=lambda *_: self.fail("visual-first must not sample RAM"))
                hold.assert_called_once()
                release.assert_called_once()
                self.assertFalse(private.exists())
        req = result["known_good_swing_request"]
        self.assertEqual(req["a_lead_requested_frames"], 45)
        self.assertEqual(req["a_lead_observed_frame_delta"], 45)
        self.assertEqual(req["a_button_only_prime_requests"], 46)
        self.assertTrue(req["a_lead_per_observed_frame_reasserted"])
        self.assertIn("not_game_verified", req["a_priming_evidence"])
        self.assertEqual(result["human_observation"]["contact_human"], "no")
        self.assertFalse(result["raw_data_created"])

    def test_atomic_a45_success_one_swing_and_bridge_receipt_no_ram(self):
        replies = iter(["", "", "U", "no"])
        with tempfile.TemporaryDirectory() as folder:
            private = Path(folder) / "RAW-PRIVATE.jsonl"
            with patch("scripts.collect_outcome_transition.AtomicA45SwingTraceClient") as client, \
                 patch("scripts.collect_outcome_transition.hold_a_for_observed_frames") as poll, \
                 patch("scripts.collect_outcome_transition.release_buttons") as release:
                client.return_value.run.return_value = {
                    "state": "complete", "id": 1, "kind": "atomic_a45_swing",
                    "applied_frames": 89, "prehold_applied_frames": 45,
                    "prehold_start_frame": 100,
                    "last_prehold_frame": 144, "trace_start_frame": 145,
                    "game_a_recognition_verified": False,
                }
                result = run_session(object(), raw_path=private,
                    pre_samples=2, post_samples=2, settled_samples=2,
                    interval=0, visual_first=True, atomic_a45=True,
                    a_lead_frames=45, input_fn=lambda _: next(replies),
                    snapshot_fn=lambda *_: self.fail("no RAM in M1.5"))
                self.assertEqual(client.return_value.run.call_count, 1)
                poll.assert_not_called()
                release.assert_called_once()
                self.assertFalse(private.exists())
        req = result["known_good_swing_request"]
        self.assertEqual(req["a_lead_requested_frames"], 45)
        self.assertEqual(req["a_lead_observed_frame_delta"], 45)
        self.assertEqual(req["a_button_only_prime_requests"], 0)
        self.assertTrue(req["a_lead_atomic_bridge_callback"])
        self.assertEqual(req["a_lead_bridge_button_dispatch_frames"], 45)
        self.assertFalse(req["a_lead_per_observed_frame_reasserted"])
        self.assertEqual(req["generated_trace_frames"], 89)
        self.assertEqual(result["human_observation"]["contact_human"], "no")

    def test_atomic_a45_preflight_failure_has_no_swing_and_releases(self):
        replies = iter(["", ""])
        with tempfile.TemporaryDirectory() as folder:
            with patch("scripts.collect_outcome_transition.AtomicA45SwingTraceClient") as client, \
                 patch("scripts.collect_outcome_transition.release_buttons") as release:
                client.return_value.run.side_effect = RuntimeError("missing capability")
                with self.assertRaisesRegex(RuntimeError, "missing capability"):
                    run_session(object(), raw_path=Path(folder) / "RAW.jsonl",
                        pre_samples=2, post_samples=2, settled_samples=2,
                        interval=0, visual_first=True, atomic_a45=True,
                        a_lead_frames=45, input_fn=lambda _: next(replies))
                release.assert_called_once()

    def test_atomic_a45_invalid_optin_rejected_before_any_controller_input(self):
        with self.assertRaisesRegex(ValueError, "atomic A45 requires"):
            run_session(object(), raw_path=Path("unused.jsonl"),
                        pre_samples=2, post_samples=2, settled_samples=2,
                        interval=0, atomic_a45=True, a_lead_frames=12,
                        visual_first=True,
                        input_fn=lambda _: self.fail("must not prompt"))

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
    def _check(self, data, *, expect_ok=True, use_token=TOKEN, backswing=1.0):
        with tempfile.TemporaryDirectory() as directory:
            caps = Path(directory)
            target = caps / f"outcome-{TOKEN}-candidates.json"
            target.write_text(json.dumps(data), encoding="utf-8")
            with patch.object(research_cli, "CAPTURES", caps):
                joined = research_cli._joined_visual_first(
                    use_token, datetime.now(timezone.utc) - timedelta(seconds=3),
                    a_lead=45, speed=1.0, backswing=backswing)
        self.assertEqual(joined["capture_status"] == "visual_first_joined", expect_ok)
        return joined

    def test_atomic_a45_join_requires_exact_callback_receipt(self):
        report = child_summary()
        report["known_good_swing_request"].update({
            "a_lead_atomic_bridge_callback": True,
            "a_lead_bridge_button_dispatch_frames": 45,
            "a_button_only_prime_requests": 0,
        })
        report["swing_dispatch"].update({
            "kind": "atomic_a45_swing",
            "prehold_applied_frames": 45,
            "game_a_recognition_verified": False,
        })
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / f"outcome-{TOKEN}-candidates.json"
            with patch.object(research_cli, "CAPTURES", Path(folder)):
                def join(data):
                    target.write_text(json.dumps(data), encoding="utf-8")
                    return research_cli._joined_visual_first(
                        TOKEN, datetime.now(timezone.utc) - timedelta(seconds=2),
                        a_lead=45, speed=1.0, backswing=1.0, atomic_a45=True)
                good = join(report)
                self.assertEqual(good["capture_status"], "visual_first_joined")
                self.assertEqual(good["controller"]["a_lead_bridge_button_dispatch_frames"], 45)
                self.assertFalse(good["train_approved"])
                for mutate in (
                    ("a_lead_bridge_button_dispatch_frames", 44),
                    ("a_lead_atomic_bridge_callback", False),
                    ("a_button_only_prime_requests", 1),
                ):
                    with self.subTest(mutate=mutate):
                        bad = deepcopy(report)
                        bad["known_good_swing_request"][mutate[0]] = mutate[1]
                        self.assertEqual(join(bad)["capture_status"], "visual_first_join_refused")
                bad_status = deepcopy(report)
                bad_status["swing_dispatch"]["prehold_applied_frames"] = 44
                self.assertEqual(join(bad_status)["capture_status"], "visual_first_join_refused")
                self.assertEqual(join(child_summary())["capture_status"], "visual_first_join_refused")

    def test_exact_run_token_allows_bounded_mtime_granularity_not_stale_files(self):
        # Windows temp-file metadata may round slightly before the parent's
        # high-resolution datetime; exact token+trace validation still applies.
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / f"outcome-{TOKEN}-candidates.json"
            path.write_text(json.dumps(child_summary()), encoding="utf-8")
            now = datetime.now(timezone.utc)
            with patch.object(research_cli, "CAPTURES", folder):
                os.utime(path, (now.timestamp() - 0.5, now.timestamp() - 0.5))
                recent = research_cli._joined_visual_first(
                    TOKEN, now, a_lead=45, speed=1.0, backswing=1.0)
                self.assertEqual(recent["capture_status"], "visual_first_joined")
                os.utime(path, (now.timestamp() - 10, now.timestamp() - 10))
                stale = research_cli._joined_visual_first(
                    TOKEN, now, a_lead=45, speed=1.0, backswing=1.0)
                self.assertEqual(stale["capture_status"], "visual_first_join_refused")

    def test_exact_token_join_strips_raw_and_preserves_censor_and_trace(self):
        result = self._check(child_summary())
        rendered = json.dumps(result)
        self.assertNotIn("MUST_NOT_PUBLISH", rendered)
        self.assertNotIn("private_sensitive_ram", rendered)
        self.assertTrue(result["shot_dispatch_verified_by_collector"])
        self.assertFalse(result["physical_distance_verified"])
        self.assertFalse(result["verified_game_score"])
        self.assertTrue(result["outcome_is_censored_penalty"])
        self.assertFalse(result["numeric_distance_target_eligible"])
        self.assertFalse(result["train_approved"])
        self.assertEqual(result["human"]["displayed_distance_source"],
                         "offgreen_100ft_penalty")
        self.assertEqual(result["controller"]["trace_sha256"],
                         child_summary()["known_good_swing_request"]["trace_sha256"])
        self.assertTrue(result["informative_action_outcome_trial"])
        self.assertFalse(result["game_id_revision_mode_machine_verified"])
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
            ("trace_sha256", "b" * 64),
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

    def test_deterministic_waveform_identity_baseline_and_1p2(self):
        baseline = child_summary()
        self.assertTrue(self._check(baseline)["informative_action_outcome_trial"])
        changed = child_summary()
        changed["known_good_swing_request"]["backswing_scale"] = 1.2
        changed["known_good_swing_request"]["trace_sha256"] = (
            _build_v1_trace_and_digest(motion_scale=1.0, speed_scale=1.0,
                                      backswing_scale=1.2)[1])
        self.assertNotEqual(baseline["known_good_swing_request"]["trace_sha256"],
                            changed["known_good_swing_request"]["trace_sha256"])
        self._check(changed, backswing=1.2)
        wrong = deepcopy(changed)
        wrong["known_good_swing_request"]["trace_sha256"] = (
            baseline["known_good_swing_request"]["trace_sha256"])
        self._check(wrong, backswing=1.2, expect_ok=False)

    def test_human_source_and_category_pair_fails_closed(self):
        for key, bad in (
            ("source", "live-emulator-read-only-US-Rev1+human-result-label"),
            ("source", "machine-verified-game-context"),
        ):
            data = child_summary()
            data[key] = bad
            self._check(data, expect_ok=False)
        for field, bad in (
            ("hitting_green_first_ball_context_human_confirmed", False),
            ("game_context_verified_by_memory", True),
        ):
            data = child_summary()
            data["human_observation"][field] = bad
            self._check(data, expect_ok=False)
        for kind, green, source, value in (
            ("green", "yes", "offgreen_display_unverified", 3.2),
            ("offgreen", "no", "ongreen_display_human", 100.0),
            ("uncertain", "unknown", "offgreen_display_unverified", None),
        ):
            data = child_summary()
            data["human_observation"].update({
                "visible_result_class_human": kind,
                "finished_on_green_human": green,
                "displayed_distance_source": source,
                "displayed_distance_human": value,
            })
            if kind == "uncertain":
                data["human_observation"].update({
                    "terminal_screen_seen_before_transition_human": None,
                    "displayed_unit_human": "not-visible",
                })
                data["settled_screen_observation"] = "human_terminal_unseen_or_unknown"
            self._check(data, expect_ok=False)

    def test_no_or_unknown_contact_is_ineligible_for_outcome_comparison(self):
        for contact in ("no", "unknown"):
            with self.subTest(contact=contact):
                data = child_summary()
                data["human_observation"]["contact_human"] = contact
                result = self._check(data)
                self.assertFalse(result["informative_action_outcome_trial"])
                self.assertFalse(result["verified_game_score"])

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
        self.assertFalse(joined["outcome_is_censored_penalty"])
        self.assertFalse(joined["informative_action_outcome_trial"])

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
                 patch.object(research_cli, "v1_clean_boot_args", return_value=["--dolphin", "MOCK-CLEAN-EXE", "--dolphin-user", "MOCK-CLEAN-USER", "--config", "MOCK-LOCAL-CONFIG", "--catalog", "MOCK-LOCAL-CATALOG"]), \
                 patch.object(research_cli, "publish_summary") as publish, \
                 patch("wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                       return_value={"revision": "V1-neutral-swing-calls",
                                     "safe_for_isolated_legacy_copy": True,
                                     "sha256": "a" * 64}):
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
                 patch.object(research_cli, "v1_clean_boot_args", return_value=["--dolphin", "MOCK-CLEAN-EXE", "--dolphin-user", "MOCK-CLEAN-USER", "--config", "MOCK-LOCAL-CONFIG", "--catalog", "MOCK-LOCAL-CATALOG"]), \
                 patch.object(research_cli, "_fresh_human_labels") as stale, \
                 patch.object(research_cli, "_fallback_human_observation") as fallback, \
                 patch.object(research_cli, "_joined_visual_first") as join, \
                 patch.object(research_cli, "publish_summary") as publish, \
                 patch("wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                       return_value={"revision": "V1-neutral-swing-calls",
                                     "safe_for_isolated_legacy_copy": True,
                                     "sha256": "a" * 64}):
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

    def test_mocked_positive_b1_run_joins_exact_child_and_stays_local(self):
        """End-to-end synthetic parent/child handshake; no emulator or upload."""
        from wii_ai_golf.lab.github_sync import SyncReport

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            captures = root / "captures"
            captures.mkdir()
            action_commands = []

            def fake_runner(argv, **_kwargs):
                action_commands.append(list(argv))
                self.assertEqual(argv.count("--send-live"), 1)
                self.assertEqual(argv.count("--send-live-swing"), 1)
                token = argv[argv.index("--run-token") + 1]
                child = child_summary()
                child["run_token"] = token
                # The child's private mock payload must never reach publication.
                (captures / f"outcome-{token}-candidates.json").write_text(
                    json.dumps(child), encoding="utf-8")
                return 0

            with patch.object(research_cli, "sync_merged_main",
                              return_value=SyncReport("up_to_date")), \
                 patch.object(research_cli, "DATA", root), \
                 patch.object(research_cli, "CAPTURES", captures), \
                 patch.object(research_cli, "_head", return_value="mocked-head"), \
                 patch.object(research_cli, "v1_clean_boot_args",
                              return_value=["--dolphin", "MOCK_CLEAN_DOLPHIN",
                                            "--dolphin-user", "MOCK_CLEAN_USER"]), \
                 patch.object(research_cli, "_run", side_effect=fake_runner), \
                 patch.object(research_cli, "_fallback_human_observation") as fallback, \
                 patch.object(research_cli, "publish_summary") as publish, \
                 patch("wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                       return_value={"revision": "V1-neutral-swing-calls",
                                     "safe_for_isolated_legacy_copy": True,
                                     "sha256": "a" * 64}):
                code = research_cli.main([
                    "v1", "--live", "--visual-first", "--no-upload",
                    "--a-lead", "45", "--speed-scale", "1.0",
                    "--backswing-scale", "1.0"])
                self.assertEqual(code, 0)
                fallback.assert_not_called()
                publish.assert_not_called()

            self.assertEqual(len(action_commands), 1)
            self.assertIn("MOCK_CLEAN_DOLPHIN", action_commands[0])
            self.assertIn("--visual-first", action_commands[0])
            self.assertNotIn("--no-upload", action_commands[0])
            records = list((root / "research-cli").glob("*.json"))
            self.assertEqual(len(records), 1)
            saved = json.loads(records[0].read_text(encoding="utf-8"))
            self.assertEqual(saved["capture_status"], "visual_first_joined")
            self.assertEqual(saved["process_exit_code"], 0)
            self.assertTrue(saved["informative_action_outcome_trial"])
            self.assertTrue(saved["outcome_is_censored_penalty"])
            self.assertFalse(saved["numeric_distance_target_eligible"])
            self.assertFalse(saved["train_approved"])
            self.assertEqual(saved["id"],
                             action_commands[0][action_commands[0].index("--run-token") + 1])
            self.assertNotIn("MUST_NOT_PUBLISH", json.dumps(saved))
            self.assertNotIn("candidate_other_private_data", json.dumps(saved))

    def test_uninformative_valid_attempt_stays_local_and_unpublished(self):
        from wii_ai_golf.lab.github_sync import SyncReport
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(research_cli, "sync_merged_main",
                              return_value=SyncReport("up_to_date")), \
                 patch.object(research_cli, "DATA", Path(directory)), \
                 patch.object(research_cli, "_run", return_value=0), \
                 patch.object(research_cli, "v1_clean_boot_args", return_value=["--dolphin", "MOCK-CLEAN-EXE", "--dolphin-user", "MOCK-CLEAN-USER", "--config", "MOCK-LOCAL-CONFIG", "--catalog", "MOCK-LOCAL-CATALOG"]), \
                 patch.object(research_cli, "_joined_visual_first",
                              return_value={"capture_status": "visual_first_joined",
                                            "informative_action_outcome_trial": False,
                                            "human": {"contact_human": "unknown"}}), \
                 patch.object(research_cli, "publish_summary") as publish, \
                 patch("wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                       return_value={"revision": "V1-neutral-swing-calls",
                                     "safe_for_isolated_legacy_copy": True,
                                     "sha256": "a" * 64}):
                code = research_cli.main(["v1", "--live", "--a-lead", "45",
                                          "--visual-first"])
                self.assertEqual(code, 2)
                publish.assert_not_called()
                records = list((Path(directory) / "research-cli").glob("*.json"))
                self.assertEqual(len(records), 1)
                saved = json.loads(records[0].read_text())
                self.assertFalse(saved["informative_action_outcome_trial"])

    def test_bridge_source_changed_during_action_quarantines_b1(self):
        """A source mutation during a synthetic completed action cannot pass B1."""
        from wii_ai_golf.lab.github_sync import SyncReport
        with tempfile.TemporaryDirectory() as directory:
            sandbox = Path(directory)
            checkout = sandbox / "checkout"
            checkout.mkdir()
            bridge = sandbox / "tools" / "mcp_bridge_swing_legacy_eval.py"
            bridge.parent.mkdir()
            original = (
                "# WII_AI_GOLF_ATOMIC_TRACE_V1\n"
                "# WII_AI_GOLF_SWING_TRACE_V1\n"
                "print('before')\n"
            )
            bridge.write_text(original, encoding="utf-8")
            runner_calls = []

            def mutating_runner(argv, **_kwargs):
                runner_calls.append(list(argv))
                bridge.write_text(original + "# changed during action\n",
                                  encoding="utf-8")
                return 0

            with patch.object(research_cli, "ROOT", checkout), \
                 patch.object(research_cli, "DATA", sandbox / "data"), \
                 patch.object(research_cli, "sync_merged_main",
                              return_value=SyncReport("up_to_date")), \
                 patch.object(research_cli, "v1_clean_boot_args",
                              return_value=["--dolphin", "MOCK_CLEAN"]), \
                 patch.object(research_cli, "_run", side_effect=mutating_runner), \
                 patch.object(research_cli, "_joined_visual_first") as join, \
                 patch.object(research_cli, "publish_summary") as publish:
                code = research_cli.main([
                    "v1", "--live", "--visual-first", "--no-upload",
                    "--a-lead", "45", "--speed-scale", "1.0",
                    "--backswing-scale", "1.0",
                ])
            self.assertEqual(code, 2)
            self.assertEqual(len(runner_calls), 1)
            join.assert_not_called()
            publish.assert_not_called()
            summaries = list((sandbox / "data" / "research-cli").glob("*.json"))
            self.assertEqual(len(summaries), 1)
            saved = json.loads(summaries[0].read_text(encoding="utf-8"))
            self.assertEqual(saved["capture_status"],
                             "unqualified_bridge_source_change")
            self.assertTrue(saved["bridge_source_changed_during_action"])
            self.assertFalse(saved["informative_action_outcome_trial"])
            self.assertFalse(saved["train_approved"])

    def test_missing_bridge_source_digest_prevents_b1_launch(self):
        from wii_ai_golf.lab.github_sync import SyncReport
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(research_cli, "DATA", Path(directory)), \
             patch.object(research_cli, "sync_merged_main",
                          return_value=SyncReport("up_to_date")), \
             patch("wii_ai_golf.shared.bridge_provenance.inspect_bridge_file",
                   return_value={"revision": "V1-neutral-swing-calls",
                                 "safe_for_isolated_legacy_copy": True}), \
             patch.object(research_cli, "_run") as runner:
            code = research_cli.main(["v1", "--live", "--visual-first",
                                      "--no-upload", "--a-lead", "45"])
            self.assertEqual(code, 2)
            runner.assert_not_called()

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
