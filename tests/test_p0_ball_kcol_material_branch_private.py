"""Synthetic ONLY source-bounded Ball KCL material dispatch and vector audit."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

DIR=Path(__file__).resolve().parents[1]/"scripts"
TESTS=Path(__file__).resolve().parents[0]
sys.path.insert(0,str(DIR))
mod=importlib.util.spec_from_file_location(
    "p0_ball_material",DIR/"p0_ball_kcol_material_branch_private.py")
m=importlib.util.module_from_spec(mod)
mod.loader.exec_module(m)
p=importlib.util.spec_from_file_location(
    "p0_prior_call_fixture",TESTS/"test_p0_ball_kcol_postcall_context_private.py")
prior_test=importlib.util.module_from_spec(p)
p.loader.exec_module(prior_test)


def fixture():
    words,read=prior_test.fixture()
    for (unit,off),word in m.ORIGINAL_ANCHORS.items():
        words[m.units.UNITS[unit][0]+off]=word
    # Synthetic additional read of a field with the same *offset*, showing
    # why member-offset match alone does not establish ball velocity.
    words[m.units.UNITS["Ball"][0]+0x3600]=prior_test.d(48,0,10,0xAC)
    return words,read


class BallMaterialBranchTests(unittest.TestCase):
    def test_source_5_plus_7_and_exact_anchors(self):
        words,read=fixture()
        result=m.inspect(read)
        self.assertTrue(result["original_five_ball_queries_exactly_qualified"])
        self.assertEqual(result["status"],"SOURCE_MATERIAL_BRANCH_AND_BALL_VECTOR_FIELDS")
        self.assertEqual(len(result["native_windows"]),7)
        self.assertEqual(result["candidate_hit_classifications_checked"],[7,12,13])

    def test_original_halfword_and_bitmask_anchors(self):
        words,read=fixture()
        lo=m.units.UNITS["Ball"][0]
        self.assertEqual(read(lo+0x0B6C),0xA061000A)
        self.assertEqual(read(lo+0x0B78),0x7FC01830)
        self.assertEqual(read(lo+0x0B7C),0x7C00E039)
        self.assertEqual(read(lo+0x14F0),0xA0010008)

    def test_float_stores_are_object_fields_not_verified_velocity(self):
        words,read=fixture()
        result=m.inspect(read)
        acc=result["all_ball_source_candidate_member_field_accesses"]
        observed=[x for x in acc if x["op"]=="stfs" and x["base"]=="r23"]
        self.assertEqual([x["displacement_bytes"] for x in observed],
                         [0xAC,0xB0,0xB4])
        self.assertFalse(result["ball_velocity_field_semantics_proven"])
        self.assertTrue(all(not x["is_ball_velocity_proven"] for x in acc))

    def test_unknown_receiver_same_offset_not_promoted(self):
        words,read=fixture()
        acc=m.inspect(read)["all_ball_source_candidate_member_field_accesses"]
        self.assertIn({"site":"+0x3600","op":"lfs","base":"r10",
                       "displacement_bytes":0xAC,
                       "is_ball_velocity_proven":False},acc)

    def test_source_windows_bounded_and_detail_optional(self):
        words,read=fixture()
        compact=m.inspect(read)
        verbose=m.inspect(read,True)
        self.assertEqual([x["instruction_count"] for x in verbose["native_windows"]],
                         [29,41,70,30,36,76,108])
        self.assertLessEqual(sum(x["instruction_count"] for x in verbose["native_windows"]),m.MAX_WORDS)
        self.assertFalse(any("original_source_words_local_only" in w
                             for w in compact["native_windows"]))
        self.assertTrue(all(
            len(w["original_source_words_local_only"])==w["instruction_count"]
            for w in verbose["native_windows"]))

    def test_bad_postcall_result_anchor_abstains(self):
        words,read=fixture()
        words[m.units.UNITS["Ball"][0]+0x0B64]=0
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_wrong_material_compare_abstains(self):
        words,read=fixture()
        words[m.units.UNITS["Ball"][0]+0x14FC]=0x2800000D
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_wrong_bitmask_polarity_abstains(self):
        words,read=fixture()
        words[m.units.UNITS["Ball"][0]+0x0B7C]=0x7C00E038
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_wrong_vector_store_field_abstains(self):
        words,read=fixture()
        words[m.units.UNITS["Ball"][0]+0x1510]=prior_test.d(52,0,23,0xB8)
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_bad_original_ball_to_kcol_target_abstains(self):
        words,read=fixture()
        pc=m.units.UNITS["Ball"][0]+0x27B0
        words[pc]=prior_test.bl(pc,m.units.UNITS["GolfKCol"][0]+0x1BB8)
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_no_physics_training_and_no_private_records(self):
        import json
        words,read=fixture()
        report=m.inspect(read)
        txt=json.dumps(report)
        self.assertNotIn("original_source_words_local_only",txt)
        self.assertNotIn("tree_positions",txt)
        self.assertNotIn("KCL_vertices",txt)
        self.assertFalse(report["native_tree_contact_dispatch_proven"])
        self.assertFalse(report["tree_hitbox_geometry_verified"])
        self.assertFalse(report["training_approved"])


if __name__=="__main__":
    unittest.main()
