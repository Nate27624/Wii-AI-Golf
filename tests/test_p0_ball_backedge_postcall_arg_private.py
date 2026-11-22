"""Synthetic-only native source post-call r4 and +0x5C flag check."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m=load("ball_postcall_arg",
       ROOT/"scripts"/"p0_ball_backedge_postcall_arg_private.py")
fixture=load("ball_signed_backedge_fixture",
       ROOT/"tests"/"test_p0_ball_cc_backedge_signed_operands_private.py")


def d(op,rt,ra,imm):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&0xffff)


def mr(dest,src):
    return (31<<26)|(src<<21)|(dest<<16)|(src<<11)|(444<<1)


def bl(pc,dest,link=True):
    delta=dest-pc
    if delta%4 or not -(1<<25)<=delta<(1<<25):
        raise ValueError("synthetic PPC direct BL range")
    return (18<<26)|(delta&0x03fffffc)|int(link)


def program():
    native=fixture.source()
    native[m.BASE+m.PRELUDE_CALL]=bl(
        m.BASE+m.PRELUDE_CALL,m.BASE+0x2B20)
    native[m.BASE+m.R28_BIND]=mr(28,4)
    native[m.BASE+m.FLAG_LOAD]=d(34,0,3,92)
    native[m.BASE+0x2CB8]=mr(27,3)
    for info in m.caller.CALLERS:
        native[m.BASE+info["bind"]]=mr(31,3)
        native[m.BASE+info["arg"]]=mr(3,31)
        at=m.BASE+info["bl"]
        native[at]=bl(at,m.cfg.ENTRY)
    return native


def read(data):
    return lambda pc:data.get(pc,0x60000000)


class P0PostcallBranchTests(unittest.TestCase):
    def test_unsigned_byte_flag_is_nonzero_condition_not_float(self):
        x=m.exact_flag(read(program()))
        self.assertEqual(x["operation"],"unsigned_load_byte_lbz")
        self.assertEqual(x["source_relative_byte_offset"],"+0x05C")
        self.assertEqual(x["possible_unsigned_byte_range"],[0,255])
        self.assertEqual(x["fallthrough_condition"],"loaded_byte_is_nonzero")
        self.assertFalse(x["source_object_is_selected_live_Ball_proven"])

    def test_r28_is_postcall_volatile_r4_not_proven_entry_arg(self):
        x=m.exact_gpr_sources(read(program()))
        self.assertEqual(x["r28_bound_from_r4_source_site"],"Ball+0x2CBC")
        self.assertEqual(x["exact_original_source_call_site"],"Ball+0x2CB0")
        self.assertTrue(x["r4_is_volatile_across_linked_call_under_PPC_ABI"])
        self.assertFalse(x["r28_equals_original_function_entry_r4_proven"])
        self.assertFalse(x["callee_effect_on_r4_and_returned_state_proven"])

    def test_caller_li_value_does_not_prove_r28_negative(self):
        p=program()
        p[m.BASE+0x2B84]=d(14,4,0,-1)
        p[m.BASE+0x2C74]=d(14,4,0,0)
        x=m.inspect(read(p))
        callers=x["original_two_callers_r4_source_context"]
        self.assertEqual(callers[0][
            "closest_bounded_syntactic_r4_definition"][
            "li_signed_immediate_if_literal"],-1)
        self.assertEqual(callers[1][
            "closest_bounded_syntactic_r4_definition"][
            "li_signed_immediate_if_literal"],0)
        self.assertFalse(callers[0][
            "r4_at_callee_after_intervening_prelude_call_proven"])
        self.assertFalse(x["native_guest_backedge_taken_proven"])

    def test_looking_up_r3_flag_receiver_keeps_uncertain_owner(self):
        x=m.byte_base_path(read(program()))
        self.assertFalse(x["complete_r3_object_identity_qualified"])
        self.assertIn("Ball+0x2CB0",x[
            "source_BL_calls_that_can_clobber_r3"])
        self.assertFalse(x["original_guest_flag_value_observed"])

    def test_nonbyte_load_refuses(self):
        p=program()
        p[m.BASE+m.FLAG_LOAD]=d(32,0,3,92)
        with self.assertRaises(ValueError):
            m.exact_flag(read(p))

    def test_flag_wrong_base_register_refuses(self):
        p=program()
        p[m.BASE+m.FLAG_LOAD]=d(34,0,27,92)
        with self.assertRaises(ValueError):
            m.exact_flag(read(p))

    def test_wrong_r28_source_register_refuses(self):
        p=program()
        p[m.BASE+m.R28_BIND]=mr(28,3)
        with self.assertRaises(ValueError):
            m.exact_gpr_sources(read(p))

    def test_unlinked_callee_call_refuses(self):
        p=program()
        p[m.BASE+m.PRELUDE_CALL]=bl(
            m.BASE+m.PRELUDE_CALL,m.BASE+0x2B20,link=False)
        with self.assertRaises(ValueError):
            m.exact_gpr_sources(read(p))

    def test_recognized_r4_reassignment_after_call_does_not_prove_value(self):
        p=program()
        p[m.BASE+0x2CB4]=d(14,4,0,-4)
        x=m.exact_gpr_sources(read(p))
        self.assertEqual(len(x["recognized_intervening_r4_assignments"]),1)
        self.assertFalse(x["r28_runtime_signed_value_proven"])

    def test_another_control_transfer_after_prelude_call_refuses(self):
        p=program()
        p[m.BASE+0x2CB4]=bl(
            m.BASE+0x2CB4,m.BASE+0x2BE0)
        with self.assertRaises(ValueError):
            m.exact_gpr_sources(read(p))

    def test_exact_two_caller_bl_gate_abstains_if_wrong(self):
        p=program()
        pc=m.BASE+0x2B8C
        p[pc]=bl(pc,m.cfg.ENTRY+4)
        with self.assertRaises(ValueError):
            m.caller_r4(read(p))

    def test_full_source_report_no_collision_or_training_promotion(self):
        report=m.inspect(read(program()))
        encoded=json.dumps(report,sort_keys=True)
        self.assertTrue(report["static_may_reachability_of_CC_copy_proven"])
        self.assertFalse(report["source_input_r4_preserved_across_prelude_BL_proven"])
        self.assertFalse(report["wood_vs_foliage_collision_branch_proven"])
        self.assertFalse(report["training_approved"])
        self.assertNotIn("0x90008000",encoded)
        self.assertNotIn("original_ppc_word",encoded)


if __name__=="__main__":
    unittest.main()
