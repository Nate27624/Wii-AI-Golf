"""Synthetic-only source PPC CR0 EQ/LT register-lineage tests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
file=ROOT/"scripts"/"p0_ball_cc_backedge_signed_operands_private.py"
spec=importlib.util.spec_from_file_location("p0_signed_backedge",file)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def d(op,rt,ra,offset):
    return (op<<26)|(rt<<21)|(ra<<16)|(offset&0xffff)


def b(pc,to):
    delta=to-pc
    if delta%4 or not -(1<<25)<=delta<(1<<25):
        raise ValueError("Synthetic PPC direct branch invalid")
    return (18<<26)|(delta&0x03fffffc)


def bc(pc,to,bo,bi):
    delta=to-pc
    if delta%4 or not -(1<<15)<=delta<(1<<15):
        raise ValueError("Synthetic PPC bc out of range")
    return (16<<26)|(bo<<21)|(bi<<16)|(delta&0xfffc)


def source():
    # This program permits the published-entry static witness and
    # places simple synthetic li r0,1 / li r28,-1 before the two tests.
    return {
        m.cfg.BRANCH_SKIP:b(m.cfg.BRANCH_SKIP,m.cfg.BRANCH_TARGET),
        m.BASE+0x2FB8:d(14,0,0,1),
        m.BASE+0x2FBC:d(14,28,0,-1),
        m.BASE+m.CMP_R0:d(11,0,0,0),
        m.BASE+m.BEQ:bc(m.BASE+m.BEQ,m.BASE+0x2FDC,12,2),
        m.BASE+m.CMP_R28:d(11,0,28,0),
        m.BASE+m.BLT:bc(m.BASE+m.BLT,m.BASE+m.BACKEDGE_TARGET,12,0),
    }


def reader(mapping):
    return lambda pc:mapping.get(pc,0x60000000)


class BackedgeOperandLineageTests(unittest.TestCase):
    def test_exact_signed_cmpwi_uses_CR0_EQ_for_r0_and_LT_for_r28(self):
        obj=m.inspect(reader(source()))
        self.assertEqual([x["source_operand_register"] for x in
                          obj["original_adjacent_cmpwi_source"]],[0,28])
        self.assertEqual([x["CR_bit_index"] for x in
                          obj["original_exact_branch_sites"]],[2,0])
        self.assertEqual(obj["CC_writer_backedge_necessary_source_predicates"],[
            "r0_not_equal_to_0_for_Ball+0x2FC4_fallthrough",
            "signed_r28_less_than_0_for_Ball+0x2FCC_taken"])
        self.assertFalse(obj["same_static_witness_constraints_formally_contradictory"])
        self.assertFalse(obj["branch_witness_path_condition_feasible_at_runtime_proven"])

    def test_witness_contains_both_exact_control_choices(self):
        p=source()
        w=m.witness(reader(p))
        i=w.index(m.BASE+m.BEQ)
        j=w.index(m.BASE+m.BLT)
        self.assertEqual(w[i+1],m.BASE+m.CMP_R28)
        self.assertEqual(w[j+1],m.BASE+m.BACKEDGE_TARGET)

    def test_nearest_synthetic_writers_for_each_compare(self):
        obj=m.inspect(reader(source()))
        a=obj["source_witness_operand_reaching_writer_syntax"]
        self.assertEqual(a["r0"]["nearest_recognized_writer_on_static_witness"][
            "known_immediate_constant_if_li"],1)
        self.assertEqual(a["r28"]["nearest_recognized_writer_on_static_witness"][
            "known_immediate_constant_if_li"],-1)
        self.assertFalse(a["r28"]["register_runtime_value_proven"])

    def test_live_original_values_never_inferred_from_synthetic_li(self):
        obj=m.inspect(reader(source()))
        self.assertFalse(obj["guest_CR_values_or_register_values_observed"])
        self.assertFalse(obj["selected_Ball_or_r13_global_object_identity_proven"])
        self.assertFalse(obj["native_velocity_or_restitution_verified"])
        self.assertFalse(obj["wood_vs_foliage_collision_handler_verified"])
        self.assertFalse(obj["training_approved"])

    def test_cmpwi_unsigned_wrong_opcode_abstains(self):
        p=source()
        p[m.BASE+m.CMP_R28]=d(10,0,28,0)
        with self.assertRaises(ValueError):
            m.inspect(reader(p))

    def test_cmpwi_wrong_reg_abstains(self):
        p=source()
        p[m.BASE+m.CMP_R0]=d(11,0,1,0)
        with self.assertRaises(ValueError):
            m.cmpwi(reader(p),m.CMP_R0,0)

    def test_cmpwi_nonzero_immediate_abstains(self):
        p=source()
        p[m.BASE+m.CMP_R28]=d(11,0,28,1)
        with self.assertRaises(ValueError):
            m.inspect(reader(p))

    def test_wrong_branch_bit_eq_instead_of_lt_abstains(self):
        p=source()
        p[m.BASE+m.BLT]=bc(m.BASE+m.BLT,m.BASE+m.BACKEDGE_TARGET,12,2)
        with self.assertRaises(ValueError):
            m.inspect(reader(p))

    def test_wrong_backward_target_abstains(self):
        p=source()
        p[m.BASE+m.BLT]=bc(m.BASE+m.BLT,m.BASE+0x2CD4,12,0)
        with self.assertRaises(ValueError):
            m.inspect(reader(p))

    def test_wrong_forward_branch_bit_abstains(self):
        p=source()
        p[m.BASE+m.BEQ]=bc(m.BASE+m.BEQ,m.BASE+0x2FDC,12,0)
        with self.assertRaises(ValueError):
            m.inspect(reader(p))

    def test_unconditional_skip_that_never_reaches_backedge_refuses(self):
        p=source()
        p[m.cfg.BRANCH_TARGET]=b(m.cfg.BRANCH_TARGET,m.BASE+0x2FD8)
        with self.assertRaises(ValueError):
            m.witness(reader(p))

    def test_signed_r28_minus_one_bitpattern_does_not_get_exposed_as_native_mem(self):
        obj=m.inspect(reader(source()))
        encoded=json.dumps(obj,sort_keys=True)
        self.assertNotIn("0x9000",encoded)
        self.assertNotIn("original_PPC_instruction_word",encoded)
        self.assertNotIn("private_archive",encoded)
        self.assertFalse(obj["training_approved"])


if __name__=="__main__":
    unittest.main()
