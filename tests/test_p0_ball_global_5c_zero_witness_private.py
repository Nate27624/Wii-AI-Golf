"""Synthetic-only native PPC r30 zero and global-r26 byte-store witness."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "p0_global_byte_clear_witness",
    ROOT/"scripts"/"p0_ball_global_5c_zero_witness_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def d(op,rt,ra,imm):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&65535)


def xform(xo,rt,ra,rb=0):
    return (31<<26)|(rt<<21)|(ra<<16)|(rb<<11)|(xo<<1)


def branch(pc,target):
    delta=target-pc
    if delta%4:
        raise ValueError("Unaligned synthetic branch")
    return (18<<26)|(delta&0x03fffffc)


def program():
    return {
        m.R30_CONST:d(14,30,0,0),
        m.GLOBAL_LOAD:d(32,26,13,m.prior.source.GLOBAL_SLOT),
        m.BYTE_CLEAR:d(38,30,26,0x5C),
        m.BALL+0x2D44:xform(824,6,7,3),
        m.BALL+0x2D48:xform(202,8,9),
    }


def read(words):
    return lambda pc:words.get(pc,0x60000000)


class OriginalFlagZeroWitnessTests(unittest.TestCase):
    def test_srawi_writes_rA_not_rD(self):
        x=m.xform(xform(824,26,9,2),824)
        self.assertEqual(x["mnemonic"],"srawi")
        self.assertEqual(x["source_register"],26)
        self.assertEqual(x["destination_register"],9)
        self.assertEqual(m.gpr_writes_qualified(xform(824,26,9,2)),
                         (True,{9}))

    def test_addze_writes_rD_not_rA(self):
        x=m.xform(xform(202,12,26),202)
        self.assertEqual(x["mnemonic"],"addze")
        self.assertEqual(x["source_register"],26)
        self.assertEqual(x["destination_register"],12)
        self.assertEqual(m.gpr_writes_qualified(xform(202,12,26)),(True,{12}))

    def test_literal_zero_and_global_pointer_source_verified(self):
        p=m.exact_source(read(program()))
        self.assertEqual(p["original_r30_literal_zero_source"],"Ball+0x2CC4")
        self.assertEqual(p["original_global_pointer_r26_load_source"],"Ball+0x2D30")
        self.assertEqual(p["original_zero_byte_store_candidate_source"],"Ball+0x2D8C")
        self.assertFalse(p["native_r30_zero_on_every_runtime_path_proven"])

    def test_linear_possible_path_preserves_r26_r30(self):
        p=m.witness(read(program()))
        self.assertTrue(p["static_source_may_reach_byte_store"])
        self.assertTrue(p["all_three_source_anchors_on_one_witness"])
        self.assertTrue(p["protected_GPR26_GPR30_preservation_source_qualified"])
        self.assertTrue(p["native_byte_value_is_zero_if_witness_executes_without_clobber"])
        self.assertFalse(p["native_guest_byte_write_executed_proven"])
        self.assertFalse(p["conditional_branch_register_values_observed"])

    def test_srawi_destination_r30_blocks_source_proof(self):
        p=program()
        p[m.BALL+0x2D44]=xform(824,6,30,2)
        report=m.witness(read(p))
        self.assertFalse(report["protected_GPR26_GPR30_preservation_source_qualified"])
        self.assertTrue(report["protected_r26_r30_source_effect_uncertainties_or_clobbers"])

    def test_addze_destination_r26_blocks_global_receiver_proof(self):
        p=program()
        p[m.BALL+0x2D48]=xform(202,26,6)
        report=m.witness(read(p))
        self.assertFalse(report["protected_GPR26_GPR30_preservation_source_qualified"])
        self.assertFalse(report["receiver_is_same_global_slot_value_if_witness_executes_without_clobber"])

    def test_unqualified_source_op_abstains_from_proof(self):
        p=program()
        p[m.BALL+0x2D48]=(4<<26)
        report=m.witness(read(p))
        self.assertFalse(report["protected_GPR26_GPR30_preservation_source_qualified"])

    def test_branch_bypass_to_outside_store_window_does_not_prove_execution(self):
        p=program()
        at=m.BALL+0x2D50
        p[at]=branch(at,m.BALL+0x2DC0)
        report=m.witness(read(p))
        self.assertFalse(report["static_source_may_reach_byte_store"])
        self.assertFalse(report["protected_GPR26_GPR30_preservation_source_qualified"])

    def test_nonzero_li_r30_anchor_abstains(self):
        p=program()
        p[m.R30_CONST]=d(14,30,0,1)
        with self.assertRaises(ValueError):
            m.exact_source(read(p))

    def test_wrong_byte_store_base_refuses(self):
        p=program()
        p[m.BYTE_CLEAR]=d(38,30,27,0x5C)
        with self.assertRaises(ValueError):
            m.exact_source(read(p))

    def test_source_report_never_promotes_physics_or_training(self):
        q=m.inspect(read(program()))
        self.assertFalse(q["selected_live_ball_identity_proven"])
        self.assertFalse(q["global_flag_at_guest_collision_time_known"])
        self.assertFalse(q["native_tree_contact_wood_vs_foliage_material_verified"])
        self.assertFalse(q["training_approved"])
        output=json.dumps(q)
        self.assertNotIn("private_archive",output)
        self.assertNotIn("original_ppc_word",output)
        self.assertNotIn("0x90008000",output)


if __name__=="__main__":
    unittest.main()
