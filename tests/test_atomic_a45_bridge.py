"""No emulator: synthetic execution of the actual generated A45 bridge patch."""
from __future__ import annotations
import ast
import unittest
import tempfile
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from wii_ai_golf.integration.atomic_a45_patch import (
    patch_isolated_v1_bridge, AtomicA45PatchError)
from wii_ai_golf.integration.atomic_a45_client import AtomicA45SwingTraceClient
from wii_ai_golf.integration.swing_client import SwingSample
from scripts.probe_swing import build_probe
from scripts.collect_outcome_transition import _build_v1_trace_and_digest
from scripts.prepare_atomic_a45_bridge import prepare


# A tiny simulated ORIGINAL V1 bridge. The test executes the actual injection,
# not a reimplementation of the new A45 callback.
FAKE_V1 = """# WII_AI_GOLF_ATOMIC_TRACE_V1
# WII_AI_GOLF_SWING_TRACE_V1
_wii_ai_trace = None
_wii_ai_trace_status = {"state": "idle"}
_wii_ai_trace_next_id = 0
_frame_count = 100

def _wii_ai_submit_swing(p):
    global _wii_ai_trace, _wii_ai_trace_status, _wii_ai_trace_next_id
    if _wii_ai_trace is not None:
        raise RuntimeError("trace active")
    port, samples = p
    if type(port) is not int or port not in range(4):
        raise ValueError("bad port")
    if len(samples) != 89 or any(len(s) != 8 for s in samples):
        raise ValueError("bad waveform")
    _wii_ai_trace_next_id += 1
    _wii_ai_trace = {"id": _wii_ai_trace_next_id, "port": port,
                     "samples": samples, "start": _frame_count + 1,
                     "applied": 0, "kind": "swing"}
    _wii_ai_trace_status = {"id": _wii_ai_trace_next_id, "state": "scheduled",
                            "kind": "swing", "applied_frames": 0}
    return dict(_wii_ai_trace_status)


def _wii_ai_tick():
    global _wii_ai_trace, _wii_ai_trace_status
    t = _wii_ai_trace
    if t is None or _frame_count < t["start"]:
        return
    index = _frame_count - t["start"]
    if index < len(t["samples"]):
        sample = t["samples"][index]
        controller.set_wiimote_buttons(t["port"], {"A": sample[0]})
        controller.set_wiimote_swing(t["port"], *sample[1:])
        t["applied"] += 1
        _wii_ai_trace_status = {"id": t["id"], "state": "running",
                                "applied_frames": t["applied"]}
    else:
        controller.set_wiimote_buttons(t["port"], {"A": False})
        _wii_ai_trace_status = {"id": t["id"], "state": "complete",
                                "applied_frames": t["applied"]}
        _wii_ai_trace = None


HANDLERS = {
    "trace.submit_swing": _wii_ai_submit_swing,
}

async def fake_loop():
    _wii_ai_tick()
    _poll_sockets()
"""


class Controller:
    def __init__(self, ns):
        self.ns = ns
        self.calls = []

    def set_wiimote_buttons(self, port, buttons):
        self.calls.append((self.ns["_frame_count"], "buttons", port, dict(buttons)))

    def set_wiimote_swing(self, port, *motion):
        self.calls.append((self.ns["_frame_count"], "swing", port, motion))


class AtomicA45BridgeTests(unittest.TestCase):
    def make_bridge(self):
        source = patch_isolated_v1_bridge(FAKE_V1)
        self.assertIn("# WII_AI_GOLF_ATOMIC_A45_BRIDGE_V1", source)
        ns = {"_poll_sockets": lambda: None}
        ns["controller"] = Controller(ns)
        exec(compile(source, "fake_a45_bridge.py", "exec"), ns)
        return ns

    def test_one_frame_callback_action_has_45_button_only_then_frozen_89(self):
        ns = self.make_bridge()
        _, expected = _build_v1_trace_and_digest(
            motion_scale=1.0, speed_scale=1.0, backswing_scale=1.0)
        samples = build_probe("forward", follow_through_frames=30)
        self.assertEqual(len(samples), 89)
        payload = [[s.hold_a, *s.direction, s.distance_m,
                    s.speed_m_s, s.return_speed_m_s, s.angle_rad] for s in samples]
        self.assertEqual(ns["HANDLERS"]["trace.atomic_a45_capabilities"]([])["lead_frames"], 45)
        scheduled = ns["HANDLERS"]["trace.submit_atomic_a45"]([0, payload])
        self.assertEqual(scheduled["prehold_applied_frames"], 0)
        for _ in range(45 + 89 + 1):
            ns["_frame_count"] += 1
            ns["_wii_ai_golf_atomic_a45_tick"]()
        calls = ns["controller"].calls
        self.assertEqual(calls[:45], [(101 + i, "buttons", 0, {"A": True})
                                      for i in range(45)])
        first_swing = next(i for i, call in enumerate(calls) if call[1] == "swing")
        self.assertEqual(calls[first_swing][0], 146)
        self.assertEqual(calls[first_swing - 1], (146, "buttons", 0, {"A": True}))
        self.assertEqual(len([x for x in calls if x[1] == "swing"]), 89)
        # The generated bridge must preserve the COMPLETE legacy V1 schedule,
        # not only the 45 A-true lead and its first swing callback. V1 calls
        # set_wiimote_swing on neutral samples too (unlike the V2 bridge).
        expected_events = [(101 + i, "buttons", 0, {"A": True})
                           for i in range(45)]
        for index, sample in enumerate(payload):
            frame = 146 + index
            expected_events.append((frame, "buttons", 0, {"A": sample[0]}))
            expected_events.append((frame, "swing", 0, tuple(sample[1:])))
        expected_events.append((235, "buttons", 0, {"A": False}))
        self.assertEqual(calls, expected_events)
        buttons = [event for event in calls if event[1] == "buttons"]
        self.assertEqual(len(buttons), 135)
        self.assertEqual([event[0] for event in buttons], list(range(101, 236)))
        self.assertEqual([event[3]["A"] for event in buttons],
                         [True] * (45 + 77) + [False] * (12 + 1))
        swing_calls = [event for event in calls if event[1] == "swing"]
        self.assertEqual(sum(any(value != 0 for value in event[3])
                             for event in swing_calls), 35)
        self.assertEqual(sum(all(value == 0 for value in event[3])
                             for event in swing_calls), 54)
        self.assertEqual(ns["_wii_ai_trace_status"]["state"], "complete")
        self.assertEqual(ns["_wii_ai_trace_status"]["prehold_applied_frames"], 45)
        self.assertEqual(ns["_wii_ai_trace_status"]["applied_frames"], 89)
        self.assertEqual(ns["_wii_ai_trace_status"]["trace_start_frame"], 146)
        self.assertEqual(ns["_wii_ai_trace_status"]["last_prehold_frame"], 145)
        self.assertFalse(ns["_wii_ai_trace_status"]["game_a_recognition_verified"])

    def test_skipped_bridge_callback_aborts_before_any_motion(self):
        ns = self.make_bridge()
        payload = [[s.hold_a, *s.direction, s.distance_m,
                    s.speed_m_s, s.return_speed_m_s, s.angle_rad]
                   for s in build_probe("forward")]
        ns["HANDLERS"]["trace.submit_atomic_a45"]([0, payload])
        ns["_frame_count"] = 101
        ns["_wii_ai_golf_atomic_a45_tick"]()
        ns["_frame_count"] = 103  # callback 102 absent: cannot prove hold
        ns["_wii_ai_golf_atomic_a45_tick"]()
        self.assertEqual(ns["_wii_ai_trace_status"]["state"], "error")
        self.assertEqual(ns["_wii_ai_trace_status"]["error"], "a45_callback_gap")
        self.assertIsNone(ns["_wii_ai_trace"])
        self.assertFalse(any(x[1] == "swing" for x in ns["controller"].calls))
        self.assertEqual(ns["controller"].calls[-1][-1], {"A": False})

    def test_local_preparation_never_overwrites_conflicting_output_or_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "legacy.py"
            output = Path(tmp) / "atomic.py"
            source.write_text(FAKE_V1, encoding="utf-8")
            report = prepare(source, output)
            self.assertTrue(output.is_file())
            self.assertEqual(source.read_text(encoding="utf-8"), FAKE_V1)
            self.assertFalse(report["dolphin_launched"])
            self.assertFalse(report["bridge_loaded_in_runtime_verified"])
            self.assertEqual(prepare(source, output)["sha256"], report["sha256"])
            output.write_text("unrelated live bridge", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                prepare(source, output)
            self.assertEqual(output.read_text(), "unrelated live bridge")
            with self.assertRaises(ValueError):
                prepare(source, source)

    def test_original_handler_and_source_are_not_replaced(self):
        ns = self.make_bridge()
        self.assertIn("trace.submit_swing", ns["HANDLERS"])
        self.assertEqual(ns["HANDLERS"]["trace.submit_swing"],
                         ns["_wii_ai_submit_swing"])
        for bad in (FAKE_V1.replace("TRACE_V1", "BROKEN"),
                    FAKE_V1 + "# WII_AI_GOLF_SWING_NEUTRAL_BUTTON_ONLY_V2",
                    patch_isolated_v1_bridge(FAKE_V1)):
            with self.subTest(bad=bad[-30:]), self.assertRaises(AtomicA45PatchError):
                patch_isolated_v1_bridge(bad)

    def test_wrong_trace_pattern_refused_without_scheduling(self):
        ns = self.make_bridge()
        payload = [[s.hold_a, *s.direction, s.distance_m,
                    s.speed_m_s, s.return_speed_m_s, s.angle_rad]
                   for s in build_probe("forward")]
        payload[30][0] = False
        with self.assertRaisesRegex(ValueError, "shape"):
            ns["HANDLERS"]["trace.submit_atomic_a45"]([0, payload])
        self.assertIsNone(ns["_wii_ai_trace"])


class AtomicA45ClientTests(unittest.TestCase):
    def test_capability_refused_before_submission(self):
        class RPC:
            calls = []
            def call(self, name, _args):
                self.calls.append(name)
                raise RuntimeError("unknown method")
        rpc = RPC()
        with self.assertRaisesRegex(RuntimeError, "lacks atomic A45"):
            AtomicA45SwingTraceClient(rpc).run(build_probe("forward"))
        self.assertEqual(rpc.calls, ["trace.atomic_a45_capabilities"])

    def test_strict_receipt_and_same_trace_length(self):
        class RPC:
            state = "scheduled"
            calls = []
            def call(self, method, args):
                self.calls.append(method)
                if method == "trace.atomic_a45_capabilities":
                    return {"atomic_a45_protocol": 1, "lead_frames": 45,
                            "button_only_lead": True, "atomic_swing_followup": True}
                if method == "trace.submit_atomic_a45":
                    assert len(args[1]) == 89
                    return {"state": "scheduled", "kind": "atomic_a45_swing",
                            "id": 17, "prehold_requested_frames": 45,
                            "applied_frames": 0}
                if method == "trace.status":
                    return {"state": "complete", "id": 17, "kind": "atomic_a45_swing",
                            "applied_frames": 89, "prehold_applied_frames": 45,
                            "prehold_start_frame": 120, "last_prehold_frame": 164,
                            "trace_start_frame": 165,
                            "game_a_recognition_verified": False}
                raise AssertionError(method)
        rpc = RPC()
        result = AtomicA45SwingTraceClient(rpc).run(build_probe("forward"))
        self.assertEqual(result["prehold_applied_frames"], 45)
        self.assertEqual(rpc.calls[:2],
                         ["trace.atomic_a45_capabilities", "trace.submit_atomic_a45"])


if __name__ == "__main__":
    unittest.main()
