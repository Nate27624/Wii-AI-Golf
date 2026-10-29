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
    def test_a_button_reasserted_for_each_observed_emulator_frame(self):
        # Frame-scoped Felk input: one A request followed by polls alone would
        # leave 11/12 frames without button coverage in the old implementation.
        rpc = FakeRPC(list(range(100, 113)))
        result = hold_a_for_observed_frames(
            rpc, frames=12, sleep=lambda _: None, clock=lambda: 1.0)
        self.assertEqual(result["observed_frame_delta"], 12)
        self.assertEqual(result["requested_lead_frames"], 12)
        self.assertEqual(result["a_button_only_requests"], 13)
        self.assertTrue(result["per_observed_frame_a_reasserted"])
        self.assertFalse(result["game_a_recognition_verified"])
        self.assertEqual(result["polls"], 12)
        self.assertEqual(rpc.calls[0], (
            "controller.set_wiimote_buttons", [0, {"A": True, "B": False}]))
        buttons = [parameters for method, parameters in rpc.calls
                   if method == "controller.set_wiimote_buttons"]
        self.assertEqual(buttons, [[0, {"A": True, "B": False}]] * 13)
        self.assertEqual(rpc.calls[-1][0], "controller.set_wiimote_buttons")
        self.assertFalse(any("swing" in name for name, _ in rpc.calls))

    def test_same_frame_poll_does_not_invent_elapsed_frames(self):
        rpc = FakeRPC([100, 100, 100, 101, 101, 102, 103])
        result = hold_a_for_observed_frames(
            rpc, frames=3, sleep=lambda _: None, clock=lambda: 1.0)
        self.assertEqual(result["polls"], 6)
        self.assertEqual(result["observed_frame_delta"], 3)
        self.assertEqual(result["a_button_only_requests"], 4)
        self.assertFalse(result["game_a_recognition_verified"])

    def test_skipped_emulated_frame_aborts_before_swing(self):
        rpc = FakeRPC([100, 101, 103])
        with self.assertRaisesRegex(RuntimeError, "Unobserved emulated frame gap"):
            hold_a_for_observed_frames(
                rpc, frames=12, sleep=lambda _: None, clock=lambda: 1.0)
        self.assertEqual(rpc.calls[-1], (
            "controller.set_wiimote_buttons", [0, {"A": False, "B": False}]))
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

    def test_reassertion_rpc_failure_releases_and_never_sends_motion(self):
        class ErrorRPC(FakeRPC):
            def __init__(self, counts):
                super().__init__(counts)
                self.a_true_requests = 0

            def call(self, name, arguments):
                if name == "controller.set_wiimote_buttons" and arguments[1]["A"]:
                    self.a_true_requests += 1
                    if self.a_true_requests == 2:
                        raise OSError("injected A refresh failure")
                return super().call(name, arguments)

        rpc = ErrorRPC([100, 101])
        with self.assertRaisesRegex(OSError, "injected A refresh failure"):
            hold_a_for_observed_frames(
                rpc, frames=12, sleep=lambda _: None, clock=lambda: 1.0)
        self.assertEqual(rpc.calls[-1], (
            "controller.set_wiimote_buttons", [0, {"A": False, "B": False}]))
        self.assertFalse(any("swing" in name for name, _ in rpc.calls))

    def test_custom_remote_stays_consistent(self):
        rpc = FakeRPC(list(range(55, 68)))
        result = hold_a_for_observed_frames(
            rpc, frames=12, remote=1, sleep=lambda _: None, clock=lambda: 1.0)
        self.assertEqual(result["remote"], 1)
        self.assertEqual(rpc.calls[0][1][0], 1)
        self.assertFalse(any(x[1][1].get("A") is False
                             for x in rpc.calls if x[0] == "controller.set_wiimote_buttons"))


if __name__ == "__main__":
    unittest.main()
