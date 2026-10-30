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

# A-only read probe uses a 51-word source-selected record. Tests never touch Dolphin.
class AProbeTests(unittest.TestCase):
    class ABridge(FakeRPC):
        def __init__(self, *, moving=False):
            super().__init__(); self.moving = moving; self.ball_reads = 0
        def call(self, method, args):
            self.calls.append(method)
            if method != 'memory.read_u32':
                raise AssertionError('unexpected RPC method')
            addr = args[0]
            if 0x90010000 <= addr < 0x900100cc:
                offset = (addr - 0x90010000) // 4
                return 0x3f000000 if offset == 15 else 29 if offset in (29,37,39,40,42,44,46,48) else 0
            if 0x90020030 <= addr <= 0x90020038:
                self.ball_reads += 1
                return (1,2,3)[(addr - 0x90020030)//4] + (1 if self.moving else 0)
            raise AssertionError('unexpected memory address')

    @staticmethod
    def packet(rpc, phase, index):
        identity = (0,0,0,0,0,1,0x90010000,0x90020000,0,0,0,0,0,1)
        return {'identity':identity, 'words':{'selected_ball_plus_0x30':(1,2,3),
                'aim_candidate_plus_0x3c':(0x3f000000,)},
                'start_ns':index*100000,'end_ns':index*100000+5000,
                'frame_bracket':(index,index+1)}

    def worker(self, bridge, *, epoch=True):
        sampler=LiveSampler(connector=lambda:bridge,packet_reader=self.packet,
             include_a_state=True,source_gate=lambda rpc, identity:epoch,poll_pause_s=0.001)
        sampler.start()
        sampler.thread.join(timeout=0.04)
        sampler.stop();sampler.thread.join(timeout=1)
        return sampler.drain(),bridge

    def test_record_read_is_bounded_validated_and_readonly(self):
        events,bridge=self.worker(self.ABridge())
        samples=[e for e in events if e.kind=='sample']
        self.assertTrue(samples)
        self.assertEqual(len(samples[0].a_record),51)
        self.assertEqual(samples[0].a_record[29],29)
        self.assertTrue(samples[0].a_read_start_ns>0)
        self.assertTrue(all(x=='memory.read_u32' for x in bridge.calls))

    def test_ball_change_during_51_read_yields_unknown_without_stopping_plot(self):
        events,_=self.worker(self.ABridge(moving=True))
        samples=[e for e in events if e.kind=='sample']
        self.assertTrue(samples)
        self.assertIsNone(samples[0].a_record)
        self.assertTrue(any(e.kind=='disconnected' for e in events))

    def test_invalid_source_epoch_aborts_probe(self):
        events,_=self.worker(self.ABridge(),epoch=False)
        self.assertEqual([e.kind for e in events],['error'])

    def test_a_probe_requires_end_epoch_guard(self):
        sampler=LiveSampler(connector=lambda:self.ABridge(),packet_reader=self.packet,
                             include_a_state=True)
        sampler.start();sampler.thread.join(timeout=1)
        self.assertEqual([e.kind for e in sampler.drain()],['error'])
