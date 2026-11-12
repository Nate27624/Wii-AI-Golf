"""Synthetic-only Rev1 KCol CR0 EQ and Ball floating source tests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

m=load("p0_kcol_cr0_fp",ROOT/"scripts"/"p0_ball_kcol_cr0_float_sources_private.py")
fixture=load("p0_kcol_cr0_fp_fixture",
             ROOT/"tests"/"test_p0_ball_kcol_material_vector_edges_private.py")


def d(op,rt,ra,imm):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&65535)


def bc(pc,dest,bo=12,bi=2):
    delta=dest-pc
    if delta%4 or delta<-(1<<15) or delta>=(1<<15):
        raise ValueError("Synthetic PPC BC offset out of range")
    return (16<<26)|(bo<<21)|(bi<<16)|(delta&0xfffc)


def program():
    p=fixture.program()
    for off,branch,op,reg,code,target in m.COMPARE_PAIRS:
        p[m.BALL+off]=d(op,0,reg,code)
        p[m.BALL+branch]=bc(m.BALL+branch,m.BALL+target)
    for index,(load,store,offset) in enumerate(m.FLOAT_PAIRS):
        p[m.BALL+load]=d(48,0,1,16+index*4)
        p[m.BALL+store]=d(52,0,23,offset)
    return p


def read(words):
    return lambda pc:words.get(pc,0x60000000)


class KcolCR0FpSourceTests(unittest.TestCase):
    def test_all_four_exact_cmp_to_beq_source_edges(self):
        cs=m.pairs(read(program()))
        self.assertEqual(len(cs),4)
        self.assertEqual([x["compared_literal_class"] for x in cs],[13,7,7,12])
        self.assertTrue(all(x[
            "exact_adjacent_cmp_to_beq_CR0_EQ_source_verified"] for x in cs))
        self.assertEqual([x["source_beq_target"] for x in cs[2:]],
                         ["Ball+0x152C","Ball+0x152C"])
        self.assertFalse(cs[2]["native_collision_event_or_wood_foliage_material_verified"])

    def test_main_ball_class_7_and_12_skip_triad_in_source(self):
        x=m.inspect(read(program()))
        flow=x["main_query_classification_source_flow"]
        self.assertTrue(flow["main_query_source_class_7_or_12_beq_skips_three_stores"])
        self.assertTrue(flow["two_beq_source_targets_bypass_float_triad"])
        self.assertTrue(flow[
            "fallthrough_from_both_beq_source_has_no_intervening_branch_in_triad"])
        self.assertFalse(flow["actual_main_query_return_success_and_flags_executed_proven"])

    def test_all_three_f0_stfs_have_adjacent_lfs_f0(self):
        p=m.float_pairs(read(program()))
        self.assertEqual([x["member_byte_displacement"] for x in p],[172,176,180])
        self.assertTrue(all(x[
            "adjacent_lfs_f0_to_stfs_f0_same_register_verified"] for x in p))
        self.assertEqual([x["source_preceding_FP_instruction"]["base_GPR"]
                          for x in p],[1,1,1])
        self.assertFalse(p[0]["source_FP_load_is_KCol_query_output_proven"])

    def test_wrong_branch_BO_not_a_beq_and_does_not_promote(self):
        p=program()
        at=m.BALL+0x14F8
        p[at]=bc(at,m.BALL+0x152C,bo=4,bi=2)
        cs=m.pairs(read(p))
        self.assertFalse(cs[2]["exact_adjacent_cmp_to_beq_CR0_EQ_source_verified"])
        self.assertFalse(m.main_class_flow(read(p),cs,m.float_pairs(read(p)))[
            "main_query_source_class_7_or_12_beq_skips_three_stores"])

    def test_branch_BI_not_CR0_EQ_does_not_promote(self):
        p=program()
        at=m.BALL+0x1500
        p[at]=bc(at,m.BALL+0x152C,bo=12,bi=6)
        cs=m.pairs(read(p))
        self.assertFalse(cs[3]["exact_adjacent_cmp_to_beq_CR0_EQ_source_verified"])

    def test_compare_CR_field_other_than_0_does_not_promote(self):
        p=program()
        p[m.BALL+0x14FC]=d(10,0,0,12)|(1<<23)
        cs=m.pairs(read(p))
        self.assertFalse(cs[3]["exact_adjacent_cmp_to_beq_CR0_EQ_source_verified"])

    def test_compare_L_bit_unexpected_abstains_from_branch_link(self):
        p=program()
        p[m.BALL+0x14F4]=d(10,0,0,7)|(1<<21)
        cs=m.pairs(read(p))
        self.assertFalse(cs[2]["exact_adjacent_cmp_to_beq_CR0_EQ_source_verified"])

    def test_wrong_branch_target_fails_original_source_anchor(self):
        p=program()
        at=m.BALL+0x14F8
        p[at]=bc(at,m.BALL+0x1528)
        with self.assertRaises(ValueError):
            m.pairs(read(p))

    def test_non_lfs_predecessor_does_not_prove_f0_source(self):
        p=program()
        p[m.BALL+0x1504]=d(50,0,1,16)
        fp=m.float_pairs(read(p))
        self.assertFalse(fp[0]["adjacent_lfs_f0_to_stfs_f0_same_register_verified"])
        self.assertTrue(fp[1]["adjacent_lfs_f0_to_stfs_f0_same_register_verified"])

    def test_lfs_other_FPR_is_not_f0_store_source(self):
        p=program()
        p[m.BALL+0x1514]=d(48,2,1,24)
        fp=m.float_pairs(read(p))
        self.assertFalse(fp[2]["adjacent_lfs_f0_to_stfs_f0_same_register_verified"])

    def test_wrong_float_store_receiver_offset_abstains(self):
        p=program()
        p[m.BALL+0x1518]=d(52,0,23,184)
        with self.assertRaises(ValueError):
            m.float_pairs(read(p))

    def test_branch_inside_float_triad_abstains_from_straightline(self):
        p=program()
        p[m.BALL+0x1514]=bc(m.BALL+0x1514,m.BALL+0x152C)
        rows=m.pairs(read(p))
        fp=m.float_pairs(read(p))
        flow=m.main_class_flow(read(p),rows,fp)
        self.assertFalse(flow[
            "fallthrough_from_both_beq_source_has_no_intervening_branch_in_triad"])

    def test_no_wood_or_velocity_training_promotions(self):
        report=m.inspect(read(program()))
        self.assertTrue(report["status"].startswith("SHA_QUALIFIED"))
        self.assertFalse(report["native_selected_Ball_collision_response_proven"])
        self.assertFalse(report["prism_code_7_12_13_trunk_or_foliage_identity_proven"])
        self.assertFalse(report["native_spin_impulse_restitution_semantics_proven"])
        self.assertFalse(report["training_approved"])
        s=json.dumps(report,sort_keys=True)
        self.assertNotIn("0x90008000",s)
        self.assertNotIn("native_PPC_instruction_word",s)
        self.assertNotIn("private_archive_path",s)


if __name__=="__main__":
    unittest.main()
