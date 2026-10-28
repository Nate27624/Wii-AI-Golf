"""Fabricated source-control tests for *post-return* global pointer store CFG."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import review_p0_global_slot_post_return_paths as study


def dform(op,rt,ra,imm):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&0xffff)


def b(pc,dst,link=True):
    return (18<<26)|((dst-pc)&0x03fffffc)|int(link)


def bc(pc,dst):
    return (16<<26)|((dst-pc)&0xfffc)


def fake():
    d={pc:0x60000000 for pc in range(study.POST_ENTRY,study.STORE_PC+4,4)}
    d[study.RETURN_PC]=0x4e800020
    d[study.ADDI_PC]=dform(14,3,0,100)
    d[study.FIRST_BL]=b(study.FIRST_BL,0x8029B000)
    d[study.BRANCH_PC]=bc(study.BRANCH_PC,study.STORE_PC)
    d[study.SECOND_BL]=b(study.SECOND_BL,0x8029B300)
    d[study.STORE_PC]=dform(36,3,13,-100)
    return d


class GlobalSlotPostReturnPaths(unittest.TestCase):
    def test_two_call_results_are_separate_candidate_paths(self):
        x=study.analyze(fake().__getitem__,-100)
        self.assertTrue(x["preceding_instruction_is_exact_plain_blr"])
        self.assertTrue(x["hypothetical_entry_can_reach_store"])
        self.assertTrue(x["path_with_r3_from_first_bl_possible"])
        self.assertTrue(x["path_with_r3_from_second_bl_possible"])
        self.assertEqual(x["store_r3_candidate_sources_from_this_entry"],
                         ["return_from_first_bl","return_from_second_bl"])
        self.assertTrue(x["conditional_branch_may_skip_second_bl"])
        self.assertFalse(x["calls_confirmed_allocator_or_constructor"])
        self.assertFalse(x["runtime_store_value_verified"])
        self.assertFalse(x["training_approved"])

    def test_direct_public_call_targets_reported_no_bytes(self):
        x=study.analyze(fake().__getitem__,-100)
        self.assertEqual(x["first_bl_target_public_code_pc"],"0x8029B000")
        self.assertEqual(x["second_bl_target_public_code_pc"],"0x8029B300")
        self.assertFalse(x["callee_identities_verified_by_public_symbol_index"])

    def test_previous_instruction_not_blr_fails_closed(self):
        d=fake()
        d[study.RETURN_PC]=0x4e800420
        with self.assertRaises(ValueError): study.analyze(d.__getitem__,-100)

    def test_conditional_branch_not_to_store_refused(self):
        d=fake()
        d[study.BRANCH_PC]=bc(study.BRANCH_PC,study.STORE_PC+4)
        with self.assertRaises(ValueError): study.analyze(d.__getitem__,-100)

    def test_first_bl_wrong_opcode_refused(self):
        d=fake()
        d[study.FIRST_BL]=b(study.FIRST_BL,0x8029B000,link=False)
        with self.assertRaises(ValueError): study.analyze(d.__getitem__,-100)

    def test_second_bl_wrong_opcode_refused(self):
        d=fake()
        d[study.SECOND_BL]=dform(14,3,0,1)
        with self.assertRaises(ValueError): study.analyze(d.__getitem__,-100)

    def test_zero_addi_refused(self):
        d=fake()
        d[study.ADDI_PC]=dform(14,3,0,0)
        with self.assertRaises(ValueError): study.analyze(d.__getitem__,-100)

    def test_addi_other_ra_refused(self):
        d=fake()
        d[study.ADDI_PC]=dform(14,3,3,100)
        with self.assertRaises(ValueError): study.analyze(d.__getitem__,-100)

    def test_store_other_slot_or_register_refused(self):
        d=fake()
        d[study.STORE_PC]=dform(36,5,13,-100)
        with self.assertRaises(ValueError): study.analyze(d.__getitem__,-100)
        d=fake()
        d[study.STORE_PC]=dform(36,3,13,-99)
        with self.assertRaises(ValueError): study.analyze(d.__getitem__,-100)

    def test_first_call_result_overwritten_before_conditional_branch(self):
        d=fake()
        d[study.FIRST_BL+4]=dform(14,3,0,0)
        x=study.analyze(d.__getitem__,-100)
        self.assertFalse(x["path_with_r3_from_first_bl_possible"])
        self.assertTrue(x["path_with_r3_from_second_bl_possible"])
        self.assertIn("other_or_unrecognized_r3_assignment",x["store_r3_candidate_sources_from_this_entry"])

    def test_nonlocal_branch_in_entry_does_not_promote_to_proof(self):
        d=fake()
        d[study.POST_ENTRY]=b(study.POST_ENTRY,0x8029B100,link=False)
        x=study.analyze(d.__getitem__,-100)
        self.assertTrue(x["local_control_flow_escape_possible"])
        self.assertFalse(x["hypothetical_entry_can_reach_store"])
        self.assertTrue(x["external_predecessors_to_store_unexamined"])

    def test_result_categorical_no_private_runtime_values(self):
        x=study.analyze(fake().__getitem__,-100)
        result=json.dumps(x)
        self.assertNotIn("0x900",result)
        self.assertNotIn("raw_instr",result)
        self.assertNotIn("private_address",result)
        self.assertFalse(x["source_global_is_rendered_ball_verified"])
        self.assertFalse(x["physical_ball_xyz_verified"])

    def test_bad_signed_displacement_refused(self):
        for bad in (-40000,40000,None,3.25):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                study.analyze(fake().__getitem__,bad)


if __name__=="__main__":
    unittest.main()
