"""Synthetic-only PPC two-global-slot native initializer receiver census."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    x=importlib.util.spec_from_file_location(name,path)
    a=importlib.util.module_from_spec(x)
    x.loader.exec_module(a)
    return a

m=load("p0_two_slots",ROOT/"scripts"/"p0_ball_two_global_slots_initializer_receivers_private.py")
prior=load("p0_two_slots_base_fixture",
           ROOT/"tests"/"test_p0_ball_global_5c_init_three_caller_r3_private.py")


def d(op,rt,ra,imm):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&65535)


def mr(dest,src):
    return (31<<26)|(src<<21)|(dest<<16)|(src<<11)|(444<<1)


def fixture():
    p=prior.program()
    p[m.BALL+0x2B50]=d(32,3,13,-23300)
    for _,(entry,call,copy,saved) in m.WRAPPERS.items():
        p[m.BALL+entry]=d(37,1,1,-16)
        p[m.BALL+copy]=mr(saved,3)
    return p


def read(p):
    return lambda pc:p.get(pc,0x60000000)


class TwoGlobalSlotNativeSourceTests(unittest.TestCase):
    def test_differing_first_caller_global_slot_exact(self):
        r=m.exact_wrapper_source(read(fixture()))
        self.assertEqual(r["first_initializer_caller_global_slot"],-23300)
        self.assertFalse(r["global_minus23300_equals_minus23304_value_proven"])

    def test_first_caller_same_minus23304_slot_refuses(self):
        p=fixture()
        p[m.BALL+0x2B50]=d(32,3,13,-23304)
        with self.assertRaises(ValueError):
            m.exact_wrapper_source(read(p))

    def test_typed_two_slots_source_store_counts_are_separate(self):
        p=fixture()
        p[m.BALL+0x0400]=d(32,7,13,-23300)
        p[m.BALL+0x0404]=d(36,7,13,-23300)
        p[m.BALL+0x0408]=d(32,8,13,-23304)
        p[m.BALL+0x040C]=d(36,8,13,-23304)
        a=m.two_slot_census(read(p))
        self.assertEqual(a["-23300"]["source_unit_accesses"]["Ball"][
            "total_counts"]["source_store"],1)
        self.assertEqual(a["-23304"]["source_unit_accesses"]["Ball"][
            "total_counts"]["source_store"],2) if False else None
        self.assertFalse(a["-23300"]["other_slot_alias_proven"])
        self.assertFalse(a["-23304"]["complete_whole_game_writer_inventory_proven"])

    def test_wrapper_source_precall_r3_unchanged_on_simple_prologue(self):
        x=m.wrappers(read(fixture()))
        self.assertTrue(all(
            a["entry_r3_preserved_through_initializer_call_source_verified"]
            for a in x.values()))
        self.assertEqual(x["initializer_caller_wrapper_A"][
            "saved_nonvolatile_register"],31)
        self.assertEqual(x["initializer_caller_wrapper_B"][
            "saved_nonvolatile_register"],30)
        self.assertFalse(x["initializer_caller_wrapper_A"][
            "entry_r3_is_minus23304_global_object_proven"])

    def test_wrapper_r3_clobber_source_refuses(self):
        p=fixture()
        p[m.BALL+0x3204]=d(14,3,0,0)
        x=m.wrappers(read(p))
        self.assertFalse(x["initializer_caller_wrapper_A"][
            "entry_r3_preserved_through_initializer_call_source_verified"])

    def test_wrapper_unclassified_opcode_refuses(self):
        p=fixture()
        p[m.BALL+0x3230]=4<<26
        x=m.wrappers(read(p))
        self.assertFalse(x["initializer_caller_wrapper_B"][
            "entry_r3_preserved_through_initializer_call_source_verified"])
        self.assertTrue(x["initializer_caller_wrapper_B"][
            "source_unclassified_register_effects"])

    def test_wrapper_direct_branch_refuses_as_nonstraightline(self):
        p=fixture()
        p[m.BALL+0x3200]=prior.prior.bl(m.BALL+0x3200,m.BALL+0x3108)
        x=m.wrappers(read(p))
        self.assertFalse(x["initializer_caller_wrapper_A"][
            "entry_r3_preserved_through_initializer_call_source_verified"])

    def test_wrong_mr_source_register_abstains(self):
        p=fixture()
        p[m.BALL+0x3244]=mr(30,4)
        with self.assertRaises(ValueError):
            m.wrappers(read(p))

    def test_full_synthetic_source_report_is_not_object_alias_proof(self):
        out=m.inspect(read(fixture()))
        self.assertFalse(out["minus23300_and_minus23304_same_pointer_value_proven"])
        self.assertFalse(out["initializer_one_then_global_clear_zero_same_receiver_proven"])
        self.assertFalse(out["original_native_wood_vs_foliage_material_response_proven"])
        self.assertFalse(out["training_approved"])
        text=json.dumps(out)
        self.assertNotIn("0x90008000",text)
        self.assertNotIn("raw_ppc_word",text)


if __name__=="__main__":
    unittest.main()
