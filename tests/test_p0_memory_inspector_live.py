"""Synthetic-only bounded live worker checks: never connects to real Dolphin."""
from __future__ import annotations

from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.inspector.live import LiveSampler, ReadOnlyRPC


class FakeRPC:
    def __init__(self):
        self.calls = []
    def call(self, method, args):
        self.calls.append(method)
        if method == "frame.get_count":
            return 3
        return 0
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


def pkt(rpc, phase, index, *, mutate=False, invalid=False, disconnect=False):
    rpc.call("memory.read_u32", [0x80000000])
    rpc.call("frame.get_count", [])
    if disconnect and index:
        raise TimeoutError("private pointer 0xDEADBEEF")
    owner = tuple([0] * 5 + [1] + [0] * 7 + [3])
    if mutate and index:
        owner = owner[:5] + (2,) + owner[6:]
    bracket = (index, index + 1) if not invalid else (index + 1, index)
    return {"identity": owner,
            "words": {"selected_ball_plus_0x30": (0x3f800000 + index, 0x00000000, 0x40000000),
                      "aim_candidate_plus_0x3c": (0x3f000000,)},
            "start_ns": index * 100000000, "end_ns": index * 100000000 + 600000,
            "frame_bracket": bracket}


class LiveTests(unittest.TestCase):
    def test_allowlist_only_read_rpc(self):
        fake = FakeRPC()
        bridge = ReadOnlyRPC(fake)
        self.assertEqual(bridge.call("memory.read_u32", [0x80000000]), 0)
        self.assertEqual(bridge.call("frame.get_count", []), 3)
        for forbidden in ("controller.set_buttons", "controller.swing", "memory.write_u32",
                          "savestate.load", "savestate.save", "system.shutdown", "game.launch"):
            with self.subTest(method=forbidden), self.assertRaises(PermissionError):
                bridge.call(forbidden, [])
        self.assertEqual(fake.calls, ["memory.read_u32", "frame.get_count"])

    def run_worker(self, fn, *, pause=0.001):
        fake = FakeRPC()
        sampler = LiveSampler(connector=lambda: fake, packet_reader=fn, poll_pause_s=pause)
        sampler.start()
        sampler.thread.join(timeout=0.09)
        sampler.stop()
        sampler.thread.join(timeout=1)
        self.assertFalse(sampler.thread.is_alive())
        return sampler.drain(), fake

    def test_live_samples_have_source_and_rate(self):
        events, fake = self.run_worker(pkt, pause=0.005)
        samples = [e for e in events if e.kind == "sample"]
        self.assertGreaterEqual(len(samples), 2)
        self.assertEqual(samples[-1].hole, 3)
        self.assertEqual(samples[-1].selected_player, 1)
        self.assertTrue(samples[-1].sample.source_qualified)
        self.assertGreater(samples[-1].rate_hz, 0.0)
        self.assertEqual(samples[-1].sample.words["selected_ball_plus_0x30"][0], 0x3f800000 + samples[-1].sample.ordinal)
        self.assertTrue(set(fake.calls) <= {"memory.read_u32", "frame.get_count"})
        self.assertTrue(any(e.kind == "disconnected" for e in events))

    def test_source_identity_swap_stops_without_joining(self):
        events, _ = self.run_worker(lambda rpc, phase, i: pkt(rpc, phase, i, mutate=True))
        self.assertEqual([e.kind for e in events], ["sample", "error"])
        self.assertIn("source/bridge failure", events[-1].reason)

    def test_invalid_nonphysics_bracket_abstains(self):
        events, _ = self.run_worker(lambda rpc, phase, i: pkt(rpc, phase, i, invalid=True))
        self.assertEqual([e.kind for e in events], ["error"])

    def test_timeout_fail_closed_and_no_private_pointer_leak(self):
        events, _ = self.run_worker(lambda rpc, phase, i: pkt(rpc, phase, i, disconnect=True))
        self.assertEqual([e.kind for e in events], ["sample", "error"])
        self.assertIn("TimeoutError", events[-1].reason)
        self.assertNotIn("DEADBEEF", events[-1].reason)

    def test_bounded_queue_and_no_unattended_reconnect(self):
        events, _ = self.run_worker(pkt, pause=0)
        self.assertLessEqual(len(events), 24)
        self.assertEqual(events[-1].kind, "disconnected")

    def test_invalid_raw_types_fail_closed(self):
        def broken(rpc, phase, index):
            p = pkt(rpc, phase, index)
            p["words"]["selected_ball_plus_0x30"] = (True,)
            return p
        events, _ = self.run_worker(broken)
        self.assertEqual([e.kind for e in events], ["error"])

    def test_local_port_validation(self):
        with self.assertRaises(ValueError):
            LiveSampler(port=0)
        with self.assertRaises(ValueError):
            LiveSampler(port=True)

    def test_worker_source_import_only_during_user_start(self):
        source = (ROOT / "src/wii_ai_golf/inspector/live.py").read_text()
        self.assertIn("from p0_live_directional_aim_series import packet", source)
        self.assertIn("ReadOnlyRPC(raw_rpc)", source)
        self.assertNotIn('rpc.call("memory.write', source)
        self.assertNotIn('rpc.call("controller.', source)


if __name__ == "__main__":
    unittest.main()
