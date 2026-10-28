"""Fabricated regression for source-global GPR forwarding before D-form access.

This is a review-only extension of #268's bounded six-word PPC source helper;
never loads Dolphin, native ROM/RAM, pointers, screenshots, or uploaded files.
"""
from __future__ import annotations
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import review_p0_global_slot_load_consumers as m

P=m.UNIT_BASE+0x2B64
D=-100
NOP=0x60000000


def d(op,rt,ra,imm=0):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&65535)


def mr(dst,src):
    return (31<<26)|(src<<21)|(dst<<16)|(src<<11)|(444<<1)


def check(body, source_reg=5):
    words={P:d(32,source_reg,13,D)}
    words.update(body)
    return m.first_consumer(lambda pc:words.get(pc,NOP),P,D)


class ForwardedR3Review(unittest.TestCase):
    def test_field_load_via_exact_mr_r3_from_global_reg(self):
        out=check({P+4:mr(3,5),P+8:d(32,4,3,0x4C)})
        self.assertEqual(out["first_bounded_consumer_class"],
                         "field_load_through_forwarded_r3_pointer")
        self.assertEqual(out["source_syntactic_field_displacement"],0x4C)
        self.assertFalse(out["all_path_pointer_dataflow_verified"])

    def test_field_store_via_forwarded_r3(self):
        out=check({P+4:mr(3,5),P+8:d(36,4,3,0x30)})
        self.assertEqual(out["first_bounded_consumer_class"],
                         "field_store_through_forwarded_r3_pointer")

    def test_source_register_r0_copy_is_valid_r3_pointer(self):
        out=check({P+4:mr(3,0),P+8:d(32,4,3,0x4C)},source_reg=0)
        self.assertEqual(out["first_bounded_consumer_class"],
                         "field_load_through_forwarded_r3_pointer")

    def test_base_r0_is_literal_zero_not_pointer_even_after_forward(self):
        out=check({P+4:mr(3,5),P+8:d(32,4,0,0x4C)})
        self.assertNotEqual(out["first_bounded_consumer_class"],
                            "field_load_through_forwarded_r3_pointer")

    def test_no_copy_to_r3_does_not_generate_forwarded_use(self):
        out=check({P+4:d(32,4,3,0x4C)})
        self.assertNotEqual(out["first_bounded_consumer_class"],
                            "field_load_through_forwarded_r3_pointer")

    def test_prior_control_transfer_must_abstain(self):
        out=check({P+4:mr(3,5),P+8:16<<26,P+12:d(32,4,3,0x4C)})
        self.assertEqual(out["first_bounded_consumer_class"],
                         "branch_or_call_before_proven_consumer")

    def test_r3_clobber_after_forward_stops_before_field(self):
        out=check({P+4:mr(3,5),P+8:d(14,3,3,4),P+12:d(32,4,3,0x4C)})
        self.assertEqual(out["first_bounded_consumer_class"],
                         "possible_register_clobber_before_proven_consumer")

    def test_source_reg_clobber_after_copy_still_conservatively_abstains(self):
        out=check({P+4:mr(3,5),P+8:d(32,5,4,0),
                   P+12:d(32,4,3,0x4C)})
        self.assertEqual(out["first_bounded_consumer_class"],
                         "possible_register_clobber_before_proven_consumer")

    def test_zero_compare_on_forwarded_pointer(self):
        out=check({P+4:mr(3,5),P+8:d(11,0,3,0)})
        self.assertEqual(out["first_bounded_consumer_class"],
                         "zero_compare_on_forwarded_r3_pointer")

    def test_large_immediate_redacted(self):
        out=check({P+4:mr(3,5),P+8:d(32,4,3,0x6B4)})
        self.assertEqual(out["first_bounded_consumer_class"],
                         "field_load_through_forwarded_r3_pointer")
        self.assertIsNone(out["source_syntactic_field_displacement"])

    def test_direct_bl_still_classifies_argument_not_function_identity(self):
        out=check({P+4:mr(3,5),P+8:(18<<26)|1})
        self.assertEqual(out["first_bounded_consumer_class"],
                         "direct_bl_after_r3_pointer_candidate")
        self.assertFalse(out["call_target_or_receiver_type_verified"])

    def test_sanitized_fields_remain_no_runtime_or_training(self):
        out=check({P+4:mr(3,5),P+8:d(32,4,3,0x4C)})
        self.assertFalse(out["rendered_active_ball_verified"])
        text=json.dumps(out)
        for secret in ("PRIVATE_HEAP","0x9000","MEM1.raw","native_ram"):
            self.assertNotIn(secret,text)


if __name__=="__main__":
    unittest.main()
