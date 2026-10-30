"""Synthetic only: directional aim time-series with no Dolphin/game access."""
from __future__ import annotations

from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import p0_live_directional_aim_series as series
from test_p0_live_no_contact_compare import FakeRPC


def bits(value):
    return int.from_bytes(struct.pack(">f", value), "big")


class DirectionalSeriesTests(unittest.TestCase):
    def test_packet_reuses_source_gates_and_extra_candidate_words(self):
        rpc = FakeRPC()
        packet = series.packet(rpc, "B0", 0)
        self.assertEqual(len(packet["words"][series.EXTRA[0]]), 3)
        self.assertEqual(len(packet["words"][series.EXTRA[1]]), 3)
        self.assertTrue(set(rpc.calls) <= {"frame.get_count", "memory.read_u32", "memory.read_bytes"})

    def test_intra_packet_owner_mutation_abstains(self):
        rpc = FakeRPC()
        original = rpc.call
        def changed(method, params):
            if method == "memory.read_u32" and params == [0x90040000 + 0x334] and rpc.frame >= 2:
                return 0x90040100
            return original(method, params)
        rpc.call = changed
        with self.assertRaisesRegex(ValueError, "intra-packet"):
            series.packet(rpc, "B0", 0)

    def test_scene_mode_guard(self):
        rpc = FakeRPC()
        rpc.vals[0x90020000 + 0x94] = 3
        with self.assertRaisesRegex(ValueError, "mode"):
            series.packet(rpc, "B0", 0)

    def test_directional_reversibility_and_new_channels(self):
        rpc = FakeRPC()
        events = []
        for phase, _ in series.PHASES:
            value = {"B0": 2.0, "B1": 2.0, "L1": 2.5, "C1": 2.0,
                     "R1": 1.5, "C2": 2.0, "L2": 2.5}[phase]
            rpc.vals[0x90040004 + 0x3C] = bits(value)
            for i in range(2):
                events.append(series.packet(rpc, phase, i))
        summary = series.sanitize(events, 2)
        self.assertTrue(summary["directional_float32_hypothesis_opposite_signs"])
        self.assertTrue(summary["left_repeat_exact_word_pattern"])
        self.assertTrue(summary["recenter_C1_exact_B0_word"])
        self.assertTrue(summary["recenter_C2_exact_B0_word"])
        self.assertEqual(summary["phase_metrics"]["L1"]["aim_float32_hypothesis_delta_vs_B0"], 0.5)
        self.assertEqual(summary["phase_metrics"]["R1"]["aim_float32_hypothesis_delta_vs_B0"], -0.5)
        self.assertEqual(summary["new_candidate_channels"], list(series.EXTRA))
        self.assertFalse(summary["training_approved"])
        self.assertFalse(summary["guest_physics_step_verified"])

    def test_negative_with_no_change_is_not_dropped(self):
        rpc = FakeRPC()
        events = [series.packet(rpc, phase, i) for phase, _ in series.PHASES for i in range(2)]
        summary = series.sanitize(events, 2)
        self.assertFalse(summary["directional_float32_hypothesis_opposite_signs"])
        self.assertEqual(summary["phase_metrics"]["R1"]["aim_unique_word_patterns"], 1)
        self.assertFalse(summary["training_approved"])

    def test_cross_session_identity_rejected(self):
        rpc = FakeRPC()
        events = [series.packet(rpc, phase, i) for phase, _ in series.PHASES for i in range(2)]
        altered = dict(events[-1])
        altered["identity"] = (*altered["identity"][:-1], 7)
        events[-1] = altered
        with self.assertRaisesRegex(ValueError, "identity"):
            series.sanitize(events, 2)

    def test_missing_packet_rejected(self):
        rpc = FakeRPC()
        events = [series.packet(rpc, phase, i) for phase, _ in series.PHASES for i in range(2)]
        with self.assertRaisesRegex(ValueError, "phase"):
            series.sanitize(events[:-1], 2)

    def test_typed_float_guard(self):
        self.assertIsNone(series.typed_float(0x7FC00000))
        self.assertIsNone(series.typed_float(True))
        self.assertIsNone(series.typed_float(-1))
        self.assertEqual(series.typed_float(bits(2.5)), 2.5)

    def test_script_does_not_send_controller_input(self):
        source=(ROOT / "scripts" / "p0_live_directional_aim_series.py").read_text(encoding="utf-8")
        ps=(ROOT / "scripts" / "run_p0_live_directional_aim_series.ps1").read_text(encoding="utf-8").lower()
        self.assertIn("--samples-per-phase", source)
        self.assertIn("green-pre-start", ps)
        self.assertIn("--attach-running", ps)
        self.assertNotIn("--swing", ps)
        for method in ('rpc.call("controller.', 'rpc.call("memory.write', "savestate.save"):
            self.assertNotIn(method, source)


if __name__ == "__main__":
    unittest.main()
