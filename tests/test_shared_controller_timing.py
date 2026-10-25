"""A lead uses observed Dolphin frames, not button RPC count; never sends motion."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.shared.controller_timing import hold_a_for_observed_frames


class FakeRPC:
    def __init__(self, counts: list[int]):
        self.counts = list(counts)
        self.calls = []

    def call(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "frame.get_count":
            if not self.counts:
                raise RuntimeError("test exhausted available frame counts")
            return self.counts.pop(0)
        if name == "controller.set_wiimote_buttons":
            return {"ok": True}
        raise AssertionError(f"Unexpected RPC: {name}")


class ObservedAPreholdTests(unittest.TestCase):
    def test_one_a_button_call_before_twelve_observed_emulator_frames(self):
        rpc = FakeRPC([100, 101, 103, 112])
        result = hold_a_for_observed_frames(
            rpc, frames=12, sleep=lambda _: None, clock=lambda: 1.0)
        self.assertEqual(result["observed_frame_delta"], 12)
        self.assertEqual(result["requested_lead_frames"], 12)
        self.assertEqual(result["a_button_only_requests"], 1)
        self.assertFalse(result["game_a_recognition_verified"])
        self.assertEqual(result["polls"], 3)
        self.assertEqual(rpc.calls[0], (
            "controller.set_wiimote_buttons", [0, {"A": True, "B": False}]))
        self.assertEqual(rpc.calls[-1][0], "frame.get_count")
        self.assertFalse(any("swing" in name for name, _ in rpc.calls))

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
        self.assertFalse(any(x[1][1].get("A") is False
                             for x in rpc.calls if x[0] == "controller.set_wiimote_buttons"))


if __name__ == "__main__":
    unittest.main()
