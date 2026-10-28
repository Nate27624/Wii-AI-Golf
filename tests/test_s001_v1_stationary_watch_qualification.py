"""No-Dolphin tests for source-selected stationary V1 private watcher qualification."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import qualify_v1_selected_watch_readonly as q


def sample(i):
    return {
        "input_stage": "idle_control",
        "source_owner_consistent": True,
        "trace_id_if_active": None,
        "trace_sample_index_if_active": None,
        "selected_player_record_words_PRIVATE": [0x90000000] * 51,
        "frame_tick_index": 200 + 4 * i,
        "selected_slot_candidate": 0,
        "source_hole_index": 1,
        "read_overhead_us": 950,
        "ball_translation_f32_candidate": [2.0, 3.0, 4.0],
        "record_translation_f32_candidate": [2.0, 3.0, 4.0],
        "current_start_f32_candidate": [2.0, 3.0, 4.0],
    }


def private():
    return {
        "status": {"state": "complete", "samples": 32, "max_read_us": 950},
        "samples": [sample(i) for i in range(32)],
        "training_allowed": False,
    }


class FakeRPC:
    def __init__(self, *, status=None, data=None):
        self.calls = []
        self.status = list(status or ["idle","recording","complete"])
        self.data = data or private()
    def call(self, method, arguments=None):
        self.calls.append((method,arguments))
        if method == "bridge.ping":
            return {"connected": True}
        if method == "golf.ball_watch.v1_provenance":
            return {
                "swing_protocol": 1,
                "legacy_neutral_swing_events": True,
                "a_lead_observed_frames_required_by_operator_baseline": 45,
                "a_lead_applied": False,
                "live_contact_verified": False,
                "training_allowed": False,
            }
        if method == "golf.ball_watch.status":
            if len(self.status) > 1:
                return {"state": self.status.pop(0)}
            return {"state": self.status[0]}
        if method == "golf.ball_watch.arm":
            return {"state": "armed",
                    "requested_duration_frames": 128,
                    "interval_frames": 4}
        if method == "golf.ball_watch.drain":
            return self.data
        raise RuntimeError("unexpected RPC method")


class StationaryQualificationTests(unittest.TestCase):
    def test_dry_run_never_connects(self):
        with patch.object(q,"watched_v1_rpc",side_effect=AssertionError("no RPC")):
            self.assertEqual(q.main([]),0)

    def test_stable_source_32_samples_pass_no_raw_data(self):
        result=q.summarize_qualification(private(),elapsed_s=2.5)
        self.assertEqual(result["result"],"PASS")
        self.assertEqual(result["sample_count"],32)
        self.assertEqual(result["maximum_sample_read_microseconds"],950)
        self.assertFalse(result["training_allowed"])
        self.assertFalse(result["live_swing_automatically_authorized"])
        self.assertNotIn("2415919104",str(result))  # 0x90000000 private pointer

    def test_mock_runtime_arms_and_drains_without_controller_or_trace(self):
        rpc=FakeRPC()
        report=q.qualify_running(rpc,clock=lambda:2.0,sleep=lambda _:None)
        methods=[name for name,_ in rpc.calls]
        self.assertEqual(report["result"],"PASS")
        self.assertEqual(methods.count("golf.ball_watch.arm"),1)
        self.assertEqual(methods.count("golf.ball_watch.drain"),1)
        self.assertTrue(all(not name.startswith("controller.") for name in methods))
        self.assertTrue(all(not name.startswith("trace.") for name in methods))
        self.assertEqual([args for name,args in rpc.calls
                          if name=="golf.ball_watch.arm"],[[128,4]])

    def test_read_overhead_failure_refused(self):
        x=private()
        x["status"]["max_read_us"]=5001
        with self.assertRaisesRegex(RuntimeError,"5ms"):
            q.summarize_qualification(x,elapsed_s=2.0)

    def test_per_sample_budget_failure_refused(self):
        x=private()
        x["samples"][2]["read_overhead_us"]=5001
        with self.assertRaisesRegex(RuntimeError,"budget"):
            q.summarize_qualification(x,elapsed_s=2)

    def test_identity_or_hole_changes_fail(self):
        x=private()
        x["samples"][10]["source_hole_index"]=2
        with self.assertRaisesRegex(RuntimeError,"instability"):
            q.summarize_qualification(x,elapsed_s=2)

    def test_motion_or_trace_contamination_refused(self):
        for key,value in (
            ("trace_id_if_active",42),
            ("input_stage","trace"),
            ("source_owner_consistent",False),
        ):
            with self.subTest(key=key):
                x=private()
                x["samples"][9][key]=value
                with self.assertRaises(RuntimeError):
                    q.summarize_qualification(x,elapsed_s=2)

    def test_missing_or_extra_samples_refused(self):
        for count in (0,31,33):
            with self.subTest(count=count):
                x=private()
                x["samples"]=x["samples"][:count] if count<=32 else x["samples"]+[sample(32)]
                x["status"]["samples"]=count
                with self.assertRaisesRegex(RuntimeError,"incomplete"):
                    q.summarize_qualification(x,elapsed_s=2)

    def test_vector_changes_at_rest_refused(self):
        x=private()
        x["samples"][10]["ball_translation_f32_candidate"][1]+=0.02
        with self.assertRaisesRegex(RuntimeError,"stationary"):
            q.summarize_qualification(x,elapsed_s=2)

    def test_bridge_tick_gap_refused(self):
        x=private()
        x["samples"][11]["frame_tick_index"]+=1
        with self.assertRaisesRegex(RuntimeError,"instability"):
            q.summarize_qualification(x,elapsed_s=2)

    def test_source_gate_failure_does_not_drain_or_send_input(self):
        rpc=FakeRPC(status=["idle","source_gate_failed"])
        with self.assertRaisesRegex(RuntimeError,"gate"):
            q.qualify_running(rpc,clock=lambda:2.0,sleep=lambda _:None)
        methods=[name for name,_ in rpc.calls]
        self.assertNotIn("golf.ball_watch.drain",methods)
        self.assertTrue(all(not name.startswith("controller.") for name in methods))

    def test_read_only_provenance_failure_no_arm(self):
        rpc=FakeRPC(status=["recording"])
        with self.assertRaises(RuntimeError):
            q.qualify_running(rpc,clock=lambda:2.0,sleep=lambda _:None)
        self.assertFalse(any(name=="golf.ball_watch.arm" for name,_ in rpc.calls))


    def test_subthreshold_cumulative_drift_rejected_for_every_vector(self):
        # Old adjacent-only rule would PASS all of these after drifting
        # 31 * 0.9e-4 = 0.00279, despite stability tolerance of 1e-4.
        for field in (
            "ball_translation_f32_candidate",
            "record_translation_f32_candidate",
            "current_start_f32_candidate",
        ):
            for axis in range(3):
                with self.subTest(field=field, axis=axis):
                    data = private()
                    for i, sample_row in enumerate(data["samples"]):
                        sample_row[field][axis] += i * (0.9 * q.VECTOR_STABILITY_TOL)
                    with self.assertRaisesRegex(RuntimeError, "stationary"):
                        q.summarize_qualification(data, elapsed_s=2.0)

    def test_cumulative_drift_reversing_before_end_rejected(self):
        # Finishing back at start cannot hide an earlier large excursion.
        data = private()
        for i, sample_row in enumerate(data["samples"]):
            deviation = min(i, 31-i) * (0.9 * q.VECTOR_STABILITY_TOL)
            sample_row["ball_translation_f32_candidate"][0] += deviation
        with self.assertRaisesRegex(RuntimeError, "stationary"):
            q.summarize_qualification(data, elapsed_s=2.0)

    def test_small_stationary_jitter_within_anchor_and_adjacent_bounds_passes(self):
        # Noise can vary without exceeding *either* criterion.
        data = private()
        for i, sample_row in enumerate(data["samples"]):
            offset = (0.35 if i % 2 else -0.35) * q.VECTOR_STABILITY_TOL
            for field in (
                "ball_translation_f32_candidate",
                "record_translation_f32_candidate",
                "current_start_f32_candidate",
            ):
                sample_row[field][0] += offset
        report = q.summarize_qualification(data, elapsed_s=2.0)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(
            report["frame_counter_type"],
            "bridge_coroutine_tick_not_guest_physics_frame",
        )
        self.assertFalse(report["ball_world_xyz_verified"])
        self.assertFalse(report["training_allowed"])



if __name__=="__main__":
    unittest.main()
