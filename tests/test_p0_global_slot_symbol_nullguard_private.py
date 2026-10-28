"""Native-free public symbol target and PPC branch BO/BI/null-check tests."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import review_p0_global_slot_symbol_nullguard as m

def d(op,reg,base,imm):
    return (op<<26)|(reg<<21)|(base<<16)|(imm&0xffff)

def call(pc,dst):
    return (18<<26)|((dst-pc)&0x03fffffc)|1

def bc(pc,dst,bo=12,bi=2):
    return (16<<26)|(bo<<21)|(bi<<16)|((dst-pc)&0xfffc)

def setup():
    p=m.prior
    words={pc:0x60000000 for pc in range(p.POST_ENTRY,p.STORE_PC+4,4)}
    words[p.RETURN_PC]=0x4e800020
    words[p.ADDI_PC]=d(14,3,0,0x1ac)
    words[p.FIRST_BL]=call(p.FIRST_BL,0x800a3244)
    words[m.COMPARE_PC]=d(10,0,3,0)
    words[p.BRANCH_PC]=bc(p.BRANCH_PC,p.STORE_PC)
    words[p.SECOND_BL]=call(p.SECOND_BL,0x8029ab78)
    words[p.STORE_PC]=d(36,3,13,-100)
    return words

class PublicMapAndBranchBOTests(unittest.TestCase):
    def test_true_null_guard_and_two_return_source_candidates(self):
        o=m.analyze(setup().__getitem__,-100)
        self.assertTrue(o["exact_operator_new_target_verified"])
        self.assertTrue(o["source_function_entry_matches_public_map"])
        self.assertEqual(o["first_callee_public_symbol"],"__nw__FUl")
        self.assertEqual(o["second_callee_public_symbol"],"fn_8029AB78")
        self.assertTrue(o["null_allocation_skips_second_call_pattern_verified"])
        self.assertTrue(o["second_call_possible_per_BO_category"])
        self.assertEqual(o["post_return_store_r3_candidate_classes_after_BO"],
                         ["return_from_first_bl","return_from_second_bl"])
        self.assertFalse(o["second_callee_is_ball_constructor_verified"])
        self.assertFalse(o["training_approved"])

    def test_BO_always_does_not_invent_second_call_path(self):
        words=setup()
        words[m.BRANCH_PC]=bc(m.BRANCH_PC,m.prior.STORE_PC,bo=20,bi=0)
        o=m.analyze(words.__getitem__,-100)
        self.assertEqual(o["branch_to_store"]["BO_category"],"unconditional_always")
        self.assertFalse(o["second_call_possible_per_BO_category"])
        self.assertEqual(o["post_return_store_r3_candidate_classes_after_BO"],
                         ["return_from_first_bl"])
        self.assertFalse(o["null_allocation_skips_second_call_pattern_verified"])

    def test_BNE_zero_compare_not_null_failure_skip(self):
        words=setup()
        words[m.BRANCH_PC]=bc(m.BRANCH_PC,m.prior.STORE_PC,bo=4)
        o=m.analyze(words.__getitem__,-100)
        self.assertTrue(o["branch_to_store"]["CR0_EQ_bit_selected"])
        self.assertFalse(o["branch_to_store"]["CR0_EQ_desired_true"])
        self.assertFalse(o["null_allocation_skips_second_call_pattern_verified"])

    def test_unknown_CR_bit_abstains_on_null_semantics(self):
        words=setup()
        words[m.BRANCH_PC]=bc(m.BRANCH_PC,m.prior.STORE_PC,bo=12,bi=6)
        o=m.analyze(words.__getitem__,-100)
        self.assertFalse(o["null_allocation_skips_second_call_pattern_verified"])

    def test_cmpwi_signed_zero_also_satisfies_zero_guard(self):
        words=setup()
        words[m.COMPARE_PC]=d(11,0,3,0)
        o=m.analyze(words.__getitem__,-100)
        self.assertTrue(o["null_allocation_skips_second_call_pattern_verified"])
        self.assertEqual(o["compare_after_operator_new"]["kind"],"cmpwi_cr0_r3_zero")

    def test_compare_wrong_register_refuses_semantic_claim(self):
        words=setup()
        words[m.COMPARE_PC]=d(10,0,4,0)
        o=m.analyze(words.__getitem__,-100)
        self.assertFalse(o["null_allocation_skips_second_call_pattern_verified"])

    def test_compare_nonzero_refuses_semantic_claim(self):
        words=setup()
        words[m.COMPARE_PC]=d(11,0,3,1)
        o=m.analyze(words.__getitem__,-100)
        self.assertFalse(o["null_allocation_skips_second_call_pattern_verified"])

    def test_unknown_compare_must_abstain(self):
        words=setup()
        words[m.COMPARE_PC]=0x60000000
        o=m.analyze(words.__getitem__,-100)
        self.assertFalse(o["compare_after_operator_new"]["compare_r3_zero_verified"])
        self.assertFalse(o["null_allocation_skips_second_call_pattern_verified"])

    def test_wrong_operator_new_call_refuses(self):
        words=setup()
        words[m.FIRST_CALL]=call(m.FIRST_CALL,0x800a3250)
        with self.assertRaises(ValueError):
            m.analyze(words.__getitem__,-100)

    def test_wrong_golf_second_call_refuses(self):
        words=setup()
        words[m.SECOND_CALL]=call(m.SECOND_CALL,0x8029ab7c)
        with self.assertRaises(ValueError):
            m.analyze(words.__getitem__,-100)

    def test_invalid_non_bc_rejected(self):
        with self.assertRaises(ValueError):
            m.branch_BO_BI(0x48000000)
        with self.assertRaises(ValueError):
            m.branch_BO_BI(-1)

    def test_ctr_branch_not_automatically_CR0_null_skip(self):
        words=setup()
        words[m.BRANCH_PC]=bc(m.BRANCH_PC,m.prior.STORE_PC,bo=16,bi=2)
        o=m.analyze(words.__getitem__,-100)
        self.assertEqual(o["branch_to_store"]["BO_category"],"CTR_condition")
        self.assertFalse(o["null_allocation_skips_second_call_pattern_verified"])

    def test_safe_categorical_output_no_runtime_addresses_or_bits(self):
        o=m.analyze(setup().__getitem__,-100)
        txt=json.dumps(o)
        self.assertNotIn("0x900",txt)
        self.assertNotIn("raw_instruction",txt)
        self.assertFalse(o["actual_written_pointer_value_verified"])
        self.assertFalse(o["source_pointer_is_initialized_to_new_object_verified"])
        self.assertEqual(o["first_callee_unit_relative_entry"],"+0x0618")
        self.assertEqual(o["second_callee_unit_relative_entry"],"+0x3BA0")

if __name__=="__main__":
    unittest.main()
