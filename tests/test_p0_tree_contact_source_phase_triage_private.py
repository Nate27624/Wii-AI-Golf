"""Synthetic-only deep source-relative Ball phase / 94-tree timeline triage."""
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
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


m=load("source_phase_triage",SCRIPTS/"p0_tree_contact_source_phase_triage_private.py")
fix=load("original_recover_fixture",
         ROOT/"tests"/"test_recover_p0_tree_contact_record_private.py")
capture=m.base.capture


def floatblob(values):
    return struct.pack(">fff",*values)


def vector_packet(index,values):
    ball=bytearray(capture.BALL_BYTES)
    ball[0x30:0x3C]=floatblob(values)
    return {"ball_object_candidate_be_hex_PRIVATE":ball.hex(),
            "nested_translation_candidate_be_hex_PRIVATE":floatblob(values).hex(),
            "sample_index":index}


class PhaseTriageTests(unittest.TestCase):
    def test_synthetic_original_sha_qualified_three_trial_session(self):
        with tempfile.TemporaryDirectory() as temp:
            session=fix.synthetic_session(temp)
            recovered,trials=m.base.read_trials(session)
            report=m.inspect(recovered,trials)
            self.assertEqual(report["original_ball_sample_count"],9)
            self.assertEqual(report["original_tree_snapshot_count"],6)
            self.assertEqual(set(report["per_trial"]),set(m.TRIAL_ORDER))
            self.assertFalse(report["native_foliage_collision_proven"])
            self.assertFalse(report["native_ball_velocity_or_impulse_proven"])
            self.assertFalse(report["training_approved"])

    def test_exact_nested_ball_triplet_alias_across_dynamic_samples(self):
        rows=[vector_packet(i,(float(i),0,0)) for i in range(6)]
        ball=m.base.decode_window(rows,*m.base.STREAMS["ball_candidate"])
        nested=m.base.decode_window(rows,*m.base.STREAMS["nested_translation_candidate"])
        out=m.ball_nested_alias(ball,nested)
        self.assertIn("+0x030",
                      out["all_sample_exact_nested_triplet_alias_ball_word_offsets"])
        self.assertEqual(out["ball_plus_0x30_exact_nested_match_samples"],6)
        self.assertEqual(out["ball_plus_0xAC_exact_nested_match_samples"],1)
        self.assertEqual(out["source_nested_triplet_distinct_pattern_count"],6)
        self.assertFalse(out["nested_and_ball_field_same_rendered_position_proven"])

    def test_first_sustained_change_run_not_late_reset(self):
        sequence=[floatblob((0,0,0))]*9
        sequence += [floatblob((float(i),0,0)) for i in range(1,6)]
        sequence += [floatblob((5,0,0))]*6
        sequence += [floatblob((0,0,0))]
        result=m.change_runs(sequence)
        self.assertEqual(result["first_change_after_sample"],9)
        self.assertEqual(result["longest_contiguous_change_run_after_sample_indices"],[9,13])
        self.assertTrue(result["multiple_disjoint_motion_runs_exist"])
        self.assertTrue(result["sustained_run_min_four_changes"])
        self.assertFalse(result["source_triplet_changes_are_physics_motion_verified"])

    def test_angular_deviation_is_trajectory_candidate_only(self):
        pts=[(0.,0.,0.),(1.,0.,0.),(2.,0.,0.),(2.,1.,0.),(2.,2.,0.)]
        run=m.change_runs([floatblob(p) for p in pts])
        result=m.motion_bends(pts,run)
        self.assertTrue(result["finite_source_triplet_decode"])
        self.assertEqual(result["largest_candidate_turns"][0]["source_sample_index"],3)
        self.assertAlmostEqual(result["largest_candidate_turns"][0][
            "direction_change_angle_degrees"],90.0)
        self.assertFalse(result["largest_candidate_turns"][0][
            "observed_visual_tree_contact_at_this_sample_proven"])
        self.assertFalse(result["native_impact_frame_proven"])

    def test_nonfinite_source_candidate_suppresses_turning_estimates(self):
        b=floatblob((float("nan"),0,0))
        rows=[b,b]
        self.assertIsNone(m.triplet_sequence(rows,0))
        result=m.motion_bends(None,m.change_runs(rows))
        self.assertFalse(result["finite_source_triplet_decode"])
        self.assertFalse(result["native_impact_frame_proven"])

    def test_source_tree_24_2c_cochange_not_a_tree_contact(self):
        def row(index,change):
            array=bytearray(m.base.TREE_BYTES)
            array[:4]=b"ABCD"
            for tree in range(m.base.TREE_COUNT):
                pos=tree*m.base.TREE_STRIDE
                array[pos:pos+4]=b"ABCD"
            for tree in m.TREE_INDICES:
                for off in (0x24,0x2C):
                    array[tree*m.base.TREE_STRIDE+off:tree*m.base.TREE_STRIDE+off+4]=(
                        change.to_bytes(4,"big"))
            return {"sample_index":index,
                    "all_94_tree_records_be_hex_PRIVATE":array.hex()}
        result=m.tree_timeline([row(0,0),row(8,1),row(16,1)])
        self.assertEqual(result["tree_candidate_change_timeline"]["11"][
            "+0x024"]["changed_snapshot_intervals"],[[0,8]])
        self.assertEqual(result["all_94_tree_animation_or_runtime_common_update_intervals"][0][
            "source_tree_count_both_plus_0x24_and_plus_0x2C_changed"],3)
        self.assertFalse(result["tree_0x24_or_0x2C_proven_impact_fields"])

    def test_assumed_coordinate_rank_only_can_find_nearest_tree_candidate(self):
        def snapshot():
            data=bytearray(m.base.TREE_BYTES)
            for i in range(m.base.TREE_COUNT):
                pos=i*m.base.TREE_STRIDE+0x30
                coords=(1.,0.,1.) if i==11 else (1000.+float(i),0.,1000.)
                data[pos:pos+12]=floatblob(coords)
            return data.hex()
        points=[(0.,0.,0.),(.2,0.,.2),(.4,0.,.4),(.6,0.,.6),(.8,0.,.8)]
        rows=[{"sample_index":i,
               "all_94_tree_records_be_hex_PRIVATE":snapshot() if i%2==0 else None}
              for i in range(5)]
        r=m.tree_candidate_spatial_rank(
            rows,points,m.change_runs([floatblob(p) for p in points]))
        self.assertTrue(r["available"])
        nearest=r["tentative_source_coordinate_proximity_ranks"][
            "XZ_plane_UNVERIFIED_shared_axes"]["most_frequent_nearest_source_tree_array_indices"]
        self.assertEqual(nearest[0]["source_tree_array_index"],11)
        self.assertFalse(r["source_ball_tree_world_coordinate_frame_aligned_proven"])
        self.assertFalse(r["contacted_wood_or_foliage_tree_identified"])

    def test_changed_tree_centre_abstains_spatial_rank_instead_of_false_claim(self):
        values=[]
        for i in range(5):
            data=bytearray(m.base.TREE_BYTES)
            for tree in range(m.base.TREE_COUNT):
                struct.pack_into(">fff",data,tree*m.base.TREE_STRIDE+0x30,
                                 float(tree),0.,float(tree))
            if i==4:
                struct.pack_into(">fff",data,11*m.base.TREE_STRIDE+0x30,
                                 999.,0.,999.)
            values.append({"sample_index":i,
                           "all_94_tree_records_be_hex_PRIVATE":
                               data.hex() if i in (0,4) else None})
        points=[(float(i),0.,float(i)) for i in range(5)]
        out=m.tree_candidate_spatial_rank(
            values,points,m.change_runs([floatblob(p) for p in points]))
        self.assertFalse(out["available"])
        self.assertEqual(out["reason"],"source_tree_centres_changed")

    def test_original_first_packet_tree_differences_are_field_sized(self):
        with tempfile.TemporaryDirectory() as temp:
            session=fix.synthetic_session(temp)
            recovered,trials=m.base.read_trials(session)
            row=trials["leaves"]["rows"][0]
            tree=bytearray.fromhex(row["all_94_tree_records_be_hex_PRIVATE"])
            off=11*m.base.TREE_STRIDE+0x4C
            tree[off:off+4]=b"ABCD"
            row["all_94_tree_records_be_hex_PRIVATE"]=tree.hex()
            result=m.first_snapshot_mismatches(trials)
            comp=next(x for x in result["comparisons"] if
                      x["trial_intent"]=="leaves")
            diffs=comp["source_byte_baseline_differences"]["source_trees"]
            self.assertEqual(diffs["source_tree_objects_with_initial_difference"],1)
            self.assertEqual(diffs["initial_different_word_offsets_per_tree"][0][
                "tree_record_relative_word_offset"],"+0x04C")
            self.assertFalse(result["same_pre_shot_savestate_proven"])

    def test_main_writes_only_new_safe_file_preserving_originals(self):
        with tempfile.TemporaryDirectory() as temp:
            session=fix.synthetic_session(temp)
            prior={p:p.read_bytes() for p in session.rglob("*") if p.is_file()}
            self.assertEqual(m.main(["--session",str(session)]),0)
            report=session/"tree-contact-source-phase-triage-SAFE.json"
            self.assertTrue(report.is_file())
            data=json.loads(report.read_text())
            self.assertFalse(data["training_approved"])
            self.assertEqual(prior,{p:p.read_bytes() for p in prior})
            self.assertEqual(m.main(["--session",str(session)]),2)

    def test_corrupt_original_source_sha_abstains(self):
        with tempfile.TemporaryDirectory() as temp:
            session=fix.synthetic_session(temp)
            raw=next(session.glob("wood-*/candidate-stream-RAW-PRIVATE.jsonl"))
            with raw.open("a",encoding="utf-8") as f:
                f.write("{}\n")
            self.assertEqual(m.main(["--session",str(session)]),2)
            self.assertFalse((session/"tree-contact-source-phase-triage-SAFE.json").exists())

    def test_no_raw_coordinates_or_addresses_in_safe_report(self):
        with tempfile.TemporaryDirectory() as temp:
            session=fix.synthetic_session(temp)
            report=m.inspect(*m.base.read_trials(session))
            text=json.dumps(report,sort_keys=True)
            self.assertNotIn("source_identity_digest_PRIVATE",text)
            self.assertNotIn("ball_object_candidate_be_hex_PRIVATE",text)
            self.assertNotIn("0x9000",text)
            self.assertNotIn(str(session),text)


if __name__=="__main__":
    unittest.main()
