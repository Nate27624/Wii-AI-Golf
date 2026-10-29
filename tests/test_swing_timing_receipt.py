"""Synthetic B1 bridge-timing audit; cannot start Dolphin or a shot."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.audit.swing_timing_receipt import audit_b1_timing_receipt, V1_PHASES


def receipt():
    return {
        "known_good_swing_request": {
            "preset": "forward",
            "generated_trace_frames": 89,
            "a_lead_requested_frames": 45,
            "a_lead_observed_frame_delta": 45,
            "a_lead_start_frame": 100,
            "a_lead_last_observed_frame": 145,
            "a_button_only_prime_requests": 46,
            "per_observed_frame_a_reasserted": True,
            "a_button_prime_applied": True,
            "a_priming_evidence": "frame_observed_A_requested_not_game_verified",
        },
        "swing_dispatch": {
            "state": "complete",
            "total_frames": 89,
            "applied_frames": 89,
            "start_frame": 148,
            "completion_dispatch_frame": 237,
        },
        "human_observation": {"contact_human": "yes", "private_extra": "DO_NOT_PRINT"},
    }


class B1BridgeTimingReceiptTests(unittest.TestCase):
    def test_baseline_a45_gap_and_phase_boundaries(self):
        got = audit_b1_timing_receipt(receipt())
        self.assertEqual(got["status"], "bridge_counter_arithmetic_consistent_only")
        self.assertEqual(got["unobserved_bridge_ticks_before_trace_start"], 2)
        self.assertEqual(got["phase_start_bridge_frames"], {
            "neutral_A": 148, "backswing_A": 160,
            "forward_A": 175, "followthrough_A": 195, "released_A": 225,
        })
        self.assertEqual(tuple(x[2] - x[1] for x in V1_PHASES),
                         (12, 15, 20, 30, 12))
        self.assertEqual(got["trace_A_requested_samples"], 77)
        self.assertEqual(got["frame_scoped_A_reassertion_requests"], 46)
        self.assertEqual(got["trace_A_released_samples"], 12)
        for field in ("game_a_latch_verified", "guest_physics_frame_join_verified",
                      "ball_contact_verified", "training_allowed"):
            self.assertIs(got[field], False)
        self.assertNotIn("DO_NOT_PRINT", str(got))
        self.assertNotIn("human_observation", str(got))

    def test_a90_is_one_pretrace_factor_not_a_different_waveform(self):
        child = receipt()
        req = child["known_good_swing_request"]
        req["a_lead_requested_frames"] = 90
        req["a_button_only_prime_requests"] = 91
        req["a_lead_observed_frame_delta"] = 90
        req["a_lead_last_observed_frame"] = 190
        child["swing_dispatch"]["start_frame"] = 191
        child["swing_dispatch"]["completion_dispatch_frame"] = 280
        got = audit_b1_timing_receipt(child)
        self.assertEqual(got["status"], "bridge_counter_arithmetic_consistent_only")
        self.assertEqual(got["requested_A_lead_bridge_frames"], 90)
        self.assertEqual(got["unobserved_bridge_ticks_before_trace_start"], 0)
        self.assertEqual(got["phase_start_bridge_frames"]["forward_A"], 218)

    def test_legacy_single_rpc_prehold_abstains_despite_45_frame_counter(self):
        child = receipt()
        request = child["known_good_swing_request"]
        request["a_button_only_prime_requests"] = 1
        request.pop("per_observed_frame_a_reasserted")
        out = audit_b1_timing_receipt(child)
        self.assertEqual(out["status"], "abstain_single_rpc_A_not_held_across_frames")
        self.assertFalse(out["game_a_latch_verified"])
        self.assertNotIn("unobserved_bridge_ticks_before_trace_start", out)

    def test_new_helper_old_collector_one_request_claim_abstains(self):
        child = receipt()
        child["known_good_swing_request"]["a_button_only_prime_requests"] = 1
        got = audit_b1_timing_receipt(child)
        self.assertEqual(got["status"],
                         "abstain_missing_or_inconsistent_A_reassertion_receipt")

    def test_unverified_frame_refresh_marker_abstains(self):
        child = receipt()
        child["known_good_swing_request"]["per_observed_frame_a_reasserted"] = False
        got = audit_b1_timing_receipt(child)
        self.assertEqual(got["status"],
                         "abstain_missing_or_inconsistent_A_reassertion_receipt")

    def test_missing_or_malformed_counters_fail_closed(self):
        for name in ("lead_requested", "lead_observed", "lead_start",
                     "lead_last", "trace_start", "trace_completion"):
            mapping = {
                "lead_requested": ("known_good_swing_request", "a_lead_requested_frames"),
                "lead_observed": ("known_good_swing_request", "a_lead_observed_frame_delta"),
                "lead_start": ("known_good_swing_request", "a_lead_start_frame"),
                "lead_last": ("known_good_swing_request", "a_lead_last_observed_frame"),
                "trace_start": ("swing_dispatch", "start_frame"),
                "trace_completion": ("swing_dispatch", "completion_dispatch_frame"),
            }
            outer, key = mapping[name]
            for bad in (None, -1, True, "45"):
                with self.subTest(name=name, bad=bad):
                    child = receipt()
                    child[outer][key] = bad
                    got = audit_b1_timing_receipt(child)
                    self.assertNotEqual(got["status"], "bridge_counter_arithmetic_consistent_only")
                    self.assertFalse(got["ball_contact_verified"])

    def test_missing_status_wrong_waveform_or_no_lead_abstains(self):
        for outer, key, bad in (
            ("swing_dispatch", "state", "scheduled"),
            ("swing_dispatch", "applied_frames", 88),
            ("swing_dispatch", "total_frames", 122),
            ("known_good_swing_request", "generated_trace_frames", 122),
            ("known_good_swing_request", "a_lead_requested_frames", 0),
            ("known_good_swing_request", "a_button_only_prime_requests", 45),
        ):
            with self.subTest(field=key):
                child = receipt()
                child[outer][key] = bad
                out = audit_b1_timing_receipt(child)
                self.assertTrue(out["status"].startswith("abstain"))
                self.assertFalse(out["training_allowed"])

    def test_frame_sequence_arithmetic_refuses_contradictions(self):
        for outer, key, bad in (
            ("known_good_swing_request", "a_lead_observed_frame_delta", 30),
            ("known_good_swing_request", "a_lead_last_observed_frame", 140),
            ("swing_dispatch", "start_frame", 145),
            ("swing_dispatch", "completion_dispatch_frame", 235),
        ):
            child = receipt()
            child[outer][key] = bad
            got = audit_b1_timing_receipt(child)
            self.assertEqual(got["status"], "abstain_contradictory_bridge_counters")
            self.assertNotIn("unobserved_bridge_ticks_before_trace_start", got)


if __name__ == "__main__":
    unittest.main()
