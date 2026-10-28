"""S001/S002: 51-word selected-record watched vs unwatched parity, FAKE.

Executes the REAL emitted _wii_ai_tick and the real _wii_ball_watch_tick
in a mock environment. Never opens Dolphin, a socket, or a ROM; no human
observations or runtime frame/performance claims are made.
"""
from __future__ import annotations

import ast
import struct
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from probe_swing import build_probe
from wii_ai_golf.integration.atomic_patch import (
    _ATOMIC_SNIPPET, git_blob_sha, patch_bridge,
)
from wii_ai_golf.integration.swing_patch import (
    _SWING_HANDLER, extend_atomic_bridge_with_swing,
)
from wii_ai_golf.integration.ball_watch_patch import (
    _BALL_WATCH_HANDLER, extend_swing_bridge_with_ball_watch,
)
from record_selected_ball_swing_private import validate_frozen_trace


MINIMAL_SOURCE = (
    'HANDLERS = {\n'
    '    "frame.get_count":                _frame_get_count,\n'
    '}\n'
    'while True:\n'
    '    await event.frameadvance()\n'
    '    _frame_count += 1\n'
    '    _poll_sockets()\n'
)


def word_float(v):
    return struct.unpack(">I", struct.pack(">f", v))[0]


class FakeMemory:
    def __init__(self):
        m, scene, config, field = 0x80007000, 0x90010000, 0x90011000, 0x90012000
        pm, ball, start = 0x90013000, 0x90014000, 0x90015000
        self.words = {
            0x80000000: 0x52535045, 0x80000004: 0x30310001,
            0x804BF4D8: m, m + 0x18: 5, m + 0x0C: scene,
            scene + 0x1C: 5, scene + 0x20: m, scene + 0x54: 2,
            0x804BF8C4: config, config + 0x94: 4, config + 0x98: 1,
            0x804BF868: field, field + 0x50: start,
            0x804BF8D0: pm, pm: 0x803C7DD0, pm + 0x334: pm + 4,
            pm + 4 + 0x88: ball, ball: 0x803C7918,
            ball + 0x4C: ball + 0x30,
            start + 0x48: start + 0x0C, start + 0x4C: start + 0x30,
        }
        for base in (ball + 0x30, start + 0x30, pm + 4 + 0x54):
            for i, v in enumerate((2.5, 0.75, -4.0)):
                self.words[base + i * 4] = word_float(v)
        for offset in range(0, 0xCC, 4):
            self.words.setdefault(pm + 4 + offset, 0)
        self.fail_all = False
        self.total_reads = 0
        self.record_reads = 0
        self.selected_record = pm + 4

    def read_u32(self, address):
        self.total_reads += 1
        if self.selected_record <= address < self.selected_record + 0xCC:
            self.record_reads += 1
        if self.fail_all:
            raise RuntimeError("mock native read error; no raw value")
        return self.words[address]


class FakeController:
    def __init__(self, ns):
        self.ns = ns
        self.calls = []

    def set_wiimote_buttons(self, port, buttons):
        self.calls.append((self.ns["_frame_count"], "button", port,
                           tuple(sorted(buttons.items()))))

    def set_wiimote_swing(self, port, *motion):
        self.calls.append((self.ns["_frame_count"], "swing", port, tuple(motion)))

    def set_wiimote_acceleration(self, port, *accel):
        self.calls.append((self.ns["_frame_count"], "accel", port, tuple(accel)))


def simulate(watch: bool, break_memory_at: int | None = None,
             force_slow_read: bool = False):
    ns = {"_frame_count": 100}
    controller = FakeController(ns)
    memory = FakeMemory()
    ns["controller"] = controller
    ns["memory"] = memory

    # Same pinned generated code as S001 production patch, from a fake
    # upstream-shape fixture; no third-party bridge or Dolphin loaded.
    source = patch_bridge(
        MINIMAL_SOURCE, expected_sha=git_blob_sha(MINIMAL_SOURCE))
    source = extend_atomic_bridge_with_swing(source)
    source = extend_swing_bridge_with_ball_watch(source)
    tree = ast.parse(source)
    assert source.count("    _wii_ball_watch_tick()\n    _wii_ai_tick()") == 1
    tick = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == "_wii_ai_tick")
    exec(_ATOMIC_SNIPPET + _SWING_HANDLER + _BALL_WATCH_HANDLER, ns)
    exec(compile(ast.Module(body=[tick], type_ignores=[]),
                 "<generated-atomic-swing-tick>", "exec"), ns)
    if force_slow_read:
        class SyntheticSlowClock:
            n = 0
            def perf_counter(self):
                self.n += 1
                return self.n * .01
        ns["_wii_ball_time"] = SyntheticSlowClock()
    samples = build_probe("forward", a_setup_frames=12, follow_through_frames=30)
    digest = validate_frozen_trace(samples)
    payload = [[s.hold_a, *s.direction, s.distance_m, s.speed_m_s,
                s.return_speed_m_s, s.angle_rad] for s in samples]
    if watch:
        ns["_wii_ball_watch_arm"]([256, 4])
    else:
        # Keep the same 256 ticks, including idle and prehold. No sampling.
        pass

    step = 0
    def advance(pressed_a_for_prime=False):
        nonlocal step
        step += 1
        ns["_frame_count"] += 1
        if pressed_a_for_prime:
            controller.set_wiimote_buttons(0, {"A": True})
        if break_memory_at is not None and step >= break_memory_at:
            memory.fail_all = True
        if watch:
            ns["_wii_ball_watch_tick"]()
        ns["_wii_ai_tick"]()

    # 24 no-controller-call idle ticks (negative control).
    for _ in range(24):
        advance()
    if watch:
        ns["_wii_ball_watch_stage"](["a_prime"])
    # 45 button-only, no extra motion: mimics the logical A prime.
    for _ in range(45):
        advance(pressed_a_for_prime=True)
    if watch:
        ns["_wii_ball_watch_stage"](["trace"])
    ack = ns["_wii_ai_submit_swing"]([0, payload])
    # 89 samples + 1 completion/release tick.
    for _ in range(len(payload) + 1):
        advance()
    if watch and ns["_wii_ball_watch"] is not None:
        ns["_wii_ball_watch_stage"](["posttrace"])
    # Total 24 + 45 + 90 + 98 = 257 -> watcher reaches COMPLETE on 257th.
    for _ in range(98):
        advance()
    status = ns["_wii_ai_status"]([])
    watch_status = ns["_wii_ball_watch_status"]([]) if watch else None
    sampled = list(ns["_wii_ball_watch_samples"])
    return {
        "calls": controller.calls, "trace_ack": ack,
        "trace_status": status, "watch_status": watch_status,
        "digest": digest,
        "record_reads": memory.record_reads,
        "sampled_record_lengths": [
            len(s["selected_player_record_words_PRIVATE"]) for s in sampled
        ],
        "samples": sampled,
    }


class ExpandedSelectedRecordTraceParityTests(unittest.TestCase):
    def test_89_sample_dispatch_identical_with_and_without_watch(self):
        control = simulate(False)
        watched = simulate(True)
        self.assertEqual(control["calls"], watched["calls"])
        self.assertEqual(control["trace_ack"], watched["trace_ack"])
        self.assertEqual(control["trace_status"], watched["trace_status"])
        self.assertEqual(control["digest"], watched["digest"])
        self.assertEqual(control["trace_status"]["state"], "complete")
        self.assertEqual(control["trace_status"]["applied_frames"], 89)
        self.assertEqual(watched["watch_status"]["state"], "complete")
        self.assertEqual(watched["watch_status"]["samples"], 64)
        motions = [c for c in watched["calls"] if c[1] == "swing"]
        self.assertEqual(len(motions), 35)

    def test_watch_read_failure_keeps_all_controller_commands_identical(self):
        control = simulate(False)
        watched = simulate(True, break_memory_at=100)
        self.assertEqual(control["calls"], watched["calls"])
        self.assertEqual(control["trace_status"], watched["trace_status"])
        self.assertEqual(watched["watch_status"]["state"], "source_gate_failed")
        self.assertEqual(control["trace_status"]["applied_frames"], 89)

    def test_full_record_is_present_at_all_64_bounded_ticks(self):
        watched = simulate(True)
        self.assertEqual(watched["watch_status"]["state"], "complete")
        self.assertEqual(watched["watch_status"]["samples"], 64)
        self.assertEqual(watched["sampled_record_lengths"], [51] * 64)
        self.assertGreaterEqual(watched["record_reads"], 64 * 51)
        self.assertFalse(any("_source_owner_tuple" in sample
                             for sample in watched["samples"]))
        self.assertEqual(
            {sample["input_stage"] for sample in watched["samples"]},
            {"idle_control", "a_prime", "trace", "posttrace"},
        )

    def test_slow_51_word_read_disarms_without_swallowing_swing(self):
        control = simulate(False)
        slow = simulate(True, force_slow_read=True)
        self.assertEqual(slow["watch_status"]["state"], "read_overhead_exceeded")
        self.assertEqual(slow["trace_status"]["state"], "complete")
        self.assertEqual(control["calls"], slow["calls"])
        self.assertEqual(control["digest"], slow["digest"])
        self.assertEqual(control["trace_status"], slow["trace_status"])

    def test_watch_tick_is_not_guest_frame_or_observed_contact(self):
        watched = simulate(True)
        self.assertEqual(watched["trace_ack"]["state"], "scheduled")
        self.assertEqual(watched["watch_status"]["state"], "complete")
        # No game frame / visible hit exists in this entirely synthetic test.
        self.assertNotIn("guest_frame_verified", watched["watch_status"])
        self.assertNotIn("contact", watched["watch_status"])


if __name__ == "__main__":
    unittest.main()
