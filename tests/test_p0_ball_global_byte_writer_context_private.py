"""Synthetic-only original Ball global slot and byte writer receiver context tests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "p0_global_writer_context",
    ROOT/"scripts"/"p0_ball_global_byte_writer_context_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def d(op,rt,ra,disp):
    return (op<<26)|(rt<<21)|(ra<<16)|(disp&0xFFFF)


def b(pc,dest):
    diff=dest-pc
    if diff%4 or diff<-(1<<25) or diff>=(1<<25):
        raise ValueError("Invalid synthetic branch")
    return (18<<26)|(diff&0x03FFFFFC)


def data():
    out={}
    for name,(off,op,rt,ra,disp) in m.SOURCE_ANCHORS.items():
        out[m.BALL+off]=d(op,rt,ra,disp)
    for off,reg in m.DIRECT_LOADS:
        out[m.BALL+off]=d(32,reg,13,m.source.GLOBAL_SLOT)
    return out


def read(p):
    return lambda pc:p.get(pc,0x60000000)


class BallGlobalWriterContextTests(unittest.TestCase):
    def test_original_byte_and_global_slot_sites_are_source_gated(self):
        out=m.verify_anchors(read(data()))
        self.assertEqual(len(out),5)
        self.assertEqual(out[0]["original_public_site"],"Ball+0x3084")
        self.assertEqual(out[1]["original_public_site"],"Ball+0x2D8C")
        self.assertEqual(out[2]["original_public_site"],"Ball+0x314C")
        self.assertTrue(all(not e["receiver_is_same_global_object_proven"]
                            for e in out))

    def test_original_slot_store_wrong_source_reg_refuses(self):
        p=data()
        p[m.BALL+0x3084]=d(36,4,13,m.source.GLOBAL_SLOT)
        with self.assertRaises(ValueError):
            m.verify_anchors(read(p))

    def test_original_byte_writer_wrong_displacement_refuses(self):
        p=data()
        p[m.BALL+0x314C]=d(38,5,3,0x58)
        with self.assertRaises(ValueError):
            m.verify_anchors(read(p))

    def test_original_second_byte_read_must_follow_global_load(self):
        p=data()
        p[m.BALL+0x2FB8]=d(32,3,13,m.source.GLOBAL_SLOT+4)
        with self.assertRaises(ValueError):
            m.verify_anchors(read(p))

    def test_source_window_includes_anchor_with_safe_lexical_syntax(self):
        q=m.context(read(data()),0x3084)
        pcs=[v["source_site"] for v in q["source_window_instructions"]]
        self.assertIn("Ball+0x3084",pcs)
        x=[v for v in q["source_window_instructions"]
           if v["source_site"]=="Ball+0x3084"][0]
        self.assertEqual((x["operation"],x["base_register"],x[
            "source_signed_displacement"]),("stw",13,-23304))
        self.assertFalse(q["lexical_context_implies_single_function_or_taken_branch"])

    def test_nearest_register_definition_is_syntax_not_alias_proof(self):
        p=data()
        p[m.BALL+0x3140]=d(32,3,13,m.source.GLOBAL_SLOT)
        q=m.prior_defs(read(p),0x314C,3)
        defs=q["nearest_bounded_syntactic_definitions"]
        self.assertEqual(defs[0]["possible_definition_source_site"],"Ball+0x3140")
        self.assertEqual(defs[0]["recognized_definition_class"],"lwz")
        self.assertFalse(defs[0]["definition_is_reaching_on_actual_CFG_path_proven"])
        self.assertFalse(q["global_pointer_alias_at_byte_write_proven"])

    def test_prior_unconditional_branch_exposes_unproven_path_gap(self):
        p=data()
        p[m.BALL+0x3148]=b(m.BALL+0x3148,m.BALL+0x3158)
        p[m.BALL+0x3140]=d(32,3,13,m.source.GLOBAL_SLOT)
        q=m.prior_defs(read(p),0x314C,3)
        self.assertIn("Ball+0x3148",q["bounded_previous_control_transfer_sites"])
        self.assertGreater(q["nearest_bounded_syntactic_definitions"][0][
            "branch_barriers_between_definition_and_access"],0)

    def test_typed_branch_reports_only_bounded_public_ball_sites(self):
        pc=m.BALL+0x3040
        ins=m.typed_instruction(pc,b(pc,m.BALL+0x3084))
        self.assertEqual(ins["operation"],"unconditional_b")
        self.assertEqual(ins["target_public_Ball_relative_if_bounded"],
                         "Ball+0x3084")

    def test_exact_original_anchor_report_not_training_or_collision(self):
        x=m.inspect(read(data()))
        self.assertTrue(x["r13_global_slot_has_exact_direct_native_writer_in_scanned_units"])
        self.assertFalse(x["byte_stores_proven_same_global_receiver"])
        self.assertFalse(x["global_pointer_writer_proves_selected_live_Ball_identity"])
        self.assertFalse(x["native_collision_contact_or_material_branch_proven"])
        self.assertFalse(x["training_approved"])
        s=json.dumps(x)
        self.assertNotIn("0x90008000",s)
        self.assertNotIn("original_native_ppc_word",s)
        self.assertNotIn("private_ROM_bytes",s)

    def test_unknown_opcode_is_categorized_without_exposing_word(self):
        pc=m.BALL+0x0200
        v=m.typed_instruction(pc,0xFFFFFFFF)
        self.assertEqual(v["operation"],"unclassified_source_opcode")
        self.assertNotIn("word",v)
        self.assertNotIn("raw",v)


if __name__=="__main__":
    unittest.main()
