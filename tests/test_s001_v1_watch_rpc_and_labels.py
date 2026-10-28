"""Synthetic private-watch transport sizing and human-label integrity tests.

No Dolphin, RPC networking, or raw game data. Keep this stacked review-only.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import record_selected_ball_swing_v1_private as v1


class V1EvidenceAndTransportTests(unittest.TestCase):
    def test_70_record_private_json_exceeds_default_64k_but_fits_bound(self):
        # Worst-case decimal width for u32s and plausible f32 vectors.
        row = {
            "frame_tick_index": 123456, "trace_id_if_active": 123456,
            "trace_sample_index_if_active": 88,
            "selected_slot_candidate": 3, "source_hole_index": 8,
            "ball_translation_f32_candidate": [123.987654, 123.987654, 123.987654],
            "record_translation_f32_candidate": [123.987654, 123.987654, 123.987654],
            "selected_player_record_words_PRIVATE": [4294967295] * 51,
            "current_start_f32_candidate": [123.987654, 123.987654, 123.987654],
            "source_owner_consistent": True,
            "input_stage": "posttrace", "read_overhead_us": 5000
        }
        payload = {"status": {"state": "complete", "samples": 70},
                   "samples": [row] * 70}
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.assertGreater(len(encoded), 65536)
        self.assertLess(len(encoded), v1.WATCH_RESPONSE_CAP_BYTES)
        self.assertLessEqual(v1.WATCH_RESPONSE_CAP_BYTES, 262144)

    def test_dedicated_rpc_uses_bound_not_global_default(self):
        class Capture:
            def __init__(self, **kwargs):
                self.arguments = kwargs
        with patch.object(v1, "FelkRPC", Capture):
            configured = v1.watched_v1_rpc(port=55355)
        self.assertEqual(configured.arguments["max_response_bytes"], 262144)
        self.assertEqual(configured.arguments["port"], 55355)
        self.assertEqual(configured.arguments["timeout_s"], 15)

    def test_contact_yes_and_movement_no_stay_distinct(self):
        answers = iter(["yes", "no"])
        prompts = []
        def fake_input(p):
            prompts.append(p)
            return next(answers)
        human = v1.ask_distinct_human_labels(input_fn=fake_input)
        self.assertEqual(human, {"contact_human": "yes",
                                 "ball_movement_human": "no"})
        self.assertIn("struck", prompts[0])
        self.assertIn("move", prompts[1])
        self.assertNotEqual(human["contact_human"], human["ball_movement_human"])

    def test_unknown_is_not_silently_promoted(self):
        human = v1.ask_distinct_human_labels(input_fn=lambda p: "")
        self.assertEqual(human["contact_human"], "unknown")
        self.assertEqual(human["ball_movement_human"], "unknown")

    def test_invalid_human_labels_become_unknown_not_yes(self):
        answers = iter(["perhaps", "yes"])
        human = v1.ask_distinct_human_labels(input_fn=lambda p: next(answers))
        self.assertEqual(human["contact_human"], "unknown")
        self.assertEqual(human["ball_movement_human"], "yes")

    def test_shared_rpc_defaults_unchanged(self):
        from wii_ai_golf.integration.rpc import FelkRPC
        self.assertEqual(FelkRPC().max_response_bytes, 65536)


if __name__ == "__main__":
    unittest.main()
