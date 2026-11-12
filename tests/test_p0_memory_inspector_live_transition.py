"""Synthetic source transition tests; zero game writes, bridge connects or assets."""
from __future__ import annotations

import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.inspector.live import LiveSampler, ReadOnlyRPC


class FakeRPC:
    def __init__(self):
        self.calls = []
        self.opens = 0

    def __enter__(self):
        self.opens += 1
        return self

    def __exit__(self, *args):
        return False

    def call(self, method, args):
        self.calls.append((method, tuple(args)))
        if method == "frame.get_count":
            return 1
        if method == "memory.read_u32":
            return 0
        raise AssertionError("Unsupported RPC in synthetic test")


def candidate(identity_tail: int, index: int) -> dict:
    identity = (11, 12, 13, 14, 15, identity_tail, 17, 18,
                19, 20, 21, 22, 23, 3)
    return {
        "identity": identity,
        "words": {
            "selected_ball_plus_0x30": (0x3f800000+identity_tail, 0, 0),
            "aim_candidate_plus_0x3c": (0x3f000000,),
        },
        "start_ns": index * 1000,
        "end_ns": index * 1000 + 500,
        "frame_bracket": (index, index+1),
    }


def run_simulated(sequence):
    """Patch ONLY the verified built-in reader to test worker orchestration."""
    fake = FakeRPC()
    source = iter(sequence)
    sampler = LiveSampler(connector=lambda: fake, poll_pause_s=0.002)

    def read(rpc, phase, index, **kwargs):
        rpc.call("memory.read_u32", [0x80000000])
        try:
            item = next(source)
        except StopIteration:
            sampler.stop()
            item = sequence[-1]
        if isinstance(item, BaseException):
            raise item
        return candidate(item, index)

    with patch("wii_ai_golf.inspector.fast.packet", side_effect=read):
        sampler.start()
        sampler.thread.join(timeout=2.)
        sampler.stop()
        sampler.thread.join(timeout=1.)
    if sampler.thread.is_alive():
        raise AssertionError("Synthetic live reader failed to stop")
    return sampler.drain(), fake


class LiveSourceTransitionTests(unittest.TestCase):
    def test_verifiably_changed_owner_restarts_source_segment_not_bridge(self):
        events, bridge = run_simulated([1, 1, 2, 2, 2])
        kinds = [e.kind for e in events]
        self.assertIn("transition", kinds)
        self.assertNotIn("error", kinds)
        samples = [e for e in events if e.kind == "sample"]
        self.assertGreaterEqual(len(samples), 3)
        self.assertEqual(samples[0].source_segment, 1)
        self.assertEqual(samples[-1].source_segment, 2)
        self.assertNotEqual(samples[0].sample.source_digest,
                            samples[-1].sample.source_digest)
        self.assertTrue(all(s.sample.source_qualified for s in samples))
        self.assertEqual(bridge.opens, 1)
        self.assertEqual({name for name,_ in bridge.calls},
                         {"memory.read_u32"})

    def test_temporary_invalid_owner_does_not_mix_old_or_new_samples(self):
        events, _ = run_simulated(
            [1, 1, ValueError("source identity changed across packet"),
             ValueError("scene source/owner mismatch"), 2, 2])
        kinds = [e.kind for e in events]
        self.assertEqual(kinds.count("transition"), 1)
        self.assertNotIn("error", kinds)
        samples = [e for e in events if e.kind == "sample"]
        self.assertEqual(samples[0].source_segment, 1)
        self.assertEqual(samples[-1].source_segment, 2)
        self.assertEqual(events[-1].kind, "disconnected")

    def test_same_pointer_reuse_after_source_gap_gets_new_epoch_digest(self):
        events, _ = run_simulated(
            [1, ValueError("not Golf scene"), 1, 1])
        samples = [e for e in events if e.kind == "sample"]
        self.assertEqual([s.source_segment for s in samples[:2]], [1, 2])
        self.assertNotEqual(samples[0].sample.source_digest,
                            samples[1].sample.source_digest)

    def test_rapidly_changing_owners_need_two_consecutive_good_packets(self):
        events, _ = run_simulated([1, 2, 3, 4, 4, 4])
        samples = [e for e in events if e.kind == "sample"]
        self.assertEqual([s.source_segment for s in samples[:2]], [1, 2])
        self.assertEqual(samples[1].selected_player, 4)
        self.assertEqual(sum(e.kind == "transition" for e in events), 1)

    def test_bad_rev1_or_malformed_values_still_fail_closed(self):
        for error in ("not Wii Sports USA Rev1",
                      "malformed bounded read",
                      "invalid revision header",
                      "invalid host time bracket"):
            with self.subTest(error=error):
                events,bridge = run_simulated([1, ValueError(error)])
                self.assertEqual(
                    [e.kind for e in events], ["sample", "error"])
                self.assertNotIn("transition",
                                 [e.kind for e in events])
                self.assertEqual(bridge.opens,1)
                self.assertNotIn("0x", events[-1].reason)

    def test_bounded_transition_times_out_without_reconnect(self):
        events,bridge = None,None
        with patch("wii_ai_golf.inspector.live._TRANSITION_MAX_SECONDS", 0.01):
            events,bridge = run_simulated(
                [1, ValueError("not Golf scene"),
                 ValueError("not Golf scene"),
                 ValueError("not Golf scene")])
        self.assertIn("transition",[e.kind for e in events])
        self.assertEqual(events[-1].kind,"error")
        self.assertIn("TRANSITION_TIMEOUT",events[-1].reason)
        self.assertEqual(bridge.opens,1)

    def test_noncanonical_reader_still_cannot_rebase_identity(self):
        fake = FakeRPC()
        sampler = LiveSampler(
            connector=lambda:fake,
            packet_reader=lambda rpc, phase, i: candidate(
                1 if i==0 else 2, i),
            poll_pause_s=.003)
        sampler.start()
        sampler.thread.join(timeout=1)
        self.assertFalse(sampler.thread.is_alive())
        events=sampler.drain()
        self.assertEqual([e.kind for e in events],["sample","error"])
        self.assertEqual(fake.opens,1)


if __name__ == "__main__":
    unittest.main()
