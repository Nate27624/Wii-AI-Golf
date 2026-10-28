"""OFFLINE-only single-factor V1 pretrace A comparison tests.

No Dolphin session or game memory accessed. Baseline remains 45 A-held ticks;
experimental mode uses 45 NO-A ticks and the identical frozen 89-frame trace.
"""
from __future__ import annotations

from pathlib import Path
import io
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]

import record_selected_ball_swing_v1_private as v1
import analyze_selected_player_swing_words_private as audit
from probe_swing import build_probe


class FakeRPC:
    def __init__(self):
        self.calls = []
        self.tick = 100
        self.statuses = ["recording", "complete"]

    def call(self, method, args=None):
        self.calls.append((method, args))
        if method == "frame.get_count":
            self.tick += 1
            return self.tick
        if method == "golf.ball_watch.status":
            return {"state": self.statuses.pop(0)
                    if len(self.statuses) > 1 else self.statuses[0]}
        if method == "golf.ball_watch.drain":
            return {"status": {"state": "complete"}, "samples": [{}]}
        return {"state": "acknowledged"}


def idle(rpc, *, frames):
    assert frames == 24
    rpc.calls.append(("test.idle_observed", [24]))
    return {"observed_idle_frame_delta": 25}


def neutral(rpc, *, frames):
    assert frames == 45
    rpc.calls.append(("test.no_A_observed", [45]))
    return {
        "observed_frame_delta": 45, "a_button_only_requests": 0,
        "game_a_recognition_verified": False, "input_mode": "neutral-no-A"
    }


def trace(rpc, values):
    assert len(values) == 89
    rpc.calls.append(("test.trace89", [len(values)]))
    return {"state": "complete", "total_frames": 89, "applied_frames": 89}


def probe():
    return build_probe("forward", follow_through_frames=30, a_setup_frames=12)


def mock_report():
    def row(stage, tick, trace_index=None):
        words = [0] * 51
        if stage == "trace" and trace_index is not None and trace_index >= 12:
            words[0x74 // 4] = 1
        return {
            "input_stage": stage,
            "source_owner_consistent": True,
            "selected_player_record_words_PRIVATE": words,
            "frame_tick_index": tick,
            "read_overhead_us": 64,
            "selected_slot_candidate": 0,
            "source_hole_index": 1,
            "trace_id_if_active": 3 if trace_index is not None else None,
            "trace_sample_index_if_active": trace_index,
        }
    rows = []
    for i in range(7):
        rows.append(row("idle_control", 4 * len(rows)))
    for i in range(12):
        rows.append(row("a_prime", 4 * len(rows)))
    for k in range(0, 89, 4):
        rows.append(row("trace", 4 * len(rows), k))
    for i in range(28):
        rows.append(row("posttrace", 4 * len(rows)))
    assert len(rows) == 70
    return {
        "kind": "PRIVATE-UNVERIFIED-selected-ball-frame-watch",
        "watch_status": {"state": "complete", "samples": 70, "max_read_us": 64},
        "safe_summary": {
            "watch_complete": True,
            "source_owner_consistency_checks_passed": True,
            "read_performance_checks_passed": True,
            "source_selected_slot_stable": True,
            "source_hole_stable": True,
            "start_vector_stable": True,
            "pretrace_control_mode": "neutral-45",
            "pretrace_control_A_requested": False,
            "pretrace_control_A_requests": 0,
            "pretrace_control_game_A_recognition_verified": False,
            "a_lead_observed_frames": 0,
            "pretrace_control_observed_frames": 45,
            "legacy_a_prime_stage_is_no_A_control": True,
        },
        "PRIVATE_UNVERIFIED_NUMERIC_VECTORS": rows,
    }


class NoAPretraceReviewTests(unittest.TestCase):
    def test_45_tick_neutral_sampler_never_calls_controller(self):
        rpc = FakeRPC()
        result = v1.passive_no_a_pretrace_control(
            rpc, frames=45, clock=lambda: 0.0, sleep=lambda _: None)
        self.assertGreaterEqual(result["observed_frame_delta"], 45)
        self.assertEqual(result["a_button_only_requests"], 0)
        self.assertTrue(all(not name.startswith("controller.")
                            for name, _ in rpc.calls))

    def test_same_duration_single_factor_no_a_before_frozen_trace(self):
        rpc = FakeRPC()
        def forbidden_a(*args, **kwargs):
            raise AssertionError("NO A prime RPC allowed")
        result = v1.capture_one(
            rpc, probe(), idle_wait=idle, neutral_wait=neutral,
            hold_a=forbidden_a, pretrace_mode="neutral-45", run_trace=trace,
            sleep=lambda _: None)
        self.assertEqual(result["pretrace_mode"], "neutral-45")
        self.assertEqual(result["hold"]["a_button_only_requests"], 0)
        self.assertEqual(result["trace"]["applied_frames"], 89)
        self.assertEqual(result["digest"], v1.validate_frozen_trace(probe()))
        names = [m for m, _ in rpc.calls]
        self.assertLess(names.index("test.idle_observed"),
                        names.index("test.no_A_observed"))
        self.assertLess(names.index("test.no_A_observed"),
                        names.index("test.trace89"))
        self.assertEqual([p for m,p in rpc.calls
                          if m == "golf.ball_watch.stage"],
                         [["a_prime"], ["trace"], ["posttrace"]])
        self.assertEqual(names.count("test.trace89"), 1)
        self.assertEqual(names.count("golf.ball_watch.drain"), 1)
        self.assertEqual(names.count("controller.set_wiimote_buttons"), 3)

    def test_neutral_short_wait_aborts_trace_with_release(self):
        rpc = FakeRPC()
        def short(rpc, *, frames):
            return {"observed_frame_delta": 44, "a_button_only_requests": 0,
                    "game_a_recognition_verified": False}
        with self.assertRaisesRegex(RuntimeError, "fixed 45-tick"):
            v1.capture_one(
                rpc, probe(), idle_wait=idle, neutral_wait=short,
                pretrace_mode="neutral-45", run_trace=trace, sleep=lambda _: None)
        names = [m for m,_ in rpc.calls]
        self.assertNotIn("test.trace89", names)
        self.assertEqual(names.count("controller.set_wiimote_buttons"), 3)

    def test_invalid_mode_refused_before_watcher_arm(self):
        rpc = FakeRPC()
        with self.assertRaisesRegex(ValueError, "unreviewed pretrace mode"):
            v1.capture_one(rpc, probe(), pretrace_mode="random")
        self.assertEqual(rpc.calls, [])

    def test_cli_new_mode_is_dry_run_without_rpc(self):
        out = io.StringIO()
        with patch.object(v1, "FelkRPC", side_effect=AssertionError("no RPC")):
            with redirect_stdout(out):
                self.assertEqual(v1.main(["--pretrace-mode", "neutral-45"]), 0)
        self.assertIn('"pretrace_control_mode": "neutral-45"', out.getvalue())

    def test_analyzer_does_not_mislabel_neutral_as_A_only(self):
        result = audit.analyze(mock_report())
        self.assertEqual(result["pretrace_control_mode"], "neutral-45")
        self.assertTrue(result["legacy_a_prime_stage_is_no_A_control"])
        changed = next(x for x in result["source_relative_candidate_offsets"]
                       if x["source_relative_offset"] == "+0x074")
        self.assertIsNone(changed["a_only_stable_and_equal_to_idle"])
        self.assertTrue(changed["pretrace_control_stable_and_equal_to_idle"])
        self.assertFalse(changed["pretrace_control_A_requested"])

    def test_analyzer_rejects_falsely_claimed_A_in_neutral_mode(self):
        data = mock_report()
        data["safe_summary"]["pretrace_control_A_requested"] = True
        with self.assertRaisesRegex(ValueError, "contradicts"):
            audit.analyze(data)

    def test_prior_A_held_metadata_remains_compatible(self):
        data = mock_report()
        for k in ("pretrace_control_mode", "pretrace_control_A_requested",
                  "pretrace_control_A_requests", "pretrace_control_game_A_recognition_verified",
                  "a_lead_observed_frames", "pretrace_control_observed_frames",
                  "legacy_a_prime_stage_is_no_A_control"):
            del data["safe_summary"][k]
        result = audit.analyze(data)
        self.assertEqual(result["pretrace_control_mode"], "hold-a-45")
        changed = next(x for x in result["source_relative_candidate_offsets"]
                       if x["source_relative_offset"] == "+0x074")
        self.assertTrue(changed["a_only_stable_and_equal_to_idle"])


if __name__ == "__main__":
    unittest.main()
