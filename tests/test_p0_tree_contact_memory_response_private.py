"""Synthetic-only, original-session-memory-only response investigation."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/"scripts"


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


m=load("tree_memory_response",SCRIPTS/"p0_tree_contact_memory_response_private.py")
fixture=load("tree_memory_test_fixture",
             ROOT/"tests"/"test_recover_p0_tree_contact_record_private.py")
capture=m.base.capture


def bevec(point):
    return struct.pack(">fff",*point)


def sample_rows(points,dt_ns=250_000_000):
    rows=[]
    for i,p in enumerate(points):
        ball=bytearray(capture.BALL_BYTES)
        ball[0x30:0x3C]=bevec(p)
        ball[0xCC:0xD8]=bevec(p)
        rows.append({
            "sample_index":i,
            "host_monotonic_start_ns":i*dt_ns,
            "ball_object_candidate_be_hex_PRIVATE":ball.hex(),
            "nested_translation_candidate_be_hex_PRIVATE":bevec(p).hex(),
        })
    return rows


class TreeMemoryOnlyResponseTests(unittest.TestCase):
    def test_synthetic_three_trial_manifest_end_to_end(self):
        with tempfile.TemporaryDirectory() as temp:
            session=fixture.synthetic_session(temp)
            recovered,data=m.base.read_trials(session)
            result=m.summarize(recovered,data)
            self.assertEqual(result["original_source_ball_packets"],9)
            self.assertEqual(result["original_full_tree_record_snapshots"],6)
            self.assertTrue(result["original_capture_raw_sha_verified"])
            self.assertEqual([result["per_trial"][k][
                "operator_observed_contact_not_native"] for k in
                m.prior.TRIAL_ORDER],["leaves","wood","none"])
            self.assertFalse(result["actual_collision_frame_verified"])
            self.assertFalse(result["native_colliding_tree_identity_verified"])
            self.assertFalse(result["training_approved"])

    def test_moving_only_alias_breaks_idle_dominance(self):
        points=[(0.,0.,0.)]*3+[(1.,0.,0.),(2.,0.,0.),(3.,0.,0.)]
        rows=sample_rows(points)
        ball,nested,_unused=(
            m.base.decode_window(rows,*m.base.STREAMS["ball_candidate"]),
            m.base.decode_window(rows,*m.base.STREAMS["nested_translation_candidate"]),
            None)
        # Every active nested packet is one sample *behind*; equal
        # stationary packets should not be mistaken for active aliases.
        for i in (3,4,5):
            nested[i]=ball[i-1][0x30:0x3C]
        phase=m.phases(ball)
        self.assertEqual(phase["moving"],{3,4,5})
        out=m.source_aliases(ball,nested,phase)
        source=out["nested_exact_matches_by_ball_offset_and_phase"]["+0x030"]
        self.assertEqual(source["stationary"]["exact_same_packet_nested_matches"],3)
        self.assertEqual(source["moving"]["exact_same_packet_nested_matches"],0)
        self.assertEqual(source["moving"]["exact_nested_previous_packet_matches"],3)
        inter=out["ball_candidate_exact_interfield_matches_by_phase"][
            "+0x030_versus_+0x0CC"]
        self.assertEqual(inter["moving"]["exact_same_packet_triplet_matches"],3)
        self.assertFalse(out["native_rendered_translation_or_velocity_verified"])

    def test_signed_response_ratio_shows_slowdown_not_just_max_min(self):
        # Successive position candidate movements: x=1, x=1,
        # then turn 90 deg with 0.25-unit step.
        pts=[(0.,0.,0.),(1.,0.,0.),(2.,0.,0.),(2.,.25,0.),(2.,.5,0.)]
        rows=sample_rows(pts)
        ball=m.base.decode_window(rows,*m.base.STREAMS["ball_candidate"])
        phase=m.phases(ball)
        report=m.speed_proxy(ball,rows,phase)
        top=report["largest_candidate_turns_signed_ratio"][0]
        self.assertEqual(top["original_sample_index"],3)
        self.assertEqual(top["candidate_angle_degrees"],90.0)
        self.assertAlmostEqual(top["after_over_before_displacement_ratio"],0.25)
        self.assertEqual(top["candidate_displacement_per_host_second_class"],
                         "decreasing_displacement_per_host_second")
        self.assertFalse(top["actual_collision_or_impulse_at_sample_proven"])

    def test_host_timing_ratios_not_assumed_equal(self):
        pts=[(0.,0.,0.),(1.,0.,0.),(2.,0.,0.),(3.,0.,0.),(4.,0.,0.)]
        rows=sample_rows(pts)
        # First step after previous reading gets twice the wall time.
        stamps=[0,100,200,400,500]
        for r,t in zip(rows,stamps):
            r["host_monotonic_start_ns"]=t*1_000_000
        ball=m.base.decode_window(rows,*m.base.STREAMS["ball_candidate"])
        result=m.speed_proxy(ball,rows,m.phases(ball))
        row=next(x for x in result["largest_candidate_turns_signed_ratio"]
                 if x["original_sample_index"]==3)
        self.assertAlmostEqual(row["after_over_before_displacement_ratio"],1.)
        self.assertAlmostEqual(
            row["after_over_before_host_second_normalized_ratio"],0.5)
        self.assertFalse(result["native_velocity_or_collision_verified"])

    def test_tree_field_bit_categories_never_claim_real_pointer_type(self):
        data=bytearray(m.TREE_BYTES)
        struct.pack_into(">I",data,0x24,0x80004000)
        struct.pack_into(">I",data,0x2C,0x90008000)
        struct.pack_into(">I",data,0x4C,0x3F800000)
        struct.pack_into(">I",data,0x50,0)
        report=m.tree_fields([(0,bytes(data))])
        self.assertEqual(report["source_tree_native_field_bit_pattern_categories"][
            "+0x024"]["aligned_mem1_range"],1)
        self.assertEqual(report["source_tree_native_field_bit_pattern_categories"][
            "+0x02C"]["aligned_mem2_range"],1)
        self.assertEqual(report["source_tree_native_field_bit_pattern_categories"][
            "+0x04C"]["bounded_f32_bit_pattern"],1)
        self.assertEqual(report["sampled_source_tree_record_count"],94)
        self.assertFalse(report["native_pointer_or_integer_type_proven"])

    def test_original_tree_24_2c_cochanges_at_run_onset(self):
        def tree_row(index,updates):
            a=bytearray(m.TREE_BYTES)
            for tree in range(m.TREE_COUNT):
                a[tree*m.TREE_STRIDE:tree*m.TREE_STRIDE+4]=b"TREE"
            for tree in updates:
                struct.pack_into(">I",a,tree*m.TREE_STRIDE+0x24,7)
                struct.pack_into(">I",a,tree*m.TREE_STRIDE+0x2C,7)
            return (index,bytes(a))
        trial=[tree_row(0,set()),tree_row(8,set()),
               tree_row(16,{11,38,63})]
        phase={"run":{"longest_contiguous_change_run_after_sample_indices":[10,14]}}
        result=m.active_interval_tree_changes(trial,phase)
        self.assertEqual(result["coarse_tree_snapshots_bracketing_movement_start"],[8,16])
        self.assertEqual(result["source_tree_count_changed_in_both_0x24_0x2C"],3)
        self.assertTrue(result["source_tree_11_38_40_membership_in_24_2c_cochange"]["11"])
        self.assertFalse(result["source_tree_11_38_40_membership_in_24_2c_cochange"]["40"])
        self.assertFalse(result["source_tree_field_is_collision_event_proven"])

    def test_nonfinite_candidate_triplet_abstains_from_speed(self):
        rows=sample_rows([(0.,0.,0.),(1.,0.,0.),(2.,0.,0.)])
        ball=m.base.decode_window(rows,*m.base.STREAMS["ball_candidate"])
        corrupted=bytearray(ball[-1])
        corrupted[0x30:0x34]=struct.pack(">f",float("nan"))
        ball[-1]=bytes(corrupted)
        report=m.speed_proxy(ball,rows,m.phases(ball))
        self.assertFalse(report["available"])
        self.assertFalse(report["native_velocity_or_collision_verified"])

    def test_safe_report_does_not_expose_raw_memory_or_addresses(self):
        with tempfile.TemporaryDirectory() as temp:
            session=fixture.synthetic_session(temp)
            report=m.summarize(*m.base.read_trials(session))
            text=json.dumps(report,sort_keys=True)
            self.assertNotIn("candidate-stream-RAW-PRIVATE",text)
            self.assertNotIn("host_monotonic_start_ns",text)
            self.assertNotIn("ball_object_candidate_be_hex_PRIVATE",text)
            self.assertNotIn("source_identity_digest_PRIVATE",text)
            self.assertNotIn(str(session),text)
            self.assertFalse(report["source_selected_ball_is_rendered_ball_position_proven"])

    def test_memory_only_cli_creates_once_and_does_not_rewrite_raw(self):
        with tempfile.TemporaryDirectory() as temp:
            session=fixture.synthetic_session(temp)
            original={p:p.read_bytes() for p in session.rglob("*") if p.is_file()}
            self.assertEqual(m.main(["--session",str(session)]),0)
            result=session/"tree-contact-memory-response-SAFE.json"
            self.assertTrue(result.is_file())
            data=json.loads(result.read_text())
            self.assertFalse(data["training_approved"])
            self.assertEqual(original,{p:p.read_bytes() for p in original})
            self.assertEqual(m.main(["--session",str(session)]),2)

    def test_original_raw_hash_failure_refuses_safe_output(self):
        with tempfile.TemporaryDirectory() as temp:
            session=fixture.synthetic_session(temp)
            raw=next(session.glob("wood-*/candidate-stream-RAW-PRIVATE.jsonl"))
            with raw.open("a",encoding="utf-8") as fh:
                fh.write("{}\n")
            self.assertEqual(m.main(["--session",str(session)]),2)
            self.assertFalse((session/"tree-contact-memory-response-SAFE.json").exists())


if __name__=="__main__":
    unittest.main()
