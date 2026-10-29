"""A lead uses observed Dolphin frames, not button RPC count; never sends motion."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.shared.controller_timing import hold_a_for_observed_frames


class FakeRPC:
    def __init__(self, counts: list[int], *, observed_a=True):
        self.counts = list(counts)
        self.observed_a = observed_a
        self.calls = []

    def call(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "frame.get_count":
            if not self.counts:
                raise RuntimeError("test exhausted available frame counts")
            return self.counts.pop(0)
        if name == "controller.set_wiimote_buttons":
            return {"ok": True}
        if name == "controller.get_wiimote_buttons":
            if isinstance(self.observed_a, BaseException):
                raise self.observed_a
            return {"A": self.observed_a}
        raise AssertionError(f"Unexpected RPC: {name}")


class ObservedAPreholdTests(unittest.TestCase):
    def test_source_frame_scoped_a_lead_requires_last_seen_diagnostic(self):
        rpc = FakeRPC([100, 101, 103, 112])
        result = hold_a_for_observed_frames(
            rpc, frames=12, sleep=lambda _: None, clock=lambda: 1.0)
        self.assertEqual(result["observed_frame_delta"], 12)
        self.assertEqual(result["requested_lead_frames"], 12)
        self.assertEqual(result["a_button_only_requests"], 1)
        self.assertTrue(result["emulator_last_seen_a"])
        self.assertFalse(result["continuous_a_hold_verified"])
        self.assertFalse(result["game_a_recognition_verified"])
        self.assertEqual(result["polls"], 3)
        self.assertEqual(rpc.calls[0], (
            "controller.set_wiimote_buttons", [0, {"A": True, "B": False}]))
        self.assertEqual(rpc.calls[-1], (
            "controller.get_wiimote_buttons", [0]))
        self.assertFalse(any("swing" in name for name, _ in rpc.calls))

    def test_last_seen_a_false_aborts_before_any_motion_and_releases(self):
        rpc = FakeRPC([100, 105, 112], observed_a=False)
        with self.assertRaisesRegex(RuntimeError, "not pressed"):
            hold_a_for_observed_frames(
                rpc, frames=12, sleep=lambda _: None, clock=lambda: 1.0)
        self.assertIn(("controller.get_wiimote_buttons", [0]), rpc.calls)
        self.assertEqual(rpc.calls[-1], (
            "controller.set_wiimote_buttons",
            [0, {"A": False, "B": False}]))
        self.assertFalse(any("swing" in method for method, _ in rpc.calls))

    def test_missing_or_nonboolean_a_observation_refuses_swing(self):
        for value in (None, 0, 1, "yes", {}, OSError("missing input getter")):
            with self.subTest(value=repr(value)):
                rpc = FakeRPC([100, 112], observed_a=value)
                with self.assertRaises((RuntimeError, OSError)):
                    hold_a_for_observed_frames(
                        rpc, frames=12, sleep=lambda _: None, clock=lambda: 1.0)
                self.assertEqual(rpc.calls[-1], (
                    "controller.set_wiimote_buttons",
                    [0, {"A": False, "B": False}]))
                self.assertFalse(any("swing" in method for method, _ in rpc.calls))

    def test_timeout_releases_a_and_never_sends_motion(self):
        rpc = FakeRPC([44, 44, 44, 44, 44])
        with self.assertRaisesRegex(TimeoutError, "did not advance"):
            hold_a_for_observed_frames(
                rpc, frames=12, max_polls=3,
                sleep=lambda _: None, clock=lambda: 1.0)
        self.assertEqual(rpc.calls[-1], (
            "controller.set_wiimote_buttons", [0, {"A": False, "B": False}]))
        self.assertFalse(any("swing" in name for name, _ in rpc.calls))

    def test_backwards_emulated_time_releases_a(self):
        rpc = FakeRPC([100, 99])
        with self.assertRaisesRegex(RuntimeError, "backwards"):
            hold_a_for_observed_frames(
                rpc, frames=12, sleep=lambda _: None, clock=lambda: 1.0)
        self.assertEqual(rpc.calls[-1][1][1], {"A": False, "B": False})

    def test_unavailable_or_bad_frame_counter_fails_closed(self):
        for invalid in (True, None, -1, "15", 3.0):
            with self.subTest(invalid=invalid):
                rpc = FakeRPC([invalid])
                with self.assertRaisesRegex(RuntimeError, "invalid"):
                    hold_a_for_observed_frames(
                        rpc, frames=12, clock=lambda: 1.0)
                self.assertEqual(rpc.calls[-1][1][1], {"A": False, "B": False})

    def test_invalid_frame_lead_rejected_without_input(self):
        for frames in (0, -1, 91, 2.0, True, "12"):
            with self.subTest(frames=frames):
                rpc = FakeRPC([100])
                with self.assertRaises(ValueError):
                    hold_a_for_observed_frames(rpc, frames=frames)
                self.assertEqual(rpc.calls, [])

    def test_custom_remote_stays_consistent(self):
        rpc = FakeRPC([55, 67])
        result = hold_a_for_observed_frames(
            rpc, frames=12, remote=1, sleep=lambda _: None, clock=lambda: 1.0)
        self.assertEqual(result["remote"], 1)
        self.assertEqual(rpc.calls[0][1][0], 1)
        self.assertIn(("controller.get_wiimote_buttons", [1]), rpc.calls)
        self.assertFalse(any(x[1][1].get("A") is False
                             for x in rpc.calls if x[0] == "controller.set_wiimote_buttons"))


if __name__ == "__main__":
    unittest.main()
