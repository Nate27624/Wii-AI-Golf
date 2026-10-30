"""Synthetic no-contact P0 source-candidate experiment; never connects to Dolphin."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p0_live_no_contact_compare.py"
SPEC = importlib.util.spec_from_file_location("p0_no_contact", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class FakeRPC:
    def __init__(self):
        self.frame = 0
        self.calls = []
        self.vals = {
            probe.SCENE_STATIC: 0x80010000, probe.SCENE_STATIC + 4: 0,
            0x80010000 + 0x18: 5, 0x80010000 + 0xC: 0x90010000,
            0x90010000: 0x803C7720, 0x90010000 + 0x1C: 5,
            0x90010000 + 0x20: 0x80010000, 0x90010000 + 0x54: 2,
            probe.CONFIG_STATIC: 0x90020000,
            0x90020000 + 0x94: 4, 0x90020000 + 0x98: 0,
            probe.FIELD_STATIC: 0x90030000,
            probe.PLAYER_MANAGER_STATIC: 0x90040000,
            0x90040000: 0x803C7DD4,
            0x90040000 + 0x334: 0x90040004,
            0x90040004 + 0x88: 0x90050000,
            0x90050000: 0x803C7920,
            0x90050000 + 0x4C: 0x90050030,
            0x90030000 + 0x50: 0x90060000,
            0x90030000 + 0x44: 0x90070000,
            0x90060000 + 0x4C: 0x90060030,
            0x90070000 + 0x4C: 0x90070030,
        }

    def call(self, method, params):
        self.calls.append(method)
        if method == "frame.get_count":
            self.frame += 1
            return self.frame
        if method == "memory.read_bytes":
            assert params == [0x80000000, 8]
            return b"RSPE01\x00\x01".hex()
        if method == "memory.read_u32":
            return self.vals.get(params[0], 0)
        raise AssertionError("non-read bridge method: " + method)


class NoContactExperimentTests(unittest.TestCase):
    def test_idle_control_and_aim_only_candidate(self):
        rpc = FakeRPC()
        b0 = probe.take_snapshot(rpc)
        b1 = probe.take_snapshot(rpc)
        rpc.vals[0x90040004 + 0x3C] = 42
        a0 = probe.take_snapshot(rpc)
        result = probe.summarize(b0, b1, a0)
        self.assertEqual(result["idle_repeat_changed_components"]["aim_candidate_plus_0x3c"], 0)
        self.assertEqual(result["aim_only_changed_components"]["aim_candidate_plus_0x3c"], 1)
        self.assertEqual(result["fields_stable_in_idle_but_changed_aim_only"], ["aim_candidate_plus_0x3c"])
        self.assertFalse(result["training_approved"])
        self.assertFalse(result["guest_physics_frame_verified"])
        self.assertFalse(result["contact_verified"])
        self.assertTrue(set(rpc.calls) <= {"frame.get_count", "memory.read_u32", "memory.read_bytes"})

    def test_wrong_scene_rejected(self):
        rpc = FakeRPC()
        rpc.vals[0x80010000 + 0x18] = 9
        with self.assertRaisesRegex(ValueError, "Golf scene"):
            probe.take_snapshot(rpc)

    def test_wrong_revision_rejected(self):
        rpc = FakeRPC()
        original = rpc.call

        def changed(method, params):
            if method == "memory.read_bytes":
                return b"RSPE01\x00\x00".hex()
            return original(method, params)

        rpc.call = changed
        with self.assertRaisesRegex(ValueError, "Rev1"):
            probe.take_snapshot(rpc)

    def test_cross_hole_rejected(self):
        rpc = FakeRPC()
        b0 = probe.take_snapshot(rpc)
        rpc.vals[0x90020000 + 0x98] = 1
        with self.assertRaisesRegex(ValueError, "identity"):
            probe.compare(b0, probe.take_snapshot(rpc))

    def test_selected_ball_identity_changed_rejected(self):
        rpc = FakeRPC()
        b0 = probe.take_snapshot(rpc)
        rpc.vals[0x90040004 + 0x88] = 0x90051000
        rpc.vals[0x90051000] = 0x803C7920
        rpc.vals[0x90051000 + 0x4C] = 0x90051030
        with self.assertRaisesRegex(ValueError, "identity"):
            probe.compare(b0, probe.take_snapshot(rpc))

    def test_host_frame_reversal_rejected(self):
        rpc = FakeRPC()
        b0 = probe.take_snapshot(rpc)
        b1 = probe.take_snapshot(rpc)
        b1["frame_bracket"] = (0, 1)
        with self.assertRaisesRegex(ValueError, "sequence"):
            probe.compare(b0, b1)

    def test_invalid_memory_address_and_bool_rejected(self):
        self.assertFalse(probe.in_bank(True))
        self.assertFalse(probe.in_bank(0x81FFFFFF, 12))
        self.assertFalse(probe.in_bank(0x8FFFFFFF))
        self.assertTrue(probe.in_bank(0x804BF868, bank="MEM1"))
        self.assertFalse(probe.in_bank(0x804BF868, bank="MEM2"))

    def test_launcher_and_source_contain_no_active_bridge_methods(self):
        script_text = SCRIPT.read_text(encoding="utf-8")
        launcher = (SCRIPT.parent / "run_p0_live_no_contact_compare.ps1").read_text(encoding="utf-8")
        self.assertIn("--selftest", launcher)
        self.assertIn("P0 read-only", launcher)
        for prohibited in ("controller.set", "memory.write", "savestate.load", "start-process",
                           "send-live-probe", "swing.dispatch", "mcp_bridge_swing_atomic"):
            with self.subTest(prohibited=prohibited):
                self.assertNotIn(prohibited, (script_text + launcher).lower())


if __name__ == "__main__":
    unittest.main()
