"""Synthetic-only original KCL primitive halfword → Ball query output tests."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/"scripts"
TESTS=ROOT/"tests"
sys.path.insert(0,str(SCRIPTS))


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m=load("prism_origin",SCRIPTS/"p0_ball_kcol_prism_type_origin_private.py")
source=load("material_fixture",TESTS/"test_p0_ball_kcol_material_branch_private.py")


def fixture():
    words,read=source.fixture()
    for unit,off,opcode,rt,ra,disp in m.EXPECTED_DFORM:
        lo=m.units.UNITS[unit][0]
        words[lo+off]=(opcode<<26)|(rt<<21)|(ra<<16)|(disp&0xFFFF)
    return words,read


class KCLPrismTypeOriginSyntheticTests(unittest.TestCase):
    def test_original_exact_chain_and_bounded_windows(self):
        words,read=fixture()
        r=m.inspect(read)
        self.assertTrue(r["original_source_gates_passed"])
        self.assertTrue(r["main_query_classification_from_prism_offset_0x0E"])
        self.assertTrue(r["narrowphase_classification_from_prism_offset_0x0E"])
        self.assertTrue(r["ball_0xAC_B0_B4_structural_state_copy_verified"])
        self.assertEqual(r["native_source_words"],322)
        self.assertEqual(len(r["windows"]),6)

    def test_no_tree_or_velocity_promotions(self):
        words,read=fixture()
        r=m.inspect(read)
        for key in (
            "ball_0B60_wrapped_query_resource_owner_proven",
            "classification_13_tree_semantics_proven",
            "ball_velocity_semantics_proven",
            "native_tree_hitbox_proven","training_approved"
        ):
            self.assertFalse(r[key])

    def test_detail_only_local_console_representation(self):
        words,read=fixture()
        a=m.inspect(read)
        b=m.inspect(read,True)
        self.assertFalse(any("native_code_local_only" in x for x in a["windows"]))
        self.assertTrue(all(len(x["native_code_local_only"])==x["instruction_count"]
                            for x in b["windows"]))

    def test_prism_type_offset_change_abstains(self):
        words,read=fixture()
        pc=m.units.UNITS["GolfKCol"][0]+0x0118
        words[pc]=(40<<26)|(0<<21)|(3<<16)|0x000C
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_result_outbound_pointer_change_abstains(self):
        words,read=fixture()
        pc=m.units.UNITS["GolfKCol"][0]+0x2688
        words[pc]=(44<<26)|(0<<21)|(21<<16)
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_ball_copy_register_change_abstains(self):
        words,read=fixture()
        pc=m.units.UNITS["Ball"][0]+0x3590
        words[pc]=(52<<26)|(4<<21)|(30<<16)|176
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_original_material_gate_cannot_be_bypassed(self):
        words,read=fixture()
        words[m.units.UNITS["Ball"][0]+0x0B84]=0
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_windows_limited_and_source_relative(self):
        words,read=fixture()
        original=m.MAX_NATIVE_WORDS
        try:
            m.MAX_NATIVE_WORDS=1
            with self.assertRaises(ValueError):
                m.inspect(read)
        finally:
            m.MAX_NATIVE_WORDS=original


if __name__=="__main__":
    unittest.main()
