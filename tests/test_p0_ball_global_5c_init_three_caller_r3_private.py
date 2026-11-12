"""Synthetic-only three exact native initializer callers and r3 receiver source."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

m=module("p0_3init_source",
         ROOT/"scripts"/"p0_ball_global_5c_init_three_caller_r3_private.py")
prior=module("p0_3init_fixture",
             ROOT/"tests"/"test_p0_ball_global_5c_init_caller_join_private.py")


def d(op,rt,ra,imm):
    return op<<26 | rt<<21 | ra<<16 | (imm&65535)


def program():
    p=prior.program(add_helper_initializer_call=False)
    for site in m.CALLERS:
        p[site]=prior.bl(site,m.TARGET)
    return p


def read(p):
    return lambda pc:p.get(pc,0x60000000)


class OriginalThreeCallerArgumentTests(unittest.TestCase):
    def test_exact_three_direct_native_initializer_callers(self):
        a=m.direct_calls(read(program()))
        self.assertEqual(
            a["original_exact_direct_initializer_BL_sites"],
            ["Ball+0x2B60","Ball+0x320C","Ball+0x3248"])
        self.assertEqual(a["original_exact_initializer_target"],"Ball+0x3108")
        self.assertFalse(a["initializer_object_matches_r13_global_proven"])

    def test_wrong_target_one_caller_abstains(self):
        p=program()
        p[m.CALLERS[1]]=prior.bl(m.CALLERS[1],m.TARGET+4)
        with self.assertRaises(ValueError):
            m.direct_calls(read(p))

    def test_unexpected_extra_direct_bl_abstains(self):
        p=program()
        site=m.BALL+0x3214
        p[site]=prior.bl(site,m.TARGET)
        with self.assertRaises(ValueError):
            m.direct_calls(read(p))

    def test_direct_r3_global_slot_load_is_syntactic_candidate(self):
        p=program()
        site=m.CALLERS[0]-4
        p[site]=d(32,3,13,m.GLOBAL_SLOT)
        a=m.receiver(read(p),m.CALLERS[0])
        self.assertEqual(a["nearest_syntactic_definition"]["source_site"],
                         "Ball+0x2B5C")
        self.assertTrue(a["source_immediate_global_slot_load_before_call_no_barriers"])
        self.assertFalse(a["actual_receiver_same_object_as_global_registration_proven"])

    def test_r3_receiver_passed_from_other_register_not_global(self):
        p=program()
        p[m.CALLERS[0]-4]=d(14,3,31,0)
        a=m.receiver(read(p),m.CALLERS[0])
        self.assertFalse(a["source_immediate_global_slot_load_before_call_no_barriers"])
        self.assertFalse(a["function_boundary_and_all_predecessors_qualified"])

    def test_control_barrier_invalidates_unbroken_receiver(self):
        p=program()
        p[m.CALLERS[0]-4]=prior.bl(m.CALLERS[0]-4,m.BALL+0x4020)
        p[m.CALLERS[0]-8]=d(32,3,13,m.GLOBAL_SLOT)
        a=m.receiver(read(p),m.CALLERS[0])
        self.assertGreater(a["nearest_syntactic_definition"][
            "intervening_control_site_count"],0)
        self.assertFalse(a["source_immediate_global_slot_load_before_call_no_barriers"])

    def test_unsupported_opcode_abstains_before_nearest_gpr(self):
        p=program()
        p[m.CALLERS[0]-4]=(4<<26)
        p[m.CALLERS[0]-8]=d(32,3,13,m.GLOBAL_SLOT)
        a=m.receiver(read(p),m.CALLERS[0])
        self.assertGreater(a["nearest_syntactic_definition"][
            "intervening_unknown_opcode_count"],0)
        self.assertFalse(a["source_immediate_global_slot_load_before_call_no_barriers"])

    def test_no_bounded_def_does_not_assume_entry_receiver(self):
        a=m.receiver(read(program()),m.CALLERS[0])
        self.assertIsNone(a["nearest_syntactic_definition"])
        self.assertFalse(a["actual_receiver_same_object_as_global_registration_proven"])

    def test_inspect_reports_three_caller_windows(self):
        x=m.inspect(read(program()))
        self.assertEqual(len(x["initializer_callsite_bounded_contexts"]),3)
        self.assertEqual(len(x["initializer_callsite_source_r3_ancestry"]),3)
        self.assertTrue(all(len(y["original_bounded_lexical_instruction_categories"])>0
                            for y in x["initializer_callsite_bounded_contexts"]))
        self.assertFalse(x["initialization_and_zero_clear_same_object_verified"])

    def test_source_anchor_global_registration_separate(self):
        a=m.direct_calls(read(program()))
        self.assertEqual(a["global_registration_direct_BL_site"],"Ball+0x3080")
        self.assertEqual(a["global_registration_callee_site"],"Ball+0x3BA0")
        self.assertFalse(a["registration_is_one_of_three_direct_initializer_BLs"])

    def test_untouched_original_guest_and_training_flags(self):
        data=m.inspect(read(program()))
        self.assertFalse(data["selected_live_Ball_object_or_native_impact_verified"])
        self.assertFalse(data["wood_versus_foliage_material_physics_verified"])
        self.assertFalse(data["training_approved"])
        output=json.dumps(data)
        self.assertNotIn("0x90008000",output)
        self.assertNotIn("original_native_ppc_word",output)
        self.assertNotIn("private_archive_path",output)


if __name__=="__main__":
    unittest.main()
