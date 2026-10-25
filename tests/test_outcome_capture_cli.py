"""Mocked capture lifecycle tests: no emulator, no user files."""
from pathlib import Path
import struct
from unittest.mock import patch
import sys
import tempfile
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
for item in (str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")):
    if item in sys.path:
        sys.path.remove(item)
    sys.path.insert(0, item)
from scripts.collect_outcome_transition import run_session
from scripts.probe_swing import build_probe


def row(phase, value):
    return {"game_id": "RSPE01", "disc_revision": 1, "phase": phase,
            "frame_start": 1, "frame_end": 2,
            "windows": {"golf_config": {"address": "0x90010000",
                                       "bytes_hex": struct.pack(">I", value).hex()}}}


class OutcomeCaptureCliTests(unittest.TestCase):
    def test_one_swing_between_pre_and_post(self):
        got = []
        answers = iter(["", "", "", "yes", "yes", "12.5", "yd"])
        f32_bits = struct.unpack(">I", struct.pack(">f", 12.5))[0]

        def snapshot(_rpc, phase):
            got.append(phase)
            return row(phase, {"pre": 0, "post": 1, "settled": f32_bits}[phase])

        def swing(_rpc):
            got.append("swing")
            return {"state": "complete", "applied_frames": 89}

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "RAW.jsonl"
            result = run_session(object(), raw_path=path, pre_samples=2,
                post_samples=2, settled_samples=2, interval=0,
                input_fn=lambda q: next(answers), sleep_fn=lambda s: None,
                snapshot_fn=snapshot, swing_fn=swing)
            self.assertEqual(got,
                ["pre", "pre", "swing", "post", "post", "settled", "settled"])
            self.assertEqual(result["candidate_ranking"]["all_phase_stable_change_count"], 1)
            self.assertEqual(result["human_observation"]["displayed_distance_human"], 12.5)
            self.assertEqual(result["known_good_swing_request"]["generated_trace_frames"],
                             len(build_probe("forward", follow_through_frames=30)))
            self.assertFalse(result["candidate_ranking"]["game_score_verified"])
            self.assertEqual(len(path.read_text().splitlines()), 6)

    def test_v1_observation_records_pose_and_frame_without_changing_swing(self):
        prompts = []
        replies = iter(["", "back", "", "", "yes", "no", "100ft"])
        class RPC:
            def call(self, method, args):
                self_method = method
                if self_method == "frame.get_count":
                    return 1234
                raise AssertionError("unexpected controller request")
        def user_input(prompt):
            prompts.append(prompt)
            return next(replies)
        with tempfile.TemporaryDirectory() as d:
            result = run_session(RPC(), raw_path=Path(d) / "RAW.jsonl",
                pre_samples=2, post_samples=2, settled_samples=2,
                interval=0, observe_start_pose=True,
                input_fn=user_input,
                snapshot_fn=lambda _r, phase: row(phase, {"pre": 0, "post": 2, "settled": 1}[phase]),
                swing_fn=lambda _r: {"state": "complete"})
        observed = result["human_observation"]
        self.assertEqual(observed["initial_club_pose_human"], "back")
        self.assertFalse(observed["initial_club_pose_verified_by_memory"])
        self.assertEqual(observed["shot_start_frame_before_controller_trace"], 1234)
        self.assertTrue(any("initial club position" in p for p in prompts))
        self.assertEqual(observed["contact_human"], "yes")

    def test_distance_with_unit_suffix_does_not_ask_for_unit_again(self):
        prompts = []
        responses = iter(["", "", "", "yes", "no", "100.0ft"])
        def input_fn(prompt):
            prompts.append(prompt)
            return next(responses)
        with tempfile.TemporaryDirectory() as d:
            result = run_session(object(), raw_path=Path(d) / "RAW.jsonl",
                pre_samples=2, post_samples=2, settled_samples=2, interval=0,
                input_fn=input_fn,
                snapshot_fn=lambda _r, phase: row(phase, {"pre": 0, "post": 2, "settled": 1}[phase]),
                swing_fn=lambda _r: {"state": "complete"})
        self.assertEqual(result["human_observation"]["displayed_distance_human"], 100.0)
        self.assertEqual(result["human_observation"]["displayed_unit_human"], "ft")
        self.assertFalse(any("Displayed unit" in prompt for prompt in prompts))
        self.assertEqual(result["settled_screen_observation"], "operator_confirmed_before_transition")

    def test_invalid_distance_retries_after_preserving_all_samples(self):
        responses = iter(["", "", "", "yes", "no", "not-a-distance", "100.0ft"])
        with tempfile.TemporaryDirectory() as d:
            raw = Path(d) / "RAW.jsonl"
            result = run_session(object(), raw_path=raw, pre_samples=2,
                post_samples=2, settled_samples=2, interval=0,
                input_fn=lambda _q: next(responses),
                snapshot_fn=lambda _r, phase: row(phase, {"pre": 0, "post": 2, "settled": 1}[phase]),
                swing_fn=lambda _r: {"state": "complete"})
            self.assertEqual(len(raw.read_text().splitlines()), 6)
            self.assertEqual(result["human_observation"]["displayed_unit_human"], "ft")

    def test_transition_before_settled_prompt_is_marked_uncertain(self):
        responses = iter(["", "", "t", "yes", "no", "100ft"])
        with tempfile.TemporaryDirectory() as d:
            result = run_session(object(), raw_path=Path(d) / "RAW.jsonl",
                pre_samples=2, post_samples=2, settled_samples=2, interval=0,
                input_fn=lambda _q: next(responses),
                snapshot_fn=lambda _r, phase: row(phase, {"pre": 0, "post": 2, "settled": 1}[phase]),
                swing_fn=lambda _r: {"state": "complete"})
        self.assertEqual(result["settled_screen_observation"],
                         "screen_had_already_transitioned_before_settled_samples")
        self.assertFalse(result["candidate_ranking"]["game_score_verified"])

    def test_early_cancel_does_not_write_or_swing(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "RAW.jsonl"
            result = run_session(object(), raw_path=path, pre_samples=2,
                post_samples=2, settled_samples=2, interval=0,
                input_fn=lambda q: "q",
                swing_fn=lambda rpc: self.fail("must not swing"))
            self.assertTrue(result["cancelled"])
            self.assertFalse(path.exists())

    def test_cancel_after_baseline_saves_partial_without_swing(self):
        replies = iter(["", "q"])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "RAW.jsonl"
            result = run_session(object(), raw_path=path, pre_samples=2,
                post_samples=2, settled_samples=2, interval=0,
                input_fn=lambda q: next(replies),
                snapshot_fn=lambda rpc, phase: row(phase, 1),
                swing_fn=lambda rpc: self.fail("must not swing"))
            self.assertTrue(result["cancelled"])
            self.assertEqual(result["partial_samples"], 2)
            self.assertEqual(len(path.read_text().splitlines()), 2)

    def test_live_default_uses_only_trace_with_no_separate_a_prime(self):
        events = []
        answers = iter(["", "", "", "yes", "no", "100", "ft"])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "RAW.jsonl"
            with patch("scripts.collect_outcome_transition.prime_a_button") as prime, \
                 patch("scripts.collect_outcome_transition.SwingTraceClient") as client, \
                 patch("scripts.collect_outcome_transition.release_buttons") as release:
                def trace(samples):
                    events.append("trace")
                    return {"state": "complete", "applied_frames": len(samples)}
                client.return_value.run.side_effect = trace
                result = run_session(object(), raw_path=path, pre_samples=2,
                    post_samples=2, settled_samples=2, interval=0,
                    input_fn=lambda _q: next(answers),
                    snapshot_fn=lambda _r, phase: row(phase, {"pre": 0, "post": 1, "settled": 2}[phase]))
            self.assertEqual(events, ["trace"])
            prime.assert_not_called()
            release.assert_not_called()
            self.assertEqual(result["known_good_swing_request"]["a_button_only_prime_requests"], 0)
            self.assertFalse(result["known_good_swing_request"]["a_button_prime_applied"])
            self.assertEqual(len(result["known_good_swing_request"]["trace_sha256"]), 64)
            self.assertEqual(result["known_good_swing_request"]["generated_trace_frames"],
                             result["swing_dispatch"]["applied_frames"])

    def test_optional_60_a_prime_is_explicit_and_cleans_up(self):
        events = []
        answers = iter(["", "", "", "yes", "no", "100", "ft"])
        with tempfile.TemporaryDirectory() as d:
            with patch("scripts.collect_outcome_transition.prime_a_button") as prime, \
                 patch("scripts.collect_outcome_transition.SwingTraceClient") as client, \
                 patch("scripts.collect_outcome_transition.release_buttons") as release:
                prime.side_effect = lambda *_a, **_k: events.append("prime")
                client.return_value.run.side_effect = lambda samples: (
                    events.append("trace") or {"state": "complete", "applied_frames": len(samples)})
                release.side_effect = lambda *_a, **_k: events.append("release")
                result = run_session(object(), raw_path=Path(d) / "RAW.jsonl",
                    pre_samples=2, post_samples=2, settled_samples=2, interval=0,
                    a_prime_requests=60, input_fn=lambda _q: next(answers),
                    snapshot_fn=lambda _r, phase: row(phase, {"pre": 0, "post": 1, "settled": 2}[phase]))
            self.assertEqual(events, ["prime", "trace", "release"])
            self.assertEqual(prime.call_args.kwargs, {"remote": 0, "requests": 60})
            self.assertEqual(result["known_good_swing_request"]["a_button_only_prime_requests"], 60)
            self.assertTrue(result["known_good_swing_request"]["a_button_prime_applied"])

    def test_observed_a_lead_happens_before_unchanged_trace_and_cleans_up(self):
        events = []
        answers = iter(["", "", "", "yes", "no", "100.0ft"])
        with tempfile.TemporaryDirectory() as d:
            with patch("scripts.collect_outcome_transition.hold_a_for_observed_frames") as hold, \
                 patch("scripts.collect_outcome_transition.SwingTraceClient") as client, \
                 patch("scripts.collect_outcome_transition.release_buttons") as release, \
                 patch("scripts.collect_outcome_transition.prime_a_button") as old_prime:
                def hold_side_effect(_rpc, *, frames, remote):
                    self.assertEqual((frames, remote), (12, 0))
                    events.append("hold-a-observed-12")
                    return {"observed_frame_delta": 13, "start_frame_after_a_request": 120,
                            "last_observed_frame": 133}
                hold.side_effect = hold_side_effect
                def trace(samples):
                    events.append("trace-unchanged")
                    self.assertEqual(len(samples),
                                     len(build_probe("forward", follow_through_frames=30)))
                    return {"state": "complete", "applied_frames": len(samples)}
                client.return_value.run.side_effect = trace
                release.side_effect = lambda *_a, **_k: events.append("release")
                result = run_session(object(), raw_path=Path(d) / "RAW.jsonl",
                    pre_samples=2, post_samples=2, settled_samples=2, interval=0,
                    a_lead_frames=12, input_fn=lambda _q: next(answers),
                    snapshot_fn=lambda _r, phase: row(phase, {"pre": 0, "post": 1, "settled": 2}[phase]))
            self.assertEqual(events, ["hold-a-observed-12", "trace-unchanged", "release"])
            old_prime.assert_not_called()
            self.assertEqual(result["known_good_swing_request"]["a_lead_requested_frames"], 12)
            self.assertEqual(result["known_good_swing_request"]["a_lead_observed_frame_delta"], 13)
            self.assertEqual(result["known_good_swing_request"]["a_button_only_prime_requests"], 1)
            self.assertTrue(result["known_good_swing_request"]["a_button_prime_applied"])
            self.assertIn("not_game_verified", result["known_good_swing_request"]["a_priming_evidence"])

    def test_observed_a_lead_fails_before_motion_and_releases(self):
        answers = iter(["", ""])
        with tempfile.TemporaryDirectory() as d:
            with patch("scripts.collect_outcome_transition.hold_a_for_observed_frames") as hold, \
                 patch("scripts.collect_outcome_transition.SwingTraceClient") as client, \
                 patch("scripts.collect_outcome_transition.release_buttons") as release:
                hold.side_effect = TimeoutError("frame counter stalled")
                with self.assertRaisesRegex(TimeoutError, "stalled"):
                    run_session(object(), raw_path=Path(d) / "RAW.jsonl",
                        pre_samples=2, post_samples=2, settled_samples=2,
                        interval=0, a_lead_frames=12,
                        input_fn=lambda _q: next(answers),
                        snapshot_fn=lambda _r, phase: row(phase, 1))
                client.assert_not_called()
                release.assert_called_once()

    def test_cannot_mix_unmeasured_a_prime_and_measured_lead(self):
        with self.assertRaisesRegex(ValueError, "either RPC-count"):
            run_session(object(), raw_path=Path("unused.jsonl"),
                pre_samples=2, post_samples=2, settled_samples=2, interval=0,
                a_prime_requests=60, a_lead_frames=12,
                input_fn=lambda _q: self.fail("invalid options must not prompt"))

    def test_a_prime_validation_fails_before_consuming_user_input(self):
        with self.assertRaisesRegex(ValueError, "a_prime_requests"):
            run_session(object(), raw_path=Path("unused.jsonl"), pre_samples=2,
                post_samples=2, settled_samples=2, interval=0, a_prime_requests=-1,
                input_fn=lambda _q: self.fail("invalid input must not prompt"))

    def test_cleanup_after_failed_live_swing(self):
        answers = iter(["", ""])
        rpc = object()
        with tempfile.TemporaryDirectory() as d:
            with patch("scripts.collect_outcome_transition.prime_a_button"), \
                 patch("scripts.collect_outcome_transition.SwingTraceClient") as client, \
                 patch("scripts.collect_outcome_transition.release_buttons") as release:
                client.return_value.run.side_effect = RuntimeError("synthetic swing failure")
                with self.assertRaisesRegex(RuntimeError, "synthetic swing failure"):
                    run_session(rpc, raw_path=Path(d) / "RAW.jsonl",
                        pre_samples=2, post_samples=2, settled_samples=2, interval=0,
                        input_fn=lambda _q: next(answers),
                        snapshot_fn=lambda _r, phase: row(phase, 1),
                        a_prime_requests=60)
                release.assert_called_once()
                journal = release.call_args.args[0]
                self.assertIs(journal.rpc, rpc)
                self.assertEqual(release.call_args.kwargs, {"remote": 0})
                # Even an interrupted swing must preserve a private diagnostic.
                diagnostic = Path(d) / "RAW-a-commands.json"
                self.assertTrue(diagnostic.exists())
                self.assertEqual(json.loads(diagnostic.read_text())["continuity"]["status"], "unknown")

    def test_evidence_file_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "RAW.jsonl"
            path.write_text("preserve me")
            with self.assertRaises(FileExistsError):
                run_session(object(), raw_path=path, pre_samples=2,
                    post_samples=2, settled_samples=2, interval=0,
                    input_fn=lambda q: "",
                    snapshot_fn=lambda rpc, phase: row(phase, 1))
            self.assertEqual(path.read_text(), "preserve me")


if __name__ == "__main__":
    unittest.main()
