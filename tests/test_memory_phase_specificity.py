"""S002 per-offset phase controls; deterministic synthetic RAM only."""
from __future__ import annotations
import json
import struct
import unittest
from wii_ai_golf.audit.memory_phases import summarize_phase_memory


def sample(stage, phase, value, number, *, address=0x80010000, revision=1):
    config = bytearray(0xA0)
    struct.pack_into(">I", config, 0x94, 4)
    struct.pack_into(">I", config, 0x9C, value)
    return {
        "game_id": "RSPE01", "disc_revision": revision, "game_mode_raw": 4,
        "stage": stage, "phase": phase,
        "frame_start": 100 + number * 4, "frame_end": 102 + number * 4,
        "windows": {
            "golf_config": {"address": f"0x{address:08X}", "bytes_hex": config.hex()},
            "golf_field": {"address": "0x80020000", "bytes_hex": bytes(0xA8).hex()},
            "sports_sequence": {"address": "0x80030000", "bytes_hex": bytes(0xD0).hex()},
        },
    }


def summary(rows):
    return summarize_phase_memory(rows, [], scope="focused", run_id="synthetic-phase-trial")


class PhaseSpecificityTests(unittest.TestCase):
    def test_within_phase_and_boundary_counts_are_separate(self):
        rows = [
            sample(0, "idle", 1, 0),
            sample(0, "idle", 2, 1),
            sample(1, "aim_only", 3, 2),
            sample(1, "aim_only", 4, 3),
            sample(2, "idle", 4, 4),
            sample(2, "idle", 4, 5),
        ]
        result = summary(rows)
        self.assertEqual(result["changed_word_count"], 1)
        word = result["top_changed_relative_words"][0]
        self.assertEqual(word["within_phase_changes"], 2)
        self.assertEqual(word["at_phase_boundary_changes"], 1)
        self.assertEqual(word["phase_change_counts"], {"aim_only": 1, "idle": 1})
        self.assertEqual(word["boundary_changes_into_phase"], {"aim_only": 1})
        self.assertEqual(word["phase_observation_opportunities"], {"aim_only": 1, "idle": 2})
        self.assertEqual(result["within_phase_comparisons_by_region"]["golf_config"],
                         {"aim_only": 1, "idle": 2})

    def test_zero_changes_still_count_sampled_control_opportunities(self):
        rows = [sample(0,"idle",5,0), sample(0,"idle",5,1),
                sample(1,"aim_only",5,2), sample(1,"aim_only",5,3)]
        result = summary(rows)
        self.assertEqual(result["changed_word_count"], 0)
        self.assertEqual(result["within_phase_comparisons_by_region"]["golf_config"],
                         {"idle": 1, "aim_only": 1})
        self.assertEqual(result["top_changed_relative_words"], [])

    def test_stage_boundary_cannot_be_claimed_as_motion(self):
        rows = [sample(0,"idle",1,0),sample(0,"idle",1,1),
                sample(1,"shot_attempt",7,2),sample(1,"shot_attempt",7,3)]
        word = summary(rows)["top_changed_relative_words"][0]
        self.assertEqual(word["phase_change_counts"], {})
        self.assertEqual(word["boundary_changes_into_phase"], {"shot_attempt": 1})
        self.assertEqual(word["within_phase_changes"], 0)

    def test_frames_are_observed_not_impact_claims(self):
        rows = [sample(0,"idle",1,0), sample(0,"idle",2,1)]
        out = summary(rows)
        self.assertEqual(out["phase_frame_brackets"],
                         [{"stage":0,"phase":"idle","frame_start":100,"frame_end":102},
                          {"stage":0,"phase":"idle","frame_start":104,"frame_end":106}])
        self.assertEqual(out["max_non_atomic_frame_span"], 2)
        self.assertFalse(out["confirmed_power_address"])

    def test_relocation_excludes_false_word_transition_and_opportunity(self):
        rows = [sample(0,"idle",1,0), sample(0,"idle",2,1,address=0x80011000)]
        out = summary(rows)
        self.assertEqual(out["skipped_relocated_windows"], 1)
        self.assertEqual(out["changed_word_count"], 0)
        self.assertNotIn("golf_config", out["within_phase_comparisons_by_region"])

    def test_phase_switch_without_stage_is_not_allowed(self):
        with self.assertRaisesRegex(ValueError,"phase changed"):
            summary([sample(0,"idle",1,0),sample(0,"aim_only",2,1)])

    def test_stage_rollback_refused(self):
        with self.assertRaisesRegex(ValueError,"stage order"):
            summary([sample(1,"idle",1,0),sample(0,"idle",2,1)])

    def test_revision_gating_unchanged(self):
        with self.assertRaises(ValueError):
            summary([sample(0,"idle",1,0,revision=0),sample(0,"idle",2,1)])

    def test_sanitized_summary_does_not_echo_raw_ram(self):
        out = summary([sample(0,"idle",0xDEADBEEF,0),sample(0,"idle",0xCAFEBABE,1)])
        data = json.dumps(out)
        for secret in ("80010000","DEADBEEF","CAFEBABE","bytes_hex","address"):
            self.assertNotIn(secret,data)
        self.assertIn("+0x9C",data)

    def test_denominators_are_not_equivalent_to_game_response(self):
        out = summary([sample(0,"idle",1,0),sample(0,"idle",2,1)])
        self.assertEqual(out["phase_change_count_semantics"],
                         "within_stage_only_boundary_counts_separate")
        self.assertFalse(out["confirmed_power_address"])
        self.assertFalse(out["confirmed_ball_position_address"])
        self.assertFalse(out["confirmed_club_pose_address"])


if __name__ == "__main__":
    unittest.main()
