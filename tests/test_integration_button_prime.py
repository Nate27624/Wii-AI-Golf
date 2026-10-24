"""Critical regression: A-only button presses MUST precede swing primitive.

This test models the exact user-observed failure after PR #34: 45 nominal
"prehold" swing samples still used set_wiimote_swing(0), so Wii Sports
visually swung before A engaged and the ball was not struck.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "src")):
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)

from scripts import probe_swing
from wii_ai_golf.integration.button_prime import prime_a_button


class FakeRPC:
    def __init__(self, *, fail_prime_after: int | None = None):
        self.calls = []
        self.fail_prime_after = fail_prime_after
        self.pressed = 0
        self.trace_length = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def call(self, method, params=None):
        self.calls.append((method, params))
        if method == "bridge.ping":
            return {"bridge_version": "0.3.0"}
        if method == "controller.set_wiimote_buttons":
            if params[1]["A"]:
                self.pressed += 1
                if self.fail_prime_after is not None and self.pressed > self.fail_prime_after:
                    raise OSError("injected button failure")
            return {"accepted": True}
        if method == "trace.submit_swing":
            self.trace_length = len(params[1])
            return {"state": "scheduled", "kind": "swing", "id": 1}
        if method == "trace.status":
            return {"state": "complete", "kind": "swing",
                    "id": 1, "applied_frames": self.trace_length}
        if method == "trace.abort":
            return {"state": "aborted", "id": 1}
        raise AssertionError(f"unexpected RPC {method}")


class ButtonPrimeTests(unittest.TestCase):
    def test_genuinely_no_swing_api_calls_during_button_prehold(self):
        rpc = FakeRPC()
        report = prime_a_button(rpc, remote=0, requests=60)
        self.assertEqual(report["button_only_requests"], 60)
        self.assertEqual(len(rpc.calls), 60)
        self.assertTrue(all(method == "controller.set_wiimote_buttons" and
                            params == [0, {"A": True, "B": False}]
                            for method, params in rpc.calls))

    def test_invalid_parameters_never_touch_bridge(self):
        rpc = FakeRPC()
        for count in (-1, 181, None, True, 45.0, "45"):
            with self.subTest(count=count), self.assertRaises(ValueError):
                prime_a_button(rpc, requests=count)
        for remote in (-1, 4, "0", True):
            with self.subTest(remote=remote), self.assertRaises(ValueError):
                prime_a_button(rpc, remote=remote)
        self.assertEqual(rpc.calls, [])

    def test_zero_requests_is_legacy_control(self):
        rpc = FakeRPC()
        self.assertEqual(prime_a_button(rpc, requests=0)["button_only_requests"], 0)
        self.assertFalse(rpc.calls)

    def test_full_attached_trial_button_only_first_then_exact_89_frame_swing(self):
        rpc = FakeRPC()
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "observations.jsonl"
            args = ["probe_swing.py", "--attach-running", "--send-live-swing",
                    "--preset", "forward", "--a-setup-frames", "12",
                    "--a-prime-frames", "60", "--follow-through-frames", "30",
                    "--report", str(report)]
            with patch.object(sys, "argv", args), \
                 patch.object(probe_swing, "FelkRPC", return_value=rpc), \
                 patch("builtins.input", side_effect=[
                     "", "none", "no", "unknown", "", ""
                 ]):
                probe_swing.main()

            methods = [method for method, _ in rpc.calls]
            swing_idx = methods.index("trace.submit_swing")
            self.assertEqual(methods[0], "bridge.ping")
            before = rpc.calls[1:swing_idx]
            self.assertEqual(len(before), 60)
            self.assertTrue(all(method == "controller.set_wiimote_buttons"
                                and params == [0, {"A": True, "B": False}]
                                for method, params in before))
            payload = rpc.calls[swing_idx][1][1]
            self.assertEqual(len(payload), 89)
            self.assertTrue(all(sample[0] is True for sample in payload[:77]))
            self.assertTrue(all(sample[0] is False for sample in payload[77:]))
            self.assertEqual(len(payload[0]), 8)
            self.assertEqual(payload[12][4], 0.25)  # original backswing distance
            self.assertEqual(payload[27][4], 0.6)   # original forward distance
            self.assertTrue(all(method == "controller.set_wiimote_buttons"
                                and params == [0, {"A": False, "B": False}]
                                for method, params in rpc.calls[-3:]))

            line = json.loads(report.read_text(encoding="utf-8").strip())
            self.assertEqual(line["a_prime_frames"], 60)
            self.assertEqual(line["a_setup_frames"], 12)
            self.assertEqual(line["button_prime_dispatch"]["button_only_requests"], 60)
            self.assertEqual(line["dispatch"]["applied_frames"], 89)
            self.assertEqual(line["human_ball_moved"], "no")
            self.assertIsNone(line["game_score"])

    def test_failed_button_prehold_never_submits_swing_and_releases_a(self):
        rpc = FakeRPC(fail_prime_after=3)
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "failed.jsonl"
            args = ["probe_swing.py", "--attach-running", "--send-live-swing",
                    "--a-prime-frames", "60", "--report", str(report)]
            with patch.object(sys, "argv", args), \
                 patch.object(probe_swing, "FelkRPC", return_value=rpc), \
                 patch("builtins.input", return_value=""):
                with self.assertRaisesRegex(OSError, "injected button failure"):
                    probe_swing.main()
            self.assertNotIn("trace.submit_swing", [m for m, _ in rpc.calls])
            self.assertTrue(any(m == "controller.set_wiimote_buttons" and p[1]["A"] is False
                                for m, p in rpc.calls))
            self.assertFalse(report.exists())


if __name__ == "__main__":
    unittest.main()
