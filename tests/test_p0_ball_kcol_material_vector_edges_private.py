"""Synthetic-only original Ball-KCol comparison/control and vector source tests."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "p0_kcol_edges",ROOT/"scripts"/"p0_ball_kcol_material_vector_edges_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def d(op,rt,ra,imm):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&0xFFFF)


def transfer(pc,target,linked=False,conditional=False):
    delta=target-pc
    if delta%4:
        raise ValueError("Unaligned synthetic branch")
    if conditional:
        return (16<<26)|(12<<21)|(2<<16)|(delta&0xFFFC)
    return (18<<26)|(delta&0x03FFFFFC)|int(linked)


def program():
    p={
        m.KCOL+0x0118:d(40,0,3,14),
        m.KCOL+0x011C:d(44,0,28,0),
        m.BALL+0x0B60:transfer(m.BALL+0x0B60,m.KCOL+0x1AC4,linked=True),
        m.BALL+0x14D0:transfer(m.BALL+0x14D0,m.KCOL,linked=True),
        m.BALL+m.STACK_HALFWORD:d(40,0,1,8),
    }
    for off,reg,imm,op in m.COMPARE_SITES:
        p[m.BALL+off]=d(op,0,reg,imm)
    for off,disp in m.STORES:
        p[m.BALL+off]=d(52,0,23,disp)
    p[m.BALL+0x0B88]=transfer(
        m.BALL+0x0B88,m.BALL+0x0BB8,conditional=True)
    p[m.BALL+0x0B94]=transfer(
        m.BALL+0x0B94,m.BALL+0x0BB8,conditional=True)
    p[m.BALL+0x14F8]=transfer(
        m.BALL+0x14F8,m.BALL+0x151C,conditional=True)
    p[m.BALL+0x1500]=transfer(
        m.BALL+0x1500,m.BALL+0x151C,conditional=True)
    return p


def read(p):
    return lambda pc:p.get(pc,0x60000000)


class P0BallKColMaterialVectorEdgesTests(unittest.TestCase):
    def test_exact_original_prism_result_and_main_call_anchor(self):
        a=m.source_anchors(read(program()))
        self.assertEqual(a["verified_prism_classification_source"],
                         "GolfKCol+0x0118")
        self.assertEqual(a["ball_main_query_direct_BL"],"Ball+0x14D0")
        self.assertFalse(a["kcol_code_number_is_wood_or_foliage_proven"])

    def test_exact_source_literal_material_comparisons(self):
        a=m.source_anchors(read(program()))
        vals=[x["literal_class_code"]
              for x in a["source_ball_comparisons"]]
        self.assertEqual(vals,[13,7,7,12])

    def test_wrong_compared_class_abstains(self):
        p=program()
        p[m.BALL+0x14FC]=d(10,0,0,13)
        with self.assertRaises(ValueError):
            m.source_anchors(read(p))

    def test_wrong_prism_class_output_abstains(self):
        p=program()
        p[m.KCOL+0x011C]=d(44,0,27,0)
        with self.assertRaises(ValueError):
            m.source_anchors(read(p))

    def test_wrong_float_field_abstains(self):
        p=program()
        p[m.BALL+0x1510]=d(52,0,23,184)
        with self.assertRaises(ValueError):
            m.source_anchors(read(p))

    def test_wrong_kcol_BL_target_abstains(self):
        p=program()
        p[m.BALL+0x14D0]=transfer(
            m.BALL+0x14D0,m.KCOL+4,linked=True)
        with self.assertRaises(ValueError):
            m.source_anchors(read(p))

    def test_compare_followed_by_conditional_branch_is_not_material_proof(self):
        a=m.compare_branches(read(program()))
        self.assertEqual(len(a),4)
        for entry in a:
            self.assertTrue(entry["bounded_nearby_control_edges"])
            self.assertFalse(entry["compare_CR_to_branch_CR_link_proven"])
            self.assertFalse(entry["bounded_nearby_control_edges"][0][
                "actual_tree_material_dispatch_proven"])

    def test_all_three_candidate_float_stores_may_reach_in_synthetic_Cfg(self):
        a=m.local_reachability(read(program()))
        self.assertEqual(len(a["source_vector_member_store_static_routes"]),3)
        self.assertTrue(all(x[
            "source_may_reach_from_0x14D0_under_bounded_direct_CFG"]
            for x in a["source_vector_member_store_static_routes"]))
        self.assertFalse(a["whole_game_true_CFG_and_guest_outcomes_proven"])

    def test_unconditional_early_skip_blocks_static_float_store_witness(self):
        p=program()
        p[m.BALL+0x14D4]=transfer(m.BALL+0x14D4,m.BALL+0x1520)
        a=m.local_reachability(read(p))
        self.assertTrue(all(not x[
            "source_may_reach_from_0x14D0_under_bounded_direct_CFG"]
            for x in a["source_vector_member_store_static_routes"]))

    def test_unsupported_branch_is_conservatively_unresolved(self):
        p=program()
        p[m.BALL+0x14D4]=0x4E800020
        a=m.local_reachability(read(p))
        self.assertTrue(all(not x[
            "source_may_reach_from_0x14D0_under_bounded_direct_CFG"]
            for x in a["source_vector_member_store_static_routes"]))

    def test_static_source_does_not_conflate_tree_hit_and_velocity(self):
        a=m.inspect(read(program()))
        self.assertFalse(a["class_7_12_13_tree_trunk_foliage_identity_proven"])
        self.assertFalse(a["actual_wood_or_foliage_collision_handler_proven"])
        self.assertFalse(a["active_selected_Ball_velocity_update_proven"])
        self.assertFalse(a["native_impact_restitution_or_spin_proven"])
        self.assertFalse(a["training_approved"])
        s=json.dumps(a)
        self.assertNotIn("original_native_instruction_word",s)
        self.assertNotIn("private_memory_pointer",s)
        self.assertNotIn("0x90008000",s)


if __name__=="__main__":
    unittest.main()
