"""Synthetic-only Ball global registration versus initializer caller join."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

m=load("p0_global_init_caller_join",
       ROOT/"scripts"/"p0_ball_global_5c_init_caller_join_private.py")


def d(op,rt,ra,imm):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&65535)


def mr(dst,src):
    return (31<<26)|(src<<21)|(dst<<16)|(src<<11)|(444<<1)


def bl(pc,target):
    delta=target-pc
    if delta%4 or delta<=-(1<<25) or delta>=(1<<25):
        raise ValueError("Synthetic direct BL displacement out of range")
    return (18<<26)|(delta&0x03FFFFFC)|1


def bc(pc,target):
    delta=target-pc
    if delta%4 or delta<=-(1<<15) or delta>=(1<<15):
        raise ValueError("Synthetic BC displacement out of range")
    return (16<<26)|(12<<21)|(2<<16)|(delta&0xFFFC)


def xform(rt,ra,rb,xo):
    return (31<<26)|(rt<<21)|(ra<<16)|(rb<<11)|(xo<<1)


def program(add_helper_initializer_call=True):
    p={}
    p[m.BALL+0x3068]=d(14,3,0,428)
    p[m.BALL+0x3078]=bc(m.BALL+0x3078,m.BALL+0x3084)
    p[m.BALL+0x307C]=d(14,4,0,0)
    p[m.BALL+0x3080]=bl(m.BALL+0x3080,m.LOCAL_TARGET)
    p[m.GLOBAL_STORE]=d(36,3,13,m.init.source.GLOBAL_SLOT)
    p[m.BALL+0x311C]=d(14,6,0,0)
    p[m.BALL+0x3124]=d(14,5,0,1)
    p[m.BALL+0x3134]=mr(31,3)
    p[m.BALL+0x3144]=d(36,6,3,0x54)
    p[m.BALL+0x3148]=d(36,6,3,0x58)
    p[m.BALL+0x314C]=d(38,5,3,0x5C)
    p[m.BALL+0x3150]=d(38,6,3,0x5D)
    p[m.BALL+0x2CC4]=d(14,30,0,0)
    p[m.BALL+0x2D30]=d(32,26,13,m.init.source.GLOBAL_SLOT)
    p[m.BALL+0x2D8C]=d(38,30,26,0x5C)
    p[m.BALL+0x2D44]=xform(0,0,2,824)
    p[m.BALL+0x2D48]=xform(0,0,0,202)
    if add_helper_initializer_call:
        p[m.LOCAL_TARGET+8]=bl(m.LOCAL_TARGET+8,m.BALL+0x3108)
    return p


def read(p):
    return lambda pc:p.get(pc,0x60000000)


class SourceInitializerJoinTests(unittest.TestCase):
    def test_original_registration_and_flag_init_anchors_are_exact(self):
        x=m.qualified(read(program()))
        self.assertTrue(x["original_call_result_GPR3_stored_after_call_syntactically"])
        self.assertEqual(x["source_direct_call_target"],"Ball+0x3BA0")
        self.assertFalse(x["callee_returned_pointer_matches_initializer_receiver_proven"])

    def test_inbound_direct_BL_counts_candidate_region_without_alias_promotion(self):
        x=m.inbound(read(program()))
        self.assertGreaterEqual(x["total_direct_BL_to_candidate_region_in_public_Ball_unit"],1)
        self.assertIn("Ball+0x3BA8",
                      [row["direct_BL_source_site"]
                       for row in x["bounded_direct_BL_callers"]])
        self.assertTrue(x["bounded_local_target_first_32_instruction_direct_BLs"][0][
            "source_target_is_in_candidate_initializer_region"])
        self.assertFalse(x["whole_game_callers_or_indirect_dispatch_exhausted"])

    def test_source_join_flag_is_not_pointer_identity_proof(self):
        x=m.inspect(read(program()))
        self.assertTrue(x["source_direct_3BA0_call_to_initializer_candidate_present"])
        self.assertFalse(x["initializer_receiver_aliases_r13_global_pointer_proven"])
        self.assertFalse(x["object_identity_selected_live_Ball_proven"])
        self.assertFalse(x["native_wood_foliage_collision_branch_proven"])
        self.assertFalse(x["training_approved"])

    def test_source_helper_might_not_call_initializer_in_32_instr_window(self):
        x=m.inspect(read(program(add_helper_initializer_call=False)))
        self.assertFalse(x["source_direct_3BA0_call_to_initializer_candidate_present"])
        self.assertEqual(x["source_direct_callsite_census"][
            "total_direct_BL_to_candidate_region_in_public_Ball_unit"],0)

    def test_wrong_registration_callee_fails_closed(self):
        p=program()
        p[m.CALL]=bl(m.CALL,m.LOCAL_TARGET+4)
        with self.assertRaises(ValueError):
            m.qualified(read(p))

    def test_wrong_global_slot_store_fails_closed(self):
        p=program()
        p[m.GLOBAL_STORE]=d(36,3,13,-23300)
        with self.assertRaises(ValueError):
            m.qualified(read(p))

    def test_wrong_literal_one_initializer_fails_closed(self):
        p=program()
        p[m.BALL+0x3124]=d(14,5,0,0)
        with self.assertRaises(ValueError):
            m.qualified(read(p))

    def test_source_window_reports_only_instruction_categories(self):
        x=m.source_window(read(program()),m.LOCAL_TARGET,m.LOCAL_TARGET+32)
        self.assertEqual(len(x),8)
        self.assertEqual(x[2]["operation"],"direct_bl_call")
        self.assertNotIn("word",x[2])
        self.assertNotIn("raw_code",x[2])

    def test_source_window_bounds_fail_closed(self):
        with self.assertRaises(ValueError):
            m.source_window(read(program()),m.LOCAL_TARGET,
                            m.LOCAL_TARGET+400)
        with self.assertRaises(ValueError):
            m.source_window(read(program()),m.BALL-4,m.BALL+4)

    def test_indirect_or_unlinked_branch_does_not_count_as_direct_bl(self):
        p=program(add_helper_initializer_call=False)
        p[m.LOCAL_TARGET+8]=(18<<26)|(
            ((m.BALL+0x3108)-(m.LOCAL_TARGET+8))&0x03FFFFFC)
        x=m.inbound(read(p))
        self.assertFalse(x["bounded_local_target_first_32_instruction_direct_BLs"])

    def test_synthetic_output_not_runtime_physics_or_original_raw_data(self):
        result=m.inspect(read(program()))
        s=json.dumps(result,sort_keys=True)
        self.assertFalse(result["guest_impact_execution_velocity_restitution_proven"])
        self.assertFalse(result["training_approved"])
        self.assertNotIn("0x90008000",s)
        self.assertNotIn("private_ROM",s)
        self.assertNotIn("original_binary_word",s)


if __name__=="__main__":
    unittest.main()
