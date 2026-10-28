"""Actual generated swing tick, mocked controller, before/after observer parity.

NO game, no real RAM, no sockets, no live Dolphin. This exercises the exact
source-pinned generator's emitted _wii_ai_tick function with an injected
single read-only native-word observer just before each controller dispatch.
"""
from __future__ import annotations

import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from wii_ai_golf.integration.atomic_patch import (
    _ATOMIC_SNIPPET, git_blob_sha, patch_bridge,
)
from wii_ai_golf.integration.swing_patch import (
    _SWING_HANDLER, extend_atomic_bridge_with_swing,
)
from wii_ai_golf.integration.ball_watch_preflight import (
    sample_pre_dispatch, UnverifiedSample,
)
from test_ball_watch_preflight import fake_memory

# This is a pure source-injection fixture: no external emulator or vendor file.
UPSTREAM_SHAPE = (
    'HANDLERS = {\n'
    '    "frame.get_count":                _frame_get_count,\n'
    '}\n'
    'while True:\n'
    '    await event.frameadvance()\n'
    '    _frame_count += 1\n'
    '    _poll_sockets()\n'
)


class FakeController:
    def __init__(self, ns):
        self.ns = ns
        self.log = []

    def set_wiimote_buttons(self, port, buttons):
        self.log.append((self.ns["_frame_count"], "buttons", port, dict(buttons)))

    def set_wiimote_swing(self, port, *params):
        self.log.append((self.ns["_frame_count"], "swing", port, tuple(params)))

    def set_wiimote_acceleration(self, port, x, y, z):
        self.log.append((self.ns["_frame_count"], "accel", port, (x, y, z)))


def run_fake_trace(*, observe=False, break_memory=False):
    ns = {"_frame_count": 100}
    ctl = FakeController(ns)
    ns["controller"] = ctl
    exec(_ATOMIC_SNIPPET + _SWING_HANDLER, ns)
    src = patch_bridge(UPSTREAM_SHAPE, expected_sha=git_blob_sha(UPSTREAM_SHAPE))
    src = extend_atomic_bridge_with_swing(src)
    tree = ast.parse(src)
    tick = next(x for x in tree.body if
                isinstance(x, ast.FunctionDef) and x.name == "_wii_ai_tick")
    exec(compile(ast.Module(body=[tick], type_ignores=[]), "<fake-tick>", "exec"), ns)

    # Minimal A-held waveform; not the full real V1 and no input in Dolphin.
    waveform = [
        [True, 0, -1, 0, 0.30, 2, 1, 0],
        [True, 0, 1, 0, 0.30, 2, 1, 0],
        [True, 0, 0, 0, 0, 0, 0, 0],
        [False, 0, 0, 0, 0, 0, 0, 0],
    ]
    ack = ns["_wii_ai_submit_swing"]([0, waveform])
    words, _ = fake_memory()
    private_frames = []
    failed_reads = 0
    for i in range(len(waveform) + 1):
        ns["_frame_count"] += 1
        if observe and i < len(waveform):
            stage = ("idle_before", "idle_after", "event_before", "event_after")[i]
            def r(addr):
                if break_memory:
                    raise RuntimeError("synthetic broken native read")
                return words[addr]
            try:
                private_frames.append(sample_pre_dispatch(
                    read_u32=r, bridge_tick=lambda: ns["_frame_count"],
                    stage=stage, source_contract_reviewed=True))
            except UnverifiedSample:
                failed_reads += 1
        # The exact source-generated swing tick must remain untouched.
        ns["_wii_ai_tick"]()
    return {
        "ack": ack,
        "calls": ctl.log,
        "status": ns["_wii_ai_status"]([]),
        "private_snapshots": private_frames,
        "failed_reads": failed_reads,
    }


class GeneratedSwingObserverParityTests(unittest.TestCase):
    def test_fake_observer_does_not_change_a_or_motion_dispatch(self):
        a, b = run_fake_trace(observe=False), run_fake_trace(observe=True)
        self.assertEqual(a["calls"], b["calls"])
        self.assertEqual(a["ack"], b["ack"])
        self.assertEqual(a["status"], b["status"])
        self.assertEqual(len(b["private_snapshots"]), 4)
        self.assertEqual(b["failed_reads"], 0)
        self.assertEqual(b["status"]["state"], "complete")
        self.assertEqual(b["status"]["applied_frames"], 4)
        self.assertEqual([x[1] for x in b["calls"]],
                         ["buttons", "swing", "buttons", "swing",
                          "buttons", "buttons", "buttons"])

    def test_failed_native_observer_does_not_invent_game_sample_or_dispatch(self):
        plain = run_fake_trace(observe=False)
        failed = run_fake_trace(observe=True, break_memory=True)
        self.assertEqual(failed["calls"], plain["calls"])
        self.assertEqual(failed["status"], plain["status"])
        self.assertEqual(failed["private_snapshots"], [])
        self.assertEqual(failed["failed_reads"], 4)

    def test_no_emulated_game_frame_verification_from_synthetic_tick(self):
        observed = run_fake_trace(observe=True)
        self.assertTrue(all(
            not snap["bridge_tick_verified_as_emulated_game_frame"]
            for snap in observed["private_snapshots"]
        ))
        self.assertTrue(all(
            snap["bridge_tick_start"] == snap["bridge_tick_end"]
            for snap in observed["private_snapshots"]
        ))


if __name__ == "__main__":
    unittest.main()
