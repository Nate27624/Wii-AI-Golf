import unittest
from pathlib import Path
import sys

# Avoid a stale editable install shadowing this checkout during unittest discovery.
_ROOT = Path(__file__).resolve().parents[1]
for _entry in (str(_ROOT), str(_ROOT / "src")):
    if _entry in sys.path:
        sys.path.remove(_entry)
    sys.path.insert(0, _entry)

from wii_ai_golf.integration.swing_client import SwingSample, SwingTraceClient
from scripts.probe_swing import build_probe


class RPC:
    def __init__(self):
        self.calls = []
        self.state = {"state": "idle"}

    def call(self, method, params=None):
        self.calls.append((method, params))
        if method == "trace.submit_swing":
            self.n = len(params[1])
            self.state = {"kind": "swing", "id": 1, "state": "scheduled", "applied_frames": 0}
        elif method == "trace.status":
            self.state = {"id": 1, "state": "complete", "applied_frames": self.n}
        elif method == "trace.abort":
            self.state["state"] = "aborted"
        return dict(self.state)


class SwingClientTests(unittest.TestCase):
    def test_valid_trace(self):
        rpc = RPC()
        cli = SwingTraceClient(rpc, port=0)
        result = cli.run(build_probe("forward"))
        self.assertEqual(result["applied_frames"], 122)
        self.assertEqual(rpc.calls[0][0], "trace.submit_swing")
        self.assertEqual(len(rpc.calls[0][1][1][0]), 8)

    def test_all_presets_hold_A_before_motion_and_through_followthrough(self):
        for name in ("forward", "reverse", "sideways"):
            ss = build_probe(name)
            # 45 pre-A + 15 backswing + 20 forward + 30 A-held follow-through
            # +12 released = 122. First motion is sample 46 (1-based).
            self.assertEqual(len(ss), 122)
            self.assertTrue(all(s.hold_a for s in ss[:110]))
            self.assertFalse(any(s.hold_a for s in ss[110:]))
            self.assertEqual(ss[-1].speed_m_s, 0)
            for sample in ss[:45]:
                self.assertTrue(sample.hold_a)
                self.assertEqual(sample.direction, (0.0, 0.0, 0.0))
                self.assertEqual(sample.distance_m, 0)
                self.assertEqual(sample.speed_m_s, 0)
                self.assertEqual(sample.return_speed_m_s, 0)
                self.assertEqual(sample.angle_rad, 0)
            self.assertNotEqual(ss[45].direction, (0.0, 0.0, 0.0))
            # Follow-through with A held, then 12 A-off neutral tail.
            self.assertTrue(all(sample.hold_a and sample.speed_m_s == 0
                                for sample in ss[80:110]))

    def test_configurable_followthrough_and_legacy_release(self):
        for delay in (0, 1, 15, 30, 45, 90, 180):
            with self.subTest(delay=delay):
                ss = build_probe("forward", follow_through_frames=delay)
                self.assertEqual(len(ss), 92 + delay)
                held = 80 + delay
                self.assertTrue(all(s.hold_a for s in ss[:held]))
                self.assertTrue(all(not s.hold_a for s in ss[held:]))
                self.assertTrue(all(s.speed_m_s == 0 for s in ss[80:held]))
                self.assertFalse(any(s.hold_a for s in ss[-12:]))
        self.assertEqual(len(build_probe("forward", follow_through_frames=0)), 92)

    def test_setup_delay_12_exactly_replays_original_successful_89_frame_trace(self):
        ss = build_probe("forward", a_setup_frames=12, follow_through_frames=30)
        self.assertEqual(len(ss), 89)
        self.assertEqual(sum(s.hold_a for s in ss), 77)
        self.assertTrue(all(s.hold_a and s.speed_m_s == 0 for s in ss[:12]))
        self.assertNotEqual(ss[12].direction, (0.0, 0.0, 0.0))
        self.assertEqual(ss[12].distance_m, .25)
        self.assertEqual(ss[27].distance_m, .6)
        self.assertTrue(all(not s.hold_a for s in ss[77:]))

    def test_setup_delay_is_one_factor_and_preserves_motion_profile(self):
        old = build_probe("sideways", a_setup_frames=12)
        new = build_probe("sideways", a_setup_frames=60)
        self.assertEqual(old[12:47], new[60:95])
        self.assertEqual(old[47:], new[95:])
        self.assertTrue(all(s.hold_a and s.speed_m_s == 0 for s in new[:60]))
        self.assertEqual(len(new), 137)

    def test_bad_followthrough_rejected(self):
        for val in (-1, 181, 3.5, None, True, "45"):
            with self.subTest(val=val), self.assertRaises(ValueError):
                build_probe("forward", follow_through_frames=val)

    def test_bad_a_setup_rejected(self):
        for val in (-1, 0, 181, 3.5, None, True, "45"):
            with self.subTest(val=val), self.assertRaises(ValueError):
                build_probe("forward", a_setup_frames=val)

    def test_protocol_limit_and_client_dispatch_extended_trace(self):
        rpc = RPC()
        long_samples = build_probe("forward", follow_through_frames=180)
        self.assertLessEqual(len(long_samples), 600)
        result = SwingTraceClient(rpc, port=0).run(long_samples)
        self.assertEqual(result["applied_frames"], 272)

    def test_validation(self):
        with self.assertRaises(ValueError):
            SwingSample(True, (0, 2, 0), .4, 2, 1, 0)
        with self.assertRaises(ValueError):
            SwingSample(True, (0, 1, 0), .4, float("nan"), 1, 0)
        with self.assertRaises(ValueError):
            SwingTraceClient(RPC()).submit([])


if __name__ == "__main__":
    unittest.main()
