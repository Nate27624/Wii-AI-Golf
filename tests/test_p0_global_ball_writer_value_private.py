"""Fabricated tests of single source-global slot stw value classification."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_p0_global_ball_source_xrefs_private as mod


def dform(op,reg,ra,imm):
    return (op<<26)|(reg<<21)|(ra<<16)|(imm&0xffff)


def mr(dest,src):
    return (31<<26)|(src<<21)|(dest<<16)|(src<<11)|(444<<1)


class GlobalPointerSingleStore(unittest.TestCase):
    def setUp(self):
        self.disp=-100
        self.words={
            mod.WRITER_PC:dform(36,0,13,self.disp),
            mod.WRITER_PC-8:dform(14,0,0,0),
        }
        self.read=lambda addr:self.words.get(addr,0x60000000)

    def test_single_stw_register_and_zero_literal_hint(self):
        x=mod.classify_known_writer_value(self.read,self.disp)
        self.assertEqual(x["store_source_register"],"r0")
        self.assertEqual(x["candidate_nearest_recognized_definition_class"],"literal_zero_candidate")
        self.assertTrue(x["source_value_may_be_zero_candidate"])
        self.assertFalse(x["store_value_runtime_zero_verified"])
        self.assertFalse(x["source_writer_ran_during_wedge_verified"])

    def test_load_from_memory_candidate_not_zero(self):
        self.words[mod.WRITER_PC]=dform(36,3,13,self.disp)
        self.words[mod.WRITER_PC-8]=dform(32,3,31,12)
        x=mod.classify_known_writer_value(self.read,self.disp)
        self.assertEqual(x["store_source_register"],"r3")
        self.assertEqual(x["candidate_nearest_recognized_definition_class"],"integer_memory_load")
        self.assertFalse(x["source_value_may_be_zero_candidate"])

    def test_mr_reg_provenance_classified(self):
        self.words[mod.WRITER_PC]=dform(36,3,13,self.disp)
        self.words[mod.WRITER_PC-8]=mr(3,31)
        x=mod.classify_known_writer_value(self.read,self.disp)
        self.assertEqual(x["candidate_nearest_recognized_definition_class"],"mr_from_other_register")

    def test_unrecognized_value_source_kept_unknown(self):
        self.words[mod.WRITER_PC]=dform(36,3,13,self.disp)
        x=mod.classify_known_writer_value(self.read,self.disp)
        self.assertEqual(x["candidate_nearest_recognized_definition_class"],"unknown_no_recognized_def_in_bounded_window")
        self.assertFalse(x["source_register_reaching_definition_fully_verified"])

    def test_branch_after_candidate_def_marks_hazard(self):
        self.words[mod.WRITER_PC-4]=(18<<26)
        x=mod.classify_known_writer_value(self.read,self.disp)
        self.assertTrue(x["control_transfer_after_candidate_definition"])
        self.assertTrue(x["control_transfer_in_window"])
        self.assertFalse(x["store_value_runtime_zero_verified"])

    def test_branch_before_candidate_def_not_same_hazard(self):
        self.words[mod.WRITER_PC-12]=(16<<26)
        x=mod.classify_known_writer_value(self.read,self.disp)
        self.assertTrue(x["control_transfer_in_window"])
        self.assertFalse(x["control_transfer_after_candidate_definition"])

    def test_wrong_stw_displacement_fails_closed(self):
        self.words[mod.WRITER_PC]=dform(36,0,13,-101)
        with self.assertRaises(ValueError):
            mod.classify_known_writer_value(self.read,self.disp)

    def test_wrong_source_slot_base_fails_closed(self):
        self.words[mod.WRITER_PC]=dform(36,0,12,self.disp)
        with self.assertRaises(ValueError):
            mod.classify_known_writer_value(self.read,self.disp)

    def test_not_store_opcode_refuses(self):
        self.words[mod.WRITER_PC]=dform(32,0,13,self.disp)
        with self.assertRaises(ValueError):
            mod.classify_known_writer_value(self.read,self.disp)

    def test_no_native_words_addresses_or_reaching_definition_claim(self):
        out=mod.classify_known_writer_value(self.read,self.disp)
        s=str(out)
        self.assertNotIn("0x9000",s)
        self.assertNotIn("private",s)
        self.assertEqual(out["source_unit_relative_store_pc"],"+0x3084")
        self.assertFalse(out["source_register_reaching_definition_fully_verified"])


if __name__=="__main__":
    unittest.main()
