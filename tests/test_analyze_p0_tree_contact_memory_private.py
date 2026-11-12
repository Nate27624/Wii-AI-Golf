"""Synthetic-only validation of deep P0 wood/leaves/near-miss RAM analysis."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/"scripts"


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


m=load("deep_tree_source",SCRIPTS/"analyze_p0_tree_contact_memory_private.py")
fixture=load("recover_tree_fixture",
             ROOT/"tests"/"test_recover_p0_tree_contact_record_private.py")


def synthetic_triplet():
    with tempfile.TemporaryDirectory() as temp:
        session=fixture.synthetic_session(temp)
        recovery,data=m.read_trials(session)
        result=m.analyze(recovery,data)
    return result


def mutate_field(sample,family,offset,value):
    key,size=m.STREAMS[family]
    payload=bytearray.fromhex(sample[key])
    payload[offset:offset+4]=value.to_bytes(4,"big")
    sample[key]=payload.hex()


def mutate_tree(sample,index,offset,value):
    payload=bytearray.fromhex(sample["all_94_tree_records_be_hex_PRIVATE"])
    pos=index*m.TREE_STRIDE+offset
    payload[pos:pos+4]=value.to_bytes(4,"big")
    sample["all_94_tree_records_be_hex_PRIVATE"]=payload.hex()


class TreeContactDeepMemoryTests(unittest.TestCase):
    def test_complete_SHA_checked_synthetic_session_deep_analysis(self):
        result=synthetic_triplet()
        self.assertEqual(result["original_total_ball_samples"],9)
        self.assertEqual(result["original_total_tree_snapshots"],6)
        self.assertEqual(result["trial_intents_preserved_instead_of_assuming_contact"],
                         ["wood","leaves","near_miss"])
        self.assertEqual(
            [result["per_trial"][x]["operator_observed_contact_region"]
             for x in m.INTENTS],["leaves","wood","none"])
        self.assertTrue(result["original_private_raw_sha_and_sample_counts_verified"])
        self.assertFalse(result["native_tree_impact_event_verified"])
        self.assertFalse(result["native_wood_vs_leaves_material_branch_verified"])
        self.assertFalse(result["ball_velocity_or_impulse_proven"])
        self.assertFalse(result["training_approved"])
        self.assertFalse(result["same_guest_physics_frame_verified"])

    def test_selected_ball_watch_separates_copy_and_position_hypotheses(self):
        results=synthetic_triplet()
        fields=results["per_trial"]["wood"]["candidate_object_word_dynamics"]
        ball=fields["ball_candidate"]["source_watched_fields_NOT_verified_physics"]
        self.assertIn("candidate_plus_0xAC_structural_copy_NOT_velocity",ball)
        self.assertIn("candidate_plus_0x30",ball)
        self.assertFalse(
            ball["candidate_plus_0xAC_structural_copy_NOT_velocity"][
                "rendered_ball_position_or_velocity_verified"])

    def test_time_brackets_not_atomic_and_source_comparable(self):
        result=synthetic_triplet()
        timing=result["per_trial"]["wood"]["time_and_frame_brackets"]
        self.assertTrue(timing["host_monotonic_timestamp_order_verified"])
        self.assertEqual(timing["sample_count"],3)
        self.assertFalse(timing["bridge_frame_count_is_guest_physics_frame_proven"])
        self.assertFalse(timing["uniform_shot_input_or_launch_time_proven"])
        self.assertFalse(result["cross_trial_original_start_state_bitwise_comparisons"][
            "same_launch_power_verified"])

    def test_dynamic_word_changes_and_enrichment_not_contact_proof(self):
        row={"schema_version":1,"sample_index":0}
        report={"trial_intents":list(m.INTENTS),"trials":[{}]*3,
                "original_private_raw_sha_and_sample_counts_verified":True}
        sessions={}
        for name in m.INTENTS:
            snapshots=[]
            for index in range(3):
                raw={
                    "sample_index":index,"host_monotonic_start_ns":index*100_000_000,
                    "host_monotonic_end_ns":index*100_000_000+100,
                    "bridge_frame_count_start":index*3,
                    "bridge_frame_count_end":index*3+1,
                    "all_94_tree_records_be_hex_PRIVATE":(b"\x00"*m.TREE_BYTES).hex(),
                }
                for family,(key,n) in m.STREAMS.items():
                    raw[key]=(b"\x00"*n).hex()
                if name in ("wood","leaves") and index>0:
                    mutate_field(raw,"ball_candidate",0xAC,index)
                    mutate_field(raw,"selected_record",0x54,index)
                if name in ("wood","leaves") and index==2:
                    mutate_tree(raw,5,0x48,1)
                snapshots.append(raw)
            sessions[name]={
                "rows":snapshots,
                "manifest":{"sample_count":3,"tree_snapshot_count":3,
                            "operator_observed_contact_region":(
                                "leaves" if name=="wood" else
                                "wood" if name=="leaves" else "none"),
                            "operator_observed_trajectory_changed":(
                                "no" if name=="near_miss" else "yes")},
                "directory":Path("/nonexistent"),
            }
        x=m.analyze(report,sessions)
        ball=x["contact_vs_no_contact_candidate_word_differentials"][
            "contact_comparison_family_results"]["ball_candidate"]
        self.assertEqual(ball[
            "dynamic_in_both_contact_intents_but_static_in_near_miss_count"],1)
        self.assertEqual(ball["top_both_vs_near_miss_candidates"][0][
            "source_object_relative_word_offset"],"+0x0AC")
        self.assertFalse(ball["top_both_vs_near_miss_candidates"][0][
            "independently_verified_collision_state"])
        tree=x["source_tree_word_differentials"]
        self.assertEqual(tree[
            "dynamic_same_tree_word_in_both_contact_intents_but_static_near_miss_count"],1)
        self.assertEqual(tree["top_tree_word_candidates"][0]["source_tree_array_index"],5)
        self.assertFalse(tree["top_tree_word_candidates"][0][
            "source_tree_is_contacted_tree_proven"])

    def test_94_tree_flag_changes_cannot_claim_impact(self):
        record=[]
        for i in range(3):
            raw={"sample_index":i}
            data=bytearray(m.TREE_BYTES)
            if i==2:
                pos=11*m.TREE_STRIDE+0x48
                data[pos]=1
            raw["all_94_tree_records_be_hex_PRIVATE"]=data.hex()
            record.append(raw)
        t,first,last,diff=m.tree_dynamics(record)
        self.assertEqual(t["tree_candidate_plus_0x48_word_changed_tree_count"],1)
        self.assertEqual(t["tree_objects_with_any_observed_word_changes"],1)
        self.assertEqual(t["top_dynamic_tree_array_indices"][0][
            "tree_array_index"],11)
        self.assertFalse(t["tree_candidate_plus_0x48_is_collision_event_proven"])
        self.assertFalse(t["tree_translation_field_is_impact_geometry_proven"])

    def test_broken_94_tree_shared_firstword_abstains(self):
        rows=[]
        for i in range(2):
            b=bytearray(m.TREE_BYTES)
            b[84:88]=b"\x01\x02\x03\x04"
            rows.append({"sample_index":i,
                         "all_94_tree_records_be_hex_PRIVATE":b.hex()})
        with self.assertRaises(ValueError):
            m.tree_dynamics(rows)

    def test_nonatomic_order_and_bad_candidate_window_abstain(self):
        rows=[{"sample_index":0,"host_monotonic_start_ns":100,
               "host_monotonic_end_ns":200,"bridge_frame_count_start":2,
               "bridge_frame_count_end":3},
              {"sample_index":1,"host_monotonic_start_ns":150,
               "host_monotonic_end_ns":250,"bridge_frame_count_start":4,
               "bridge_frame_count_end":5}]
        with self.assertRaises(ValueError):
            m.frame_and_host_timing(rows)
        with self.assertRaises(ValueError):
            m.decode_window([{"ball":"12345"}],"ball",8)

    def test_real_original_report_contains_no_raw_addresses_or_words(self):
        import re
        output=json.dumps(synthetic_triplet(),sort_keys=True)
        self.assertIsNone(re.search(r"0x[89][0-9a-fA-F]{7}",output))
        self.assertNotIn("candidate-stream-RAW-PRIVATE.jsonl",output)
        self.assertNotIn("D:\\",output)
        self.assertNotIn("source_identity_digest_PRIVATE",output)

    def test_deep_memory_main_creates_only_new_safe_report(self):
        with tempfile.TemporaryDirectory() as temp:
            session=fixture.synthetic_session(temp)
            originals={p:p.read_bytes() for p in session.rglob("*")
                       if p.is_file()}
            self.assertEqual(m.main(["--session",str(session)]),0)
            safe=session/"tree-contact-deep-memory-SAFE.json"
            self.assertTrue(safe.is_file())
            result=json.loads(safe.read_text(encoding="utf-8"))
            self.assertEqual(result["original_total_ball_samples"],9)
            self.assertEqual(originals,{p:p.read_bytes() for p in originals})
            self.assertEqual(m.main(["--session",str(session)]),2)

    def test_bad_manifest_sha_prevents_analysis_output(self):
        with tempfile.TemporaryDirectory() as temp:
            session=fixture.synthetic_session(temp)
            raw=next(session.glob("wood-*/candidate-stream-RAW-PRIVATE.jsonl"))
            with raw.open("a",encoding="utf-8") as f:
                f.write("{}\n")
            self.assertEqual(m.main(["--session",str(session)]),2)
            self.assertFalse((session/"tree-contact-deep-memory-SAFE.json").exists())

    def test_video_metadata_optional_and_cannot_claim_contact(self):
        with tempfile.TemporaryDirectory() as temp:
            nonvideo=Path(temp)/"not-a-video.mp4"
            self.assertFalse(m.video_meta(nonvideo)["source_video_exists"])
            nonvideo.touch()
            self.assertFalse(m.video_meta(nonvideo)["source_video_exists"])
            nonvideo.write_bytes(b"not an MP4")
            info=m.video_meta(nonvideo)
            self.assertTrue(info["source_video_exists"])
            self.assertFalse(info["visual_event_reviewed"])
            self.assertFalse(info["contact_timestamp_aligned_to_ram"])

    def test_source_enrichment_requires_all_three_trials(self):
        result=m.compare_against_control({
            "wood":{"word_stats":{}},
            "leaves":{"word_stats":{}},
        })
        self.assertFalse(result["available"])
        self.assertFalse(result["native_collision_or_contact_verified"])


if __name__=="__main__":
    unittest.main()
