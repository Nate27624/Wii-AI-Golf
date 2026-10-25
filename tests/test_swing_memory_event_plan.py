"""Synthetic only: never dispatch input or read game memory."""
from __future__ import annotations

from dataclasses import replace
import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import plan_swing_memory_events as m
from probe_swing import build_probe


class V1SwingMemoryPlanTests(unittest.TestCase):
    def test_matches_actual_published_human_contact_v1_waveform(self):
        trace = build_probe("forward", follow_through_frames=30,
                            a_setup_frames=12)
        out = m.plan(trace)
        self.assertEqual(out["trace_samples"], 89)
        self.assertEqual(out["trace_sha256"], m.EXPECTED_BASELINE_SHA256)
        self.assertEqual([p["phase"] for p in out["phases"]],
                         list(m.PHASES))
        self.assertEqual([(p["sample_start_zero_based"], p["sample_end_zero_based"])
                          for p in out["phases"]],
                         [(0,11), (12,26), (27,46), (47,76), (77,88)])
        self.assertEqual([e["sample_index_zero_based"]
                          for e in out["proposed_tick_read_markers"]],
                         list(m.PROBE_EVENT_INDICES))
        self.assertFalse(out["game_frame_alignment_verified"])
        self.assertFalse(out["golf_power_field_verified"])
        self.assertFalse(out["a_lead_game_verified"])

    def test_one_variable_mutation_must_not_masquerade_as_baseline(self):
        base = build_probe("forward")
        modified = list(base)
        modified[30] = replace(modified[30], speed_m_s=2.9)
        with self.assertRaisesRegex(ValueError, "digest"):
            m.plan(modified)

    def test_changed_a_or_unexpected_release_rejected(self):
        base = build_probe("forward")
        altered = list(base)
        altered[20] = replace(altered[20], hold_a=False)
        with self.assertRaises(ValueError):
            m.plan(altered)
        altered = list(base)
        altered[88] = replace(altered[88], distance_m=0.1)
        with self.assertRaisesRegex(ValueError, "Release"):
            m.plan(altered)

    def test_reject_wrong_trace_length_and_a_lead(self):
        base = build_probe("forward")
        with self.assertRaises(ValueError):
            m.plan(base[:-1])
        with self.assertRaises(ValueError):
            m.plan(base, observed_a_lead_requested=44)

    def test_offline_plan_does_not_call_live_bridge(self):
        with patch("plan_swing_memory_events.build_probe",
                   wraps=build_probe) as getter:
            self.assertEqual(m.main(), 0)
            getter.assert_called_once_with(
                "forward", follow_through_frames=30, a_setup_frames=12)


if __name__ == "__main__":
    unittest.main()
