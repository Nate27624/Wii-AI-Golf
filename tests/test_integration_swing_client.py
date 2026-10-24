import unittest

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
        self.assertEqual(result["applied_frames"], 59)
        self.assertEqual(rpc.calls[0][0], "trace.submit_swing")
        self.assertEqual(len(rpc.calls[0][1][1][0]), 8)

    def test_all_presets_have_bounded_frames_and_release(self):
        for name in ("forward", "reverse", "sideways"):
            ss = build_probe(name)
            self.assertEqual(len(ss), 59)
            self.assertTrue(all(s.hold_a for s in ss[:47]))
            self.assertFalse(any(s.hold_a for s in ss[47:]))
            self.assertEqual(ss[-1].speed_m_s, 0)

    def test_validation(self):
        with self.assertRaises(ValueError):
            SwingSample(True, (0, 2, 0), .4, 2, 1, 0)
        with self.assertRaises(ValueError):
            SwingSample(True, (0, 1, 0), .4, float("nan"), 1, 0)
        with self.assertRaises(ValueError):
            SwingTraceClient(RPC()).submit([])


if __name__ == "__main__":
    unittest.main()
