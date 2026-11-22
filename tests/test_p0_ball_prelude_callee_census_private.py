"""Synthetic-only original PPC native callee census; no ROM/gameplay data."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

m=load("p0_native_callee_census",ROOT/"scripts"/"p0_ball_prelude_callee_census_private.py")
prev=load("p0_native_callee_census_fixtures",
          ROOT/"tests"/"test_p0_ball_prelude_save_thunk_private.py")
TARGET=prev.TARGET

def d(op,rt,ra,disp):
    return (op<<26)|(rt<<21)|(ra<<16)|(disp&65535)

def original(stmw=False):
    code=prev.source()
    if stmw:
        code[TARGET]=d(47,27,11,-20)
        code[TARGET+4]=0x4E800020
    return code

def read(code):
    return lambda pc:code.get(pc,0x60000000)

class OriginalCalleeCensusTests(unittest.TestCase):
    def test_compiler_stmw_save_form_classifies(self):
        item=m.syntax(d(47,27,11,-20))
        self.assertEqual(item["kind"],"stmw")
        self.assertEqual(item["first_stored_register"],27)
        self.assertEqual(item["last_stored_register"],31)
        self.assertTrue(item["proven_r4_unchanged"])

    def test_stmw_then_blr_preserves_r4_without_abi_assumption(self):
        p=original(stmw=True)
        result=m.inspect(read(p),m.MEM1+0x1000000)
        x=result["callee_first_24_source_instruction_syntax"]
        self.assertTrue(x["recognized_complete_store_only_helper_proven"])
        self.assertTrue(x["exact_register_r4_preservation_proven"])
        self.assertTrue(result[
            "second_caller_minus_one_can_feed_r28_if_executed_and_path_reached"])
        self.assertFalse(result["actual_native_collision_branch_proven"])
        self.assertFalse(result["training_approved"])

    def test_old_stw_thunk_still_accepted_with_original_function(self):
        p=original()
        result=m.inspect(read(p),m.MEM1+0x1000000)
        self.assertTrue(result["callee_first_24_source_instruction_syntax"][
            "original_previous_plain_stw_only_helper_verified"])
        self.assertTrue(result["exact_callee_preserves_r4_if_stw_stmw_only_plus_blr"])

    def test_failure_of_previous_narrow_pattern_does_not_mean_clobber(self):
        p=original(stmw=True)
        x=m.classify_original_target(read(p),m.MEM1+0x1000000)
        self.assertFalse(x["original_previous_plain_stw_only_helper_verified"])
        self.assertTrue(x["exact_register_r4_preservation_proven"])

    def test_actual_six_stw_r26_through_r31_then_blr_source_shape(self):
        p=original()
        for i,reg in enumerate(range(26,32)):
            p[TARGET+4*i]=d(36,reg,11,-24+4*i)
        p[TARGET+24]=0x4E800020
        p[TARGET+28]=d(32,26,11,-24)  # after the return
        x=m.inspect(read(p),m.MEM1+0x1000000)
        callee=x["callee_first_24_source_instruction_syntax"]
        self.assertFalse(callee["original_previous_plain_stw_only_helper_verified"])
        self.assertTrue(x["native_original_r26_r31_save_thunk_source_verified"])
        self.assertTrue(callee["exact_register_r4_preservation_proven"])
        self.assertEqual(callee["store_only_complete_ordinary_blr_index"],6)
        self.assertTrue(x["original_callee_and_following_instructions_preserve_r4_verified"])
        self.assertTrue(x["second_caller_minus_one_can_feed_r28_if_executed_and_path_reached"])
        self.assertFalse(x["actual_native_collision_branch_proven"])

    def test_actual_save_helper_with_r25_prefix_does_not_match_restricted_grammar(self):
        p=original()
        p[TARGET]=d(36,25,11,-24)
        x=m.classify_original_target(read(p),m.MEM1+0x1000000)
        self.assertFalse(x["exact_register_r4_preservation_proven"])

    def test_entry_prelude_r4_overwrite_blocks_complete_negative_argument_proof(self):
        p=original()
        for i,reg in enumerate(range(26,32)):
            p[TARGET+4*i]=d(36,reg,11,-24+4*i)
        p[TARGET+24]=0x4E800020
        p[m.old.cfg.ENTRY+4]=d(14,4,4,1)
        x=m.inspect(read(p),m.MEM1+0x1000000)
        self.assertTrue(x["exact_callee_preserves_r4_if_stw_stmw_only_plus_blr"])
        self.assertFalse(x["source_entry_to_save_thunk_r4_register_preservation"][
            "r4_preserved_between_entry_and_helper_call_source_verified"])
        self.assertFalse(x["original_entry_r4_to_r28_straightline_source_verified"])
        self.assertFalse(x["second_caller_minus_one_can_feed_r28_if_executed_and_path_reached"])

    def test_native_stfd_and_psq_store_original_prologue_preserve_r4(self):
        p=original()
        for i,reg in enumerate(range(26,32)):
            p[TARGET+4*i]=d(36,reg,11,-24+4*i)
        p[TARGET+24]=0x4E800020
        # Simulate the two previously unrecognized original prologue
        # instructions without inventing any real native source words.
        p[m.old.cfg.ENTRY+12]=d(54,31,1,16)  # stfd f31,16(r1)
        p[m.old.cfg.ENTRY+16]=d(60,31,1,8)   # psq_st f31,8(r1)
        x=m.inspect(read(p),m.MEM1+0x1000000)
        entry=x["source_entry_to_save_thunk_r4_register_preservation"]
        self.assertTrue(entry["r4_preserved_between_entry_and_helper_call_source_verified"])
        self.assertEqual(
            [s["source_primary_opcode_number"] for s in
             entry["bounded_entry_prologue_register_gate_sites"][3:5]], [54,60])
        self.assertTrue(x["original_entry_r4_to_r28_straightline_source_verified"])
        self.assertTrue(x["second_caller_minus_one_can_feed_r28_if_executed_and_path_reached"])
        self.assertFalse(x["actual_native_collision_branch_proven"])

    def test_psq_stu_with_r4_base_update_fails_prologue(self):
        p=original()
        p[m.old.cfg.ENTRY+12]=d(61,31,4,16)
        gate=m.entry_r4_register_gate(read(p))
        self.assertFalse(gate["r4_preserved_between_entry_and_helper_call_source_verified"])
        record=gate["bounded_entry_prologue_register_gate_sites"][3]
        self.assertTrue(record["recognized_destination_r4_write"])
        self.assertFalse(record["r4_preserved_by_this_instruction_source_gate"])

    def test_nonupdating_floating_store_with_r4_source_base_does_not_write_r4(self):
        p=original()
        p[m.old.cfg.ENTRY+12]=d(54,31,4,16)
        p[m.old.cfg.ENTRY+16]=d(60,31,4,8)
        gate=m.entry_r4_register_gate(read(p))
        self.assertTrue(gate["r4_preserved_between_entry_and_helper_call_source_verified"])

    def test_postcall_local_r4_write_blocks_negative_r28_propagation(self):
        p=original()
        for i,reg in enumerate(range(26,32)):
            p[TARGET+4*i]=d(36,reg,11,-24+4*i)
        p[TARGET+24]=0x4E800020
        p[m.old.PRELUDE+4]=d(14,4,0,1)
        result=m.inspect(read(p),m.MEM1+0x1000000)
        self.assertTrue(result["exact_callee_preserves_r4_if_stw_stmw_only_plus_blr"])
        self.assertFalse(result[
            "source_postcall_to_r28_r4_register_preservation"][
                "r4_preserved_between_return_and_r28_binding_source_verified"])
        self.assertFalse(result["second_caller_minus_one_can_feed_r28_if_executed_and_path_reached"])

    def test_postcall_unknown_instruction_abstains_from_r4_proof(self):
        p=original()
        p[m.old.PRELUDE+4]=(31<<26)|(4<<21)|(4<<16)|(3<<11)|(266<<1)
        x=m.postcall_r4_register_gate(read(p))
        self.assertFalse(x["r4_preserved_between_return_and_r28_binding_source_verified"])
        self.assertFalse(x["whole_game_runtime_path_or_external_entry_proven"])

    def test_unknown_instruction_first_fails_without_r4_clobber_conclusion(self):
        p=original(stmw=True)
        p[TARGET]=0x64010000
        x=m.inspect(read(p),m.MEM1+0x1000000)
        self.assertFalse(x["exact_callee_preserves_r4_if_stw_stmw_only_plus_blr"])
        self.assertTrue(x["previous_stw_only_helper_result_was_not_r4_clobber_proof"])

    def test_stwu_and_other_prologue_stays_conservative(self):
        p=original(stmw=True)
        p[TARGET]=d(37,1,1,-32)
        x=m.classify_original_target(read(p),m.MEM1+0x1000000)
        self.assertFalse(x["exact_register_r4_preservation_proven"])
        self.assertEqual(x["bounded_native_callee_instruction_categories"][0]["kind"],"stwu")

    def test_stmw_then_branch_does_not_prove_local_return(self):
        p=original(stmw=True)
        p[TARGET+4]=0x48000008
        x=m.classify_original_target(read(p),m.MEM1+0x1000000)
        self.assertFalse(x["exact_register_r4_preservation_proven"])

    def test_nop_between_store_and_return_permitted(self):
        p=original(stmw=True)
        p[TARGET+4]=0x60000000
        p[TARGET+8]=0x4E800020
        x=m.classify_original_target(read(p),m.MEM1+0x1000000)
        self.assertTrue(x["exact_register_r4_preservation_proven"])
        self.assertEqual(x["store_only_complete_ordinary_blr_index"],2)

    def test_unknown_instructions_after_return_are_not_execution_proof(self):
        p=original(stmw=True)
        p[TARGET+8]=d(14,4,4,1)
        x=m.classify_original_target(read(p),m.MEM1+0x1000000)
        self.assertTrue(x["exact_register_r4_preservation_proven"])
        self.assertFalse(x["native_guest_call_executed_in_tree_shots_proven"])

    def test_target_outside_bounded_original_bank_fails_closed(self):
        p=original(stmw=True)
        pc=m.old.PRELUDE
        p[pc]=prev.bl(pc,m.old.BASE-0x100)
        x=m.classify_original_target(read(p),m.MEM1+0x20000)
        self.assertFalse(x["exact_register_r4_preservation_proven"])
        self.assertFalse(x["target_in_original_source_MEM1_bounded_window"])

    def test_r4_written_in_callee_nonstore_path_cannot_certify(self):
        p=original(stmw=True)
        p[TARGET]=d(14,4,4,-1)
        x=m.classify_original_target(read(p),m.MEM1+0x1000000)
        self.assertFalse(x["exact_register_r4_preservation_proven"])
        self.assertFalse(x["bounded_native_callee_instruction_categories"][0][
            "proven_r4_unchanged"])

    def test_output_contains_only_instruction_categories_no_absolute_pc(self):
        p=original(stmw=True)
        x=m.inspect(read(p),m.MEM1+0x1000000)
        text=json.dumps(x,sort_keys=True)
        self.assertNotIn("0x80005000",text)
        self.assertNotIn("original_native_code_word",text)
        self.assertNotIn("private_ROM_bytes",text)
        self.assertFalse(x["selected_active_Ball_cache_receiver_proven"])


if __name__=="__main__":
    unittest.main()
