"""Synthetic private watched V1 source-ball trajectory evidence tests.

These test audit software only: no Dolphin, controller, native RAM or upload.
"""
from __future__ import annotations
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

SRC = Path(__file__).resolve().parents[1] / "scripts" / "audit_p0_v1_ball_motion_private.py"
spec = importlib.util.spec_from_file_location("p0_source_ball_audit", SRC)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def words():
    w = [0] * 51
    for start in (0x54//4, 0x60//4):
        for i, val in enumerate((1.0, 2.0, 3.0)):
            w[start+i] = struct.unpack(">I", struct.pack(">f", val))[0]
    return w


def fixture(motion=True, contact="yes", movement="yes"):
    phases = [
        ("idle_control", None), ("idle_control", None),
        ("a_prime", None), ("a_prime", None),
        ("trace", 0), ("trace", 8), ("trace", 12), ("trace", 20),
        ("trace", 27), ("trace", 34), ("trace", 48), ("trace", 64),
        ("trace", 80), ("posttrace", None), ("posttrace", None),
    ]
    rows = []
    for i, (stage, index) in enumerate(phases):
        shifted = bool(motion and index is not None and index >= 34)
        shifted = shifted or bool(motion and stage == "posttrace")
        rows.append({
            "frame_tick_index": i * 4,
            "trace_sample_index_if_active": index,
            "trace_id_if_active": 123 if stage == "trace" else None,
            "input_stage": stage,
            "selected_slot_candidate": 0,
            "source_hole_index": 1,
            "source_owner_consistent": True,
            "read_overhead_us": 2800,
            "ball_translation_f32_candidate": [2.0 if shifted else 1.0, 2.0, 3.0],
            "record_translation_f32_candidate": [1.0, 2.0, 3.0],
            "current_start_f32_candidate": [1.0, 2.0, 3.0],
            "selected_player_record_words_PRIVATE": words(),
        })
    return {
        "kind": "PRIVATE-UNVERIFIED-selected-ball-frame-watch",
        "watch_status": {"state": "complete", "samples": len(rows)},
        "bridge_trace_status": {
            "kind": "swing", "state": "complete",
            "id": 123, "total_frames": 89, "applied_frames": 89,
        },
        "controller_timing": {
            "idle": {"observed_idle_frame_delta": 24},
            "observed_A_lead": {
                "observed_frame_delta": 45, "a_button_only_requests": 1,
            },
        },
        "operator_observation": movement,
        "operator_contact_human": contact,
        "safe_summary": {
            "contact_human": contact,
            "human_observed_ball_movement": movement,
            "contact_and_movement_are_separate_human_labels": True,
            "swing_protocol_v1_source_checked": True,
            "trace_sha256": "synthetic-distinct-frozen-trace",
            "a_lead_observed_frames": 45,
            "watch_complete": True,
            "source_selected_slot_stable": True,
            "source_hole_stable": True,
            "source_owner_consistency_checks_passed": True,
            "read_performance_checks_passed": True,
            "start_vector_stable": True,
            "idle_control_vector_stationary": True,
            "pretrace_candidate_ball_stationary": True,
            "candidate_ball_changed_after_trace_start": bool(motion),
            "candidate_record_triplet_equal_ball_triplet_count": (
                15 - (7 if motion else 0)),
            "phase_sample_counts": {
                "idle_control": 2, "a_prime": 2, "trace": 9, "posttrace": 2,
            },
        },
        "PRIVATE_UNVERIFIED_NUMERIC_VECTORS": rows,
    }


class TrajectoryEvidenceTests(unittest.TestCase):
    def reject(self, payload):
        with self.assertRaises(m.Reject):
            m.audit(payload)

    def test_correlated_motion_is_not_physics_verified(self):
        r = m.audit(fixture())
        self.assertTrue(r["source_ball_vector_correlated_with_observed_swing_not_physics_verified"])
        self.assertTrue(r["source_record_plus_0x54_words_match_reported_vector"])
        self.assertTrue(r["source_current_start_stable"])
        self.assertEqual(r["sample_counts_per_phase"]["trace_neutral"], 2)
        self.assertGreater(r["ball_candidate_changed_samples_after_forward_start"], 0)
        self.assertFalse(r["actual_ball_world_xyz_verified"])
        self.assertFalse(r["actual_ball_velocity_xyz_verified"])
        self.assertFalse(r["same_guest_physics_frame_verified"])
        self.assertFalse(r["source_ball_cache_cc_f0_fc_sampled"])
        self.assertFalse(r["approved_for_training"])

    def test_no_motion_does_not_promote(self):
        r = m.audit(fixture(motion=False, movement="no", contact="no"))
        self.assertFalse(r["source_ball_vector_correlated_with_observed_swing_not_physics_verified"])
        self.assertEqual(r["ball_candidate_changed_samples_after_forward_start"], 0)

    def test_observed_movement_without_candidate_change_is_negative(self):
        r = m.audit(fixture(motion=False))
        self.assertFalse(r["source_ball_vector_correlated_with_observed_swing_not_physics_verified"])

    def test_trace_candidate_change_without_contact_is_not_confirmed(self):
        for contact, movement in [("no", "yes"), ("unknown", "yes"),
                                  ("yes", "no"), ("yes", "unknown")]:
            with self.subTest(contact=contact, movement=movement):
                r = m.audit(fixture(contact=contact, movement=movement))
                self.assertFalse(r["source_ball_vector_correlated_with_observed_swing_not_physics_verified"])

    def test_neutral_trace_change_is_confound(self):
        p=fixture()
        p["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][5]["ball_translation_f32_candidate"]=[2.0,2.0,3.0]
        r=m.audit(p)
        self.assertFalse(r["idle_a_only_neutral_and_backswing_stable"])
        self.assertFalse(r["source_ball_vector_correlated_with_observed_swing_not_physics_verified"])

    def test_early_a_prime_change_is_confound(self):
        p=fixture()
        p["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][3]["ball_translation_f32_candidate"]=[2.0,2.0,3.0]
        self.assertFalse(m.audit(p)["source_ball_vector_correlated_with_observed_swing_not_physics_verified"])

    def test_backswing_change_is_confound(self):
        p=fixture()
        p["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][7]["ball_translation_f32_candidate"]=[2.0,2.0,3.0]
        self.assertFalse(m.audit(p)["source_ball_vector_correlated_with_observed_swing_not_physics_verified"])

    def test_record_words_must_match_independent_reported_record_vector(self):
        p=fixture()
        p["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][4]["selected_player_record_words_PRIVATE"][0x54//4] = 0
        self.reject(p)

    def test_tee_must_be_fixed(self):
        p=fixture()
        p["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][10]["current_start_f32_candidate"]=[4.0,2.0,3.0]
        self.assertFalse(m.audit(p)["source_ball_vector_correlated_with_observed_swing_not_physics_verified"])

    def test_wrong_or_incomplete_trace_id_rejected(self):
        for change in ("wrongid","partial","duplicate","reorder","early_stage"):
            with self.subTest(change=change):
                p=fixture()
                rows=p["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"]
                if change=="wrongid": rows[9]["trace_id_if_active"]=999
                if change=="partial": p["bridge_trace_status"]["applied_frames"]=88
                if change=="duplicate": rows[9]["trace_sample_index_if_active"]=rows[8]["trace_sample_index_if_active"]
                if change=="reorder": rows[9]["frame_tick_index"]=0
                if change=="early_stage": rows[4]["input_stage"]="idle_control"
                self.reject(p)

    def test_missing_separate_human_observations_rejected(self):
        for key in ("operator_contact_human","operator_observation"):
            p=fixture()
            p.pop(key)
            self.reject(p)

    def test_missing_45_observed_frames_rejected(self):
        p=fixture()
        p["controller_timing"]["observed_A_lead"]["observed_frame_delta"]=44
        self.reject(p)

    def test_5ms_budget_violation_rejected(self):
        p=fixture()
        p["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][9]["read_overhead_us"]=5001
        self.reject(p)

    def test_missing_motion_phase_does_not_promote(self):
        p=fixture()
        p["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"]=[
            r for r in p["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"]
            if r["trace_sample_index_if_active"] not in (48,64)]
        p["watch_status"]["samples"]=len(p["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"])
        r=m.audit(p)
        self.assertIn("followthrough",r["missing_phases"])
        self.assertFalse(r["source_ball_vector_correlated_with_observed_swing_not_physics_verified"])

    def test_output_never_emits_native_words_vectors_or_identifiers(self):
        blob=json.dumps(m.audit(fixture()))
        self.assertNotIn("selected_player_record_words_PRIVATE",blob)
        self.assertNotIn("ball_translation_f32_candidate",blob)
        self.assertNotIn("[1.0, 2.0, 3.0]",blob)
        self.assertNotIn("0x900",blob)
        self.assertNotIn('"id": 123',blob)
        self.assertIn('"approved_for_training": false',blob)

    def test_conflicting_producer_summary_fails_closed(self):
        for field in ("start_vector_stable", "candidate_ball_changed_after_trace_start",
                      "candidate_record_triplet_equal_ball_triplet_count",
                      "phase_sample_counts"):
            p = fixture()
            p["safe_summary"][field] = None
            with self.subTest(field=field):
                self.reject(p)

    def test_path_guard_accepts_only_ignored_sibling(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/m.DATA_ROOT_NAME
            root.mkdir()
            file=root/"candidate-PRIVATE.json"
            file.write_text(json.dumps(fixture()),encoding="utf8")
            self.assertEqual(m.audit(m.read_private(file,root))["sample_count"],15)
            wrong=Path(d)/"repo"
            wrong.mkdir()
            with self.assertRaises(m.Reject):
                m.read_private(file,wrong)


if __name__=="__main__":
    unittest.main()
