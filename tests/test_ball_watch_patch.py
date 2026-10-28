"""Synthetic-only, no Dolphin, no real RAM and no controller input."""
import ast
import struct
import unittest

from wii_ai_golf.integration.atomic_patch import patch_bridge, git_blob_sha
from wii_ai_golf.integration.swing_patch import extend_atomic_bridge_with_swing
from wii_ai_golf.integration.ball_watch_patch import (
    _BALL_WATCH_HANDLER, extend_swing_bridge_with_ball_watch,
    BallWatchPatchError, BALL_WATCH_MARKER,
)


FIXTURE = ('HANDLERS = {\n'
           '    "frame.get_count":                _frame_get_count,\n'
           '}\n'
           'while True:\n'
           '    await event.frameadvance()\n'
           '    _frame_count += 1\n'
           '    _poll_sockets()\n')


def befloat(x):
    return struct.unpack(">I", struct.pack(">f", x))[0]


class FakeMemory:
    def __init__(self):
        self.words = {}
        m, scene, config, field = 0x80007000, 0x90010000, 0x90011000, 0x90012000
        pm, ball, start = 0x90013000, 0x90014000, 0x90015000
        self.words.update({
            0x804BF4D8: m, m + 0x18: 5, m + 0x0C: scene,
            scene + 0x1C: 5, scene + 0x20: m, scene + 0x54: 2,
            0x804BF8C4: config, config + 0x94: 4, config + 0x98: 1,
            0x804BF868: field, field + 0x50: start,
            0x804BF8D0: pm, pm: 0x803C7DD0, pm + 0x334: pm + 4,
            pm + 4 + 0x88: ball, ball: 0x803C7918,
            ball + 0x4C: ball + 0x30,
            start + 0x48: start + 0x0C, start + 0x4C: start + 0x30,
        })
        for base in (ball + 0x30, start + 0x30, pm + 4 + 0x54):
            for i, value in enumerate((2.5, 0.75, -4.0)):
                self.words[base + i * 4] = befloat(value)

    def read_u32(self, address):
        return self.words[address]


class WatchPatchTests(unittest.TestCase):
    def setUp(self):
        self.mem = FakeMemory()
        self.ns = {"memory": self.mem, "_wii_ai_trace": None, "_frame_count": 100}
        exec(_BALL_WATCH_HANDLER, self.ns)

    def test_generated_source_is_compilable_and_single_tick(self):
        base = patch_bridge(FIXTURE, expected_sha=git_blob_sha(FIXTURE))
        swing = extend_atomic_bridge_with_swing(base)
        source = extend_swing_bridge_with_ball_watch(swing)
        self.assertIn(BALL_WATCH_MARKER, source)
        self.assertIn('    "golf.ball_watch.arm": _wii_ball_watch_arm,', source)
        self.assertEqual(source.count("    _wii_ball_watch_tick()\n    _wii_ai_tick()"), 1)
        self.assertIn('    _poll_sockets()', source)
        compile(source, "watched_bridge.py", "exec",
                flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        with self.assertRaises(BallWatchPatchError):
            extend_swing_bridge_with_ball_watch(source)
        with self.assertRaises(BallWatchPatchError):
            extend_swing_bridge_with_ball_watch(base)

    def test_source_gated_stationary_vector(self):
        snap = self.ns["_wii_ball_snapshot"]()
        self.assertEqual(snap["selected_slot_candidate"], 0)
        self.assertEqual(snap["source_hole_index"], 1)
        self.assertEqual(snap["ball_translation_f32_candidate"], [2.5, 0.75, -4.0])
        self.assertEqual(snap["current_start_f32_candidate"],
                         snap["ball_translation_f32_candidate"])
        self.assertNotIn("runtime_pointer", snap)

    def test_arm_tick_drain_local_only(self):
        self.ns["_wii_ball_watch_arm"]([24, 4])
        for f in range(101, 126):
            self.ns["_frame_count"] = f
            self.ns["_wii_ball_watch_tick"]()
        report = self.ns["_wii_ball_watch_drain"]([])
        self.assertEqual(len(report["samples"]), 7)
        self.assertEqual(report["status"]["state"], "complete")
        self.assertFalse(report["training_allowed"])
        self.assertEqual(self.ns["_wii_ball_watch_status"]([])["state"], "idle")

    def test_trace_sample_index_is_predispatch_not_contact(self):
        self.ns["_wii_ai_trace"] = {
            "id": 7, "start": 101, "samples": [0] * 89
        }
        self.ns["_frame_count"] = 115
        snap = self.ns["_wii_ball_snapshot"]()
        self.assertEqual(snap["trace_id_if_active"], 7)
        self.assertEqual(snap["trace_sample_index_if_active"], 14)
        self.assertNotIn("contact", snap)

    def test_refuses_wrong_scene_and_selector(self):
        m = self.mem.words[0x804BF4D8]
        self.mem.words[m + 0x18] = 4
        with self.assertRaises(ValueError):
            self.ns["_wii_ball_snapshot"]()
        self.mem.words[m + 0x18] = 5
        pm = self.mem.words[0x804BF8D0]
        self.mem.words[pm + 0x334] = 0xDEADBEEF
        with self.assertRaises(ValueError):
            self.ns["_wii_ball_snapshot"]()

    def test_bad_read_fails_closed_without_crashing_swing(self):
        self.ns["_wii_ball_watch_arm"]([24, 4])
        self.ns["_frame_count"] = 101
        self.mem.words.pop(0x804BF4D8)
        self.ns["_wii_ball_watch_tick"]()
        self.assertEqual(self.ns["_wii_ball_watch_status"]([])["state"], "source_gate_failed")
        self.assertEqual(len(self.ns["_wii_ball_watch_drain"]([])["samples"]), 0)

    def test_arm_limits_no_data_leak(self):
        with self.assertRaises(ValueError):
            self.ns["_wii_ball_watch_arm"]([320, 2])
        with self.assertRaises(ValueError):
            self.ns["_wii_ball_watch_arm"]([320, 0])
        with self.assertRaises(ValueError):
            self.ns["_wii_ball_watch_arm"]([15, 4])
        self.assertEqual(self.ns["_wii_ball_watch_status"]([])["state"], "idle")

    def test_slow_read_disarms(self):
        class Slow:
            n = 0
            def perf_counter(self):
                self.n += 1
                return self.n * 0.01
        self.ns["_wii_ball_time"] = Slow()
        self.ns["_wii_ball_watch_arm"]([24, 4])
        self.ns["_frame_count"] = 101
        self.ns["_wii_ball_watch_tick"]()
        self.assertEqual(self.ns["_wii_ball_watch_status"]([])["state"],
                         "read_overhead_exceeded")
        self.assertEqual(self.ns["_wii_ball_watch_status"]([])["samples"], 1)


if __name__ == "__main__":
    unittest.main()
