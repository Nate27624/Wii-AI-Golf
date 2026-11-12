"""Synthetic-only source audit tests for +0x5C initialization and r26."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "p0_native_5c_initializer",
    ROOT/"scripts"/"p0_ball_global_5c_initializer_r26_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def d(op,rt,ra,disp):
    return (op<<26)|(rt<<21)|(ra<<16)|(disp&0xffff)


def mr(dst,src):
    return (31<<26)|(src<<21)|(dst<<16)|(src<<11)|(444<<1)


def branch(pc,dest,link=False,conditional=False):
    delta=dest-pc
    if delta%4:
        raise ValueError("Unaligned synthetic PPC transfer")
    if conditional:
        return (16<<26)|(12<<21)|(2<<16)|(delta&0xfffc)
    return (18<<26)|(delta&0x3fffffc)|int(link)


def program():
    code={}
    for _,(off,op,rt,ra,disp) in m.old.SOURCE_ANCHORS.items():
        code[m.BALL+off]=d(op,rt,ra,disp)
    for off,reg in m.old.DIRECT_LOADS:
        code[m.BALL+off]=d(32,reg,13,m.source.GLOBAL_SLOT)
    for off,op,rt,ra,disp in m.INIT_FIELDS:
        code[m.BALL+off]=mr(rt,ra) if op==31 else d(op,rt,ra,disp)
    code[m.BALL+m.R26_GLOBAL_LOAD]=d(32,26,13,m.source.GLOBAL_SLOT)
    code[m.BALL+0x3068]=d(14,3,0,428)
    code[m.BALL+0x307C]=d(14,4,0,0)
    code[m.BALL+0x3078]=branch(m.BALL+0x3078,m.BALL+0x3084,conditional=True)
    code[m.BALL+0x3080]=branch(m.BALL+0x3080,m.BALL+m.LOCAL_CALL_TARGET,link=True)
    return code


def read(code):
    return lambda pc:code.get(pc,0x60000000)


class P0GlobalInitializerTests(unittest.TestCase):
    def test_exact_source_initializer_writes_literal_one_to_5c(self):
        result=m.init(read(program()))
        self.assertTrue(result["initializer_stores_literal_one_to_receiver_plus_0x5C_if_executed"])
        self.assertTrue(result["initializer_stores_literal_zero_to_receiver_plus_0x5D_if_executed"])
        self.assertFalse(result["initializer_receiver_is_global_pointer_proven"])
        self.assertFalse(result["native_guest_executed_initializer_proven"])

    def test_initializer_wrong_literal_one_abstains(self):
        code=program()
        code[m.BALL+0x3124]=d(14,5,0,0)
        with self.assertRaises(ValueError):
            m.init(read(code))

    def test_initializer_wrong_5c_receiver_abstains(self):
        code=program()
        code[m.BALL+0x314C]=d(38,5,27,0x5c)
        with self.assertRaises(ValueError):
            m.init(read(code))

    def test_initializer_intervening_r5_write_blocks_literal_value(self):
        code=program()
        code[m.BALL+0x313C]=d(14,5,0,0)
        result=m.init(read(code))
        self.assertFalse(result["bounded_intervening_register_checks"][
            "r5"]["literal_or_receiver_preserved_by_known_syntax"])
        self.assertFalse(result["initializer_stores_literal_one_to_receiver_plus_0x5C_if_executed"])

    def test_global_constructor_exact_original_local_call_and_store(self):
        result=m.global_constructor(read(program()))
        self.assertEqual(result["source_local_callee_ball_relative_target"],"Ball+0x3BA0")
        self.assertEqual(result["original_source_size_immediate"],428)
        self.assertFalse(result["callee_return_GPR3_is_allocated_constructed_ball_proven"])

    def test_global_constructor_wrong_local_target_abstains(self):
        code=program()
        code[m.BALL+0x3080]=branch(m.BALL+0x3080,m.BALL+0x3BA4,link=True)
        with self.assertRaises(ValueError):
            m.global_constructor(read(code))

    def test_r26_global_slot_load_before_byte_store_remains_only_candidate(self):
        code=program()
        result=m.global_r26(read(code))
        self.assertEqual(result["native_global_load_source"],"Ball+0x2D30")
        self.assertEqual(result["native_byte_writer_source"],"Ball+0x2D8C")
        self.assertFalse(result["same_global_pointer_value_along_source_path_proven"])

    def test_r26_source_redefinition_reported_without_alias_promotion(self):
        code=program()
        code[m.BALL+0x2D50]=d(14,26,26,4)
        result=m.global_r26(read(code))
        self.assertTrue(result["recognized_r26_redefinitions_between_source_and_store"])
        self.assertFalse(result["same_global_pointer_value_along_source_path_proven"])

    def test_r26_branch_does_not_prove_store_executed(self):
        code=program()
        pc=m.BALL+0x2D70
        code[pc]=branch(pc,m.BALL+0x2DC0)
        result=m.global_r26(read(code))
        self.assertIn("Ball+0x2D70",[x["source_site"] for x in
                                     result["source_branch_or_call_sites_between_source_and_store"]])
        self.assertFalse(result["runtime_byte_value_written_proven"])

    def test_complete_source_syntax_report_not_wood_material_or_training(self):
        result=m.inspect(read(program()))
        self.assertTrue(result["source_original_five_native_census_anchors_passed"])
        self.assertFalse(result["native_tree_collision_or_wood_vs_foliage_branch_proven"])
        self.assertFalse(result["global_object_is_selected_live_Ball_proven"])
        self.assertFalse(result["training_approved"])
        output=json.dumps(result)
        self.assertNotIn("private_archive",output)
        self.assertNotIn("raw_native_ppc_word",output)


if __name__=="__main__":
    unittest.main()
