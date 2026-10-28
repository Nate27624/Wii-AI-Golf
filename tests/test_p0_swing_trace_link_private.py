"""Synthetic only: P0 same-controller-trace / source-record integrity gate."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_p0_swing_trace_link_private.py"
spec = importlib.util.spec_from_file_location("p0_link_gate", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture(*, moved=True, human="yes"):
    phases = [
        ("idle_control", None), ("idle_control", None),
        ("a_prime", None), ("trace", 4), ("trace", 12),
        ("trace", 27), ("trace", 47), ("trace", 77),
        ("posttrace", None),
    ]
    rows = []
    for tick, (stage, index) in enumerate(phases):
        b = [2.0, 1.0, 0.0] if moved and tick >= 5 else [0.0, 1.0, 0.0]
        rows.append({
            "frame_tick_index": tick * 4,
            "read_overhead_us": 250,
            "input_stage": stage,
            "trace_sample_index_if_active": index,
            "trace_id_if_active": 23 if stage == "trace" else None,
            "selected_slot_candidate": 0,
            "source_hole_index": 1,
            "source_owner_consistent": True,
            "ball_translation_f32_candidate": b,
            "record_translation_f32_candidate": b,
            "current_start_f32_candidate": [0., 1., 0.],
            "selected_player_record_words_PRIVATE": [0xDEADBEEF] * mod.WORDS,
        })
    return {
        "kind": "PRIVATE-UNVERIFIED-selected-ball-frame-watch",
        "watch_status": {"state": "complete", "samples": len(rows)},
        "bridge_trace_status": {"state": "complete", "kind": "swing", "id": 23,
                                "total_frames": 89, "applied_frames": 89},
        "operator_observation": human,
        "safe_summary": {
            "watch_complete": True,
            "source_selected_slot_stable": True,
            "source_hole_stable": True,
            "source_owner_consistency_checks_passed": True,
            "read_performance_checks_passed": True,
            "start_vector_stable": True,
            "idle_control_vector_stationary": True,
            "pretrace_candidate_ball_stationary": True,
            "candidate_ball_changed_after_trace_start": moved,
            "human_observed_ball_movement": human,
        },
        "PRIVATE_UNVERIFIED_NUMERIC_VECTORS": rows,
    }


class P0TraceLinkPrivateTests(unittest.TestCase):
    def test_complete_correlated_candidate_but_no_physics_promotion(self):
        result = mod.audit(fixture())
        self.assertTrue(result["candidate_motion_corroborated_not_physical_proof"])
        self.assertEqual(result["private_sample_count"], 9)
        self.assertTrue(result["bridge_trace_id_matches_all_active_memory_samples"])
        self.assertFalse(result["actual_ball_xyz_or_collision_verified"])
        self.assertFalse(result["approved_for_training"])

    def test_no_motion_is_valid_negative_evidence(self):
        result = mod.audit(fixture(moved=False, human="no"))
        self.assertFalse(result["candidate_motion_corroborated_not_physical_proof"])
        self.assertFalse(result["ball_candidate_changed_after_trace_started"])

    def test_human_says_no_does_not_promote_motion(self):
        result = mod.audit(fixture(moved=True, human="no"))
        self.assertFalse(result["candidate_motion_corroborated_not_physical_proof"])

    def test_trace_id_mismatch_rejected(self):
        report = fixture()
        report["bridge_trace_status"]["id"] = 24
        with self.assertRaises(ValueError):
            mod.audit(report)

    def test_incomplete_applied_frames_rejected(self):
        report = fixture()
        report["bridge_trace_status"]["applied_frames"] = 88
        with self.assertRaises(ValueError):
            mod.audit(report)

    def test_incomplete_watch_rejected(self):
        report = fixture()
        report["watch_status"]["state"] = "recording"
        with self.assertRaises(ValueError):
            mod.audit(report)

    def test_missing_neutral_stays_inconclusive(self):
        report = fixture()
        report["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][3]["trace_sample_index_if_active"] = 12
        report["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][4]["trace_sample_index_if_active"] = 14
        result = mod.audit(report)
        self.assertFalse(result["complete_control_coverage"])
        self.assertFalse(result["candidate_motion_corroborated_not_physical_proof"])

    def test_backwards_trace_index_rejected(self):
        report = fixture()
        report["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][5]["trace_sample_index_if_active"] = 8
        with self.assertRaises(ValueError):
            mod.audit(report)

    def test_out_of_order_phase_rejected(self):
        report = fixture()
        rows = report["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"]
        rows[2]["input_stage"] = "posttrace"
        with self.assertRaises(ValueError):
            mod.audit(report)

    def test_changed_source_object_rejected(self):
        report = fixture()
        report["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][5]["selected_slot_candidate"] = 1
        with self.assertRaises(ValueError):
            mod.audit(report)

    def test_stale_or_mismatched_producer_summary_rejected(self):
        report = fixture()
        report["safe_summary"]["candidate_ball_changed_after_trace_start"] = False
        with self.assertRaises(ValueError):
            mod.audit(report)

    def test_sample_budget_exceeded_rejected(self):
        report = fixture()
        report["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][5]["read_overhead_us"] = 5001
        with self.assertRaises(ValueError):
            mod.audit(report)

    def test_private_pointer_values_never_exposed(self):
        result = mod.audit(fixture())
        output = repr(result)
        self.assertNotIn("3735928559", output)
        self.assertNotIn("DEADBEEF", output)

    def test_outside_private_root_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            local = Path(root) / "some-PRIVATE.json"
            local.write_text("{}", encoding="utf-8")
            with patch.object(mod, "DATA_ROOT", Path(root) / "missing-root"):
                with self.assertRaises((ValueError, OSError)):
                    mod._read_private(local)

    def test_source_start_conflict_rejected(self):
        report = fixture()
        report["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][5]["current_start_f32_candidate"] = [1., 1., 0.]
        with self.assertRaises(ValueError):
            mod.audit(report)


if __name__ == "__main__":
    unittest.main()
