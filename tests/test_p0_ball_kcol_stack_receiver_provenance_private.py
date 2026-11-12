"""Synthetic-only KCol result stack slots and r23 receiver provenance."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

m=load("p0_kcol_stack_receiver",
       ROOT/"scripts"/"p0_ball_kcol_stack_receiver_provenance_private.py")
fixture=load("p0_kcol_stack_fixture",
             ROOT/"tests"/"test_p0_ball_kcol_cr0_float_sources_private.py")


def d(op,rt,ra,imm):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&0xffff)


def mr(dst,src):
    return (31<<26)|(src<<21)|(dst<<16)|(src<<11)|(444<<1)


def program():
    p=fixture.program()
    for i,(load,store,_) in enumerate(m.old.FLOAT_PAIRS):
        p[m.BALL+load]=d(48,0,1,m.STACK_SLOTS[i])
    return p


def read(p):
    return lambda pc:p.get(pc,0x60000000)


class BallKcolStackReceiverTests(unittest.TestCase):
    def test_exact_original_three_stack_loads_and_class_dispatch(self):
        x=m.original_anchors(read(program()))
        self.assertEqual(x["original_three_stack_component_load_offsets"],
                         [76,80,84])
        self.assertTrue(x["source_compares_class_7_12_and_skips_triad"])
        self.assertFalse(x["same_stack_slot_is_proven_written_by_KCol_query"])

    def test_stack_source_load_changed_refuses(self):
        p=program()
        p[m.BALL+0x150C]=d(48,0,1,0x58)
        with self.assertRaises(ValueError):
            m.original_anchors(read(p))

    def test_query_direct_call_changed_refuses(self):
        p=program()
        p[m.BALL+m.CALL]=d(14,3,3,0)
        with self.assertRaises(ValueError):
            m.original_anchors(read(p))

    def test_stack_slot_access_and_argument_source_are_syntax_only(self):
        p=program()
        p[m.BALL+0x14B8]=d(14,6,1,0x4C)
        p[m.BALL+0x14B0]=d(52,5,1,0x50)
        x=m.caller_stack_accesses(read(p))
        self.assertIn("lfs",x["recognized_postcall_stack_slot_access_counts"])
        self.assertIn("stfs",x["recognized_precall_stack_slot_access_counts"])
        arg=[a for a in x["original_precall_addi_stack_address_formations"]
             if a["source_site"]=="Ball+0x14B8"][0]
        self.assertEqual(arg["destination_GPR"],6)
        self.assertEqual(arg["source_stack_relative_immediate"],76)
        self.assertFalse(arg["actual_query_parameter_role_proven"])
        self.assertFalse(x["precise_KCol_output_pointer_arg_proven"])

    def test_no_prior_output_pointer_proven_if_only_stack_float_loads(self):
        x=m.caller_stack_accesses(read(program()))
        self.assertFalse(x["precise_KCol_output_pointer_arg_proven"])
        self.assertFalse(x["all_writer_aliases_of_stack_slots_exhausted"])

    def test_r23_definition_syntactic_not_active_ball_proof(self):
        p=program()
        p[m.BALL+0x1400]=mr(23,3)
        x=m.r23_context(read(p))
        a=[v for v in x["source_r23_definition_candidates"]
           if v["source_site"]=="Ball+0x1400"]
        self.assertEqual(len(a),1)
        self.assertFalse(a[0]["is_actual_reaching_r23_definition_proven"])
        self.assertFalse(x["receiver_r23_is_selected_active_ball_proven"])

    def test_unknown_X_form_flagged_in_r23_source_context(self):
        p=program()
        p[m.BALL+0x1430]=(31<<26)|(999<<1)
        x=m.r23_context(read(p))
        self.assertIn("Ball+0x1430",[
            y["source_site"] for y in x["source_unsupported_GPR_effect_sites"]])
        self.assertFalse(x["complete_function_entry_to_r23_SSA_proven"])

    def test_main_kcol_entry_parameter_store_is_not_proven_output_buffer(self):
        p=program()
        p[m.KCOL+0x50]=d(52,1,7,0)
        x=m.kcol_entry(read(p))
        self.assertIn("stfs",x["recognized_memory_and_branch_opcode_counts"])
        row=[a for a in x["bounded_potential_parameter_based_memory_accesses"]
             if a["source_site"]=="GolfKCol+0x0050"]
        self.assertEqual(len(row),1)
        self.assertFalse(row[0]["is_the_caller_stack_component_buffer_proven"])
        self.assertFalse(x["direct_KCol_write_to_Ball_stack_4C_50_54_proven"])

    def test_result_report_no_velocity_or_tree_material_promotion(self):
        x=m.inspect(read(program()))
        self.assertEqual(x["status"],"SHA_QUALIFIED_BALL_KCOL_STACK_COMPONENT_SOURCE_CENSUS")
        self.assertFalse(x["query_wrote_three_stack_floats_verified"])
        self.assertFalse(x["class_7_or_12_is_tree_trunk_or_foliage_proven"])
        self.assertFalse(x["receiver_is_selected_live_Ball_or_velocity_proven"])
        self.assertFalse(x["native_tree_contact_impact_impulse_restitution_proven"])
        self.assertFalse(x["training_approved"])
        serialized=json.dumps(x)
        self.assertNotIn("private_archive_path",serialized)
        self.assertNotIn("PPC_WORD",serialized)
        self.assertNotIn("0x90008000",serialized)

    def test_only_numeric_stack_offset_not_runtime_alias(self):
        p=program()
        p[m.BALL+0x14C0]=d(48,2,1,0x4C)
        x=m.caller_stack_accesses(read(p))
        self.assertGreaterEqual(x["recognized_r1_stack_slot_4C_50_54_access_counts"]["lfs"],4)
        self.assertFalse(x["precise_KCol_output_pointer_arg_proven"])


if __name__=="__main__":
    unittest.main()
