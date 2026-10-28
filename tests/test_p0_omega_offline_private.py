"""Native-free, no-network regression tests for P0 omega batch."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "scripts"))
import omega_p0_offline_private as omega

def graph():
    pairs=[]
    for a in range(1,8):
        for b in range(a+1,8):
            same=(a<=2)==(b<=2)
            pairs.append({
                "capture_pair_unordered":[a,b],
                "same_source_owner_hole_pin_tee_and_config":same,
                "current_changed_components":3 if same else None,
                "cache_CC_changed_components":0 if same else None,
                "cache_F0_changed_components":0 if same else None,
                "cache_FC_changed_components":0 if same else None})
    return {
        "capture_count":7,"unordered_pairs_exhaustively_compared":21,
        "original_archive_SHA_checked_before_and_after":True,
        "human_phase_to_file_mapping_machine_verified":False,
        "source_context_group_count":2,"nodes":[{}]*7,"pairs":pairs}

def receiver():
    return {"seven_original_sha_verified_before_and_after":True,
        "source_global_outside_four_roster_in_all_captures":True,
        "both_inner_static_cfg_must_flow":False,
        "any_static_source_global_load_candidate":False,
        "receiver_chains":[{
            "outer_source_function":name,
            "outer_direct_call_count_bounded":1,
            "outer_source_status":"SYNTAX_ONLY_WITH_CONTROL_FLOW_HAZARD",
            "near_call_r3_class":"mr_r3_from_r31",
            "near_call_r3_provenance_hint":"OTHER_OR_UNRESOLVED_GPR_R3_SOURCE",
            "inner_source_function":inner,
            "inner_cfg_status":"ABSTAIN_SOURCE_UNRESOLVED"}
          for name,inner in (("SimulateManager_outer_to_ball_local","fn_80299ACC"),
                            ("MapObjBall_outer_to_ball_local","fn_80299C20"))]}

class OmegaTests(unittest.TestCase):
    def test_all_pairs_and_abstentions(self):
        x=omega._graph_extract(graph())
        self.assertEqual((x["context_qualified_unordered_pairs"],x["context_incompatible_abstained_pairs"]),(11,10))
        self.assertEqual(len(x["pairs_of_interest"]),5)

    def test_missing_or_duplicate_pair_abstains(self):
        x=graph()
        x["pairs"].pop()
        with self.assertRaises(omega.Abstain):omega._graph_extract(x)
        x=graph()
        x["pairs"][-1]=x["pairs"][0]
        with self.assertRaises(omega.Abstain):omega._graph_extract(x)

    def test_false_phase_or_source_hash_claim_abstains(self):
        x=graph();x["human_phase_to_file_mapping_machine_verified"]=True
        with self.assertRaises(omega.Abstain):omega._graph_extract(x)
        x=graph();x["original_archive_SHA_checked_before_and_after"]=False
        with self.assertRaises(omega.Abstain):omega._graph_extract(x)

    def test_receiver_exact_order_and_source_gate(self):
        self.assertTrue(omega._receiver_extract(receiver())["outside_four_player_ball_roster_7_of_7"])
        x=receiver();x["receiver_chains"].reverse()
        with self.assertRaises(omega.Abstain):omega._receiver_extract(x)
        x=receiver();x["seven_original_sha_verified_before_and_after"]=False
        with self.assertRaises(omega.Abstain):omega._receiver_extract(x)

    def test_result_kind_training_and_publishing_gate(self):
        for bad in (
            {"kind":"wrong","training_approved":False,"allowed_to_publish":False},
            {"kind":"x","training_approved":True,"allowed_to_publish":False},
            {"kind":"x","training_approved":False,"allowed_to_publish":True}):
            with patch.object(omega,"_exec",return_value=json.dumps(bad)):
                with self.assertRaises(omega.Abstain):omega._json_study(Path("/tmp"),["x"],"x")

    def test_exact_pinned_sha_instead_of_moving_pr_head(self):
        with patch.object(omega,"_exists_git_object",return_value=True) as has, \
             patch.object(omega,"_git",return_value=omega.PINS["cfg"][1]) as git:
            self.assertEqual(omega.ensure_pinned_commit(Path("/x"),"cfg"),omega.PINS["cfg"][1])
            self.assertEqual(git.call_count,1)
            self.assertEqual(has.call_count,3)

    def test_fetch_by_exact_sha_when_pr_head_moved(self):
        with patch.object(omega,"_exists_git_object",side_effect=[False,False,True]) as has, \
             patch.object(omega,"_git",return_value=omega.PINS["cfg"][1]) as git:
            self.assertEqual(omega.ensure_pinned_commit(Path("/x"),"cfg"),omega.PINS["cfg"][1])
            self.assertEqual(git.call_count,3)

    def test_unavailable_pin_abstains(self):
        with patch.object(omega,"_exists_git_object",return_value=False), \
             patch.object(omega,"_git",return_value="unknown"):
            with self.assertRaises(omega.Abstain):
                omega.ensure_pinned_commit(Path("/x"),"cfg")

    def test_canonical_manifest_not_other_folder(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);repo=base/"Wii-AI-Golf";repo.mkdir()
            root=base/"Wii-AI-Golf-Data"/"captures";root.mkdir(parents=True)
            with self.assertRaises(omega.Abstain):omega._archive(repo,None)
            p=root/"p0-new-cohort-foo-PRIVATE";p.mkdir()
            m={"kind":"p0-private-numbered-capture-inventory",
               "capture_count":7,"capture_numbers":list(range(1,8)),
               "human_phase_file_mapping_verified":False,"training_approved":False}
            (p/"manifest-PRIVATE.json").write_text(json.dumps(m))
            self.assertEqual(omega._archive(repo,None)[0],p)
            m["training_approved"]=True
            (p/"manifest-PRIVATE.json").write_text(json.dumps(m))
            with self.assertRaises(omega.Abstain):omega._archive(repo,None)

    def test_failure_output_never_echoes_secret(self):
        from io import StringIO
        with patch.object(omega,"study",side_effect=omega.Abstain("PRIVATE 0xDEADBEEF")), \
             patch("sys.stdout",new_callable=StringIO) as stdout:
            self.assertEqual(omega.main(["--repo","/x"]),2)
            self.assertNotIn("PRIVATE",stdout.getvalue())
            self.assertNotIn("DEADBEEF",stdout.getvalue())

    def test_private_digest_is_not_hex_published(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"secret.bin";p.write_bytes(b"test")
            self.assertEqual(len(omega._file_digest(p)),32)
            self.assertIsInstance(omega._file_digest(p),bytes)

if __name__ == "__main__":
    unittest.main()
