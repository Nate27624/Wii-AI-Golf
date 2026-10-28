"""Native-free constructor return candidate synthetic controls."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import review_p0_ball_constructor_return as m

def bl(pc,target):
    return (18<<26)|((target-pc)&0x03fffffc)|1
def mr(ra,rs):
    return (31<<26)|(rs<<21)|(ra<<16)|(rs<<11)|(444<<1)

def make():
    words={pc:0x60000000 for pc in range(m.BALL_CTOR_ENTRY,m.BALL_CTOR_END,4)}
    words[m.BALL_CTOR_ENTRY+4]=mr(31,3)
    words[m.BASE_CTOR_CALL]=bl(m.BASE_CTOR_CALL,m.BASE_CTOR_TARGET)
    words[m.CLASS_TAG_PC]=(36<<26)|(3<<21)|(31<<16)|8
    words[m.BALL_CTOR_END-8]=mr(3,31)
    words[m.BALL_CTOR_END-4]=0x4e800020
    return words


class ConstructorReturn(unittest.TestCase):
    def test_exact_base_call_and_saved_return_receiver_candidate(self):
        o=m.analyze(make().__getitem__)
        self.assertTrue(o["base_class_constructor_direct_call_verified"])
        self.assertEqual(o["base_constructor_public_symbol"],"fn_80290A48")
        self.assertEqual(o["entry_receiver_saved_register_classes"],["r31"])
        self.assertEqual(o["public_constructor_return_count_within_symbol"],1)
        self.assertTrue(o["bounded_exit_r3_syntactic_relationships"][0]
                        ["r3_mr_from_entry_saved_register_syntactically_possible"])
        self.assertFalse(o["all_return_values_must_equal_ctor_receiver_verified"])
        self.assertFalse(o["constructor_returns_allocated_object_on_nonnull_branch_verified"])

    def test_volatile_r3_can_be_overwritten_by_store_update_base(self):
        # Prior mr r3,r31 must NOT survive stwu r0,4(r3): writes rA=r3.
        words=make()
        words[m.BALL_CTOR_END-12]=mr(3,31)
        for op in (37,39,45,49,51,53,55):
            with self.subTest(op=op):
                changed=dict(words)
                changed[m.BALL_CTOR_END-8]=(op<<26)|(0<<21)|(3<<16)|4
                o=m.analyze(changed.__getitem__)
                ret=o["bounded_exit_r3_syntactic_relationships"][0]
                self.assertEqual(
                    ret["nearest_supported_r3_definition_class"],
                    "memory_update_base_r3")
                self.assertFalse(
                    ret["r3_mr_from_entry_saved_register_syntactically_possible"])
                self.assertFalse(
                    ret["complete_r3_reaching_definition_at_exit_verified"])

    def test_integer_update_load_r3_base_is_write(self):
        words=make()
        for op in (33,35,41,43):
            with self.subTest(op=op):
                changed=dict(words)
                changed[m.BALL_CTOR_END-8]=(op<<26)|(0<<21)|(3<<16)|4
                o=m.analyze(changed.__getitem__)
                ret=o["bounded_exit_r3_syntactic_relationships"][0]
                self.assertEqual(
                    ret["nearest_supported_r3_definition_class"],
                    "integer_load_update_base_r3")
                self.assertFalse(
                    ret["r3_mr_from_entry_saved_register_syntactically_possible"])

    def test_mr_using_r3_as_source_does_not_overwrite_r3(self):
        words=make()
        words[m.BALL_CTOR_END-12]=mr(3,31)
        words[m.BALL_CTOR_END-8]=mr(4,3)
        ret=m.analyze(words.__getitem__)["bounded_exit_r3_syntactic_relationships"][0]
        self.assertEqual(ret["nearest_supported_r3_definition_class"],"mr_from_r31")
        self.assertTrue(ret["r3_mr_from_entry_saved_register_syntactically_possible"])

    def test_plain_stores_and_floating_stores_do_not_write_r3(self):
        words=make()
        words[m.BALL_CTOR_END-12]=mr(3,31)
        for op in (36,38,44,47,48,50,52,54):
            with self.subTest(op=op):
                changed=dict(words)
                changed[m.BALL_CTOR_END-8]=(op<<26)|(3<<21)|(4<<16)
                ret=m.analyze(changed.__getitem__)["bounded_exit_r3_syntactic_relationships"][0]
                self.assertEqual(ret["nearest_supported_r3_definition_class"],"mr_from_r31")
                self.assertTrue(ret["r3_mr_from_entry_saved_register_syntactically_possible"])

    def test_integer_immediate_subtract_and_addcarry_write_r3(self):
        words=make()
        for op in (12,13):
            with self.subTest(op=op):
                changed=dict(words)
                changed[m.BALL_CTOR_END-8]=(op<<26)|(3<<21)|(4<<16)|1
                ret=m.analyze(changed.__getitem__)["bounded_exit_r3_syntactic_relationships"][0]
                self.assertEqual(
                    ret["nearest_supported_r3_definition_class"],
                    "load_or_other_integer_writer")
                self.assertFalse(ret["r3_mr_from_entry_saved_register_syntactically_possible"])

    def test_missing_exact_base_ctor_call_refuses(self):
        words=make(); words[m.BASE_CTOR_CALL]=0x60000000
        with self.assertRaises(ValueError):m.analyze(words.__getitem__)

    def test_wrong_base_ctor_destination_refuses(self):
        words=make(); words[m.BASE_CTOR_CALL]=bl(m.BASE_CTOR_CALL,m.BASE_CTOR_TARGET+4)
        with self.assertRaises(ValueError):m.analyze(words.__getitem__)

    def test_nonlink_branch_to_base_refuses(self):
        words=make();words[m.BASE_CTOR_CALL]&=~1
        with self.assertRaises(ValueError):m.analyze(words.__getitem__)

    def test_unknown_return_r3_source_kept_unknown(self):
        words=make();words[m.BALL_CTOR_END-8]=0x60000000
        o=m.analyze(words.__getitem__)
        self.assertFalse(o["bounded_exit_r3_syntactic_relationships"][0]
                         ["r3_mr_from_entry_saved_register_syntactically_possible"])

    def test_return_uses_other_register_not_saved(self):
        words=make();words[m.BALL_CTOR_END-8]=mr(3,30)
        o=m.analyze(words.__getitem__)
        self.assertFalse(o["bounded_exit_r3_syntactic_relationships"][0]
                         ["r3_mr_from_entry_saved_register_syntactically_possible"])

    def test_additional_early_return_categorized(self):
        words=make();words[m.CLASS_TAG_PC+4]=0x4e800020
        o=m.analyze(words.__getitem__)
        self.assertEqual(o["public_constructor_return_count_within_symbol"],2)

    def test_source_class_store_category_nonproof(self):
        words=make()
        o=m.analyze(words.__getitem__)
        self.assertEqual(o["class_table_initialization_instruction_op_category"],"integer_store")
        self.assertTrue(o["class_data_word_semantics_unverified"])

    def test_unrecognized_class_store_classified_unknown(self):
        words=make();words[m.CLASS_TAG_PC]=0x60000000
        o=m.analyze(words.__getitem__)
        self.assertEqual(o["class_table_initialization_instruction_op_category"],"other_or_unknown")

    def test_invalid_source_word_refused(self):
        words=make();words[m.BALL_CTOR_ENTRY]=-1
        with self.assertRaises(ValueError):m.analyze(words.__getitem__)

    def test_no_private_values_in_sanitized_report(self):
        s=json.dumps(m.analyze(make().__getitem__))
        for raw in ("0x9000","private_heap_address","raw_ppc_word"):
            self.assertNotIn(raw,s)
        self.assertIn("fn_8029AB78",s)
        self.assertFalse(m.analyze(make().__getitem__)["training_approved"])


if __name__=="__main__":
    unittest.main()
