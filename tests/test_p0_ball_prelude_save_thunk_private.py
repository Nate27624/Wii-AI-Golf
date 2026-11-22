"""Synthetic-only P0 original PPC save-GPR helper and second-caller r4."""
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


m=load("p0_source_save_helper",ROOT/"scripts"/"p0_ball_prelude_save_thunk_private.py")
fixture=load("p0_source_postcall_fixture",
             ROOT/"tests"/"test_p0_ball_backedge_postcall_arg_private.py")
TARGET=0x80005000


def d(op,rt,ra,disp):
    return op<<26 | rt<<21 | ra<<16 | (disp&0xFFFF)


def bl(pc,to):
    delta=to-pc
    if delta%4 or not -(1<<25)<=delta<(1<<25):
        raise ValueError("Invalid PPC BL synthetic")
    return 18<<26 | (delta&0x03FFFFFC) | 1


def source():
    code=fixture.program()
    code[m.PRELUDE]=bl(m.PRELUDE,TARGET)
    for i,r in enumerate(range(27,32)):
        code[TARGET+i*4]=d(36,r,11,-20+i*4)
    code[TARGET+20]=0x4E800020  # blr
    code[m.BASE+0x2B84]=d(14,4,4,1)
    code[m.BASE+0x2C78]=d(14,4,0,-1)
    return code


def reader(code):
    return lambda pc:code.get(pc,0x60000000)


class P0NativeSaveHelperTests(unittest.TestCase):
    def test_realistic_save_gpr_27_through_31_plain_stw_then_blr(self):
        h=m.thunk(reader(source()),m.MEM1+0x1000000)
        self.assertTrue(h["callee_is_store_only_GPR_save_thunk_verified"])
        self.assertEqual(h["callee_verified_plain_stw_count"],5)
        self.assertEqual(h["callee_terminal_blr_at_instruction_index"],5)
        self.assertTrue(h["r4_is_preserved_by_exact_callee_source_verified"])
        self.assertFalse(h["source_full_game_guest_execution_proven"])

    def test_exact_caller_one_increments_and_caller_two_sets_minus_one(self):
        args=m.exact_caller_r4(reader(source()))
        self.assertEqual([x["last_r4_setup_syntax"] for x in args],
                         ["addi r4,r4,+1","li r4,-1"])
        self.assertFalse(args[0]["caller_entry_r4_statically_fixed_proven"])
        self.assertTrue(args[1]["caller_entry_r4_statically_fixed_proven"])
        self.assertFalse(args[1]["actual_game_runtime_call_executed_proven"])

    def test_conditional_negative_r28_only_after_helper_proven(self):
        result=m.inspect(reader(source()),m.MEM1+0x1000000)
        self.assertTrue(result["backedge_r28_equals_function_entry_r4_via_source_verified"])
        self.assertTrue(result["second_caller_negative_r28_on_proven_straight_line_if_executed"])
        self.assertFalse(result["byte_flag_r3_plus_0x5C_runtime_value_proven"])
        self.assertFalse(result["guest_backedge_dynamically_executed_proven"])
        self.assertFalse(result["training_approved"])

    def test_helper_writing_r4_fails_closed(self):
        code=source()
        code[TARGET]=d(32,4,11,-20)
        h=m.thunk(reader(code),m.MEM1+0x1000000)
        self.assertFalse(h["callee_is_store_only_GPR_save_thunk_verified"])
        self.assertFalse(h["r4_is_preserved_by_exact_callee_source_verified"])

    def test_helper_store_of_r4_fails_restricted_save_pattern(self):
        code=source()
        code[TARGET]=d(36,4,11,-20)
        self.assertFalse(m.thunk(reader(code),m.MEM1+0x1000000)[
            "r4_is_preserved_by_exact_callee_source_verified"])

    def test_early_branch_or_unknown_operation_abstains(self):
        code=source()
        code[TARGET+8]=0x48000008
        h=m.thunk(reader(code),m.MEM1+0x1000000)
        self.assertFalse(h["r4_is_preserved_by_exact_callee_source_verified"])
        self.assertEqual(h["callee_non_save_instruction_or_unbounded_reason"],
                         "instruction_not_plain_nonvolatile_GPR_store")

    def test_bounded_missing_return_fails_closed(self):
        code=source()
        for i in range(m.MAX_THUNK_INSNS):
            code[TARGET+i*4]=d(36,27,11,-20)
        h=m.thunk(reader(code),m.MEM1+0x1000000)
        self.assertFalse(h["callee_is_store_only_GPR_save_thunk_verified"])
        self.assertEqual(h["callee_non_save_instruction_or_unbounded_reason"],
                         "bounded_helper_has_no_terminal_blr")

    def test_wrong_second_caller_negative_arg_abstains(self):
        code=source()
        code[m.BASE+0x2C78]=d(14,4,0,0)
        with self.assertRaises(ValueError):
            m.exact_caller_r4(reader(code))

    def test_call_window_modifies_r4_abstains(self):
        code=source()
        code[m.BASE+0x2C7C]=d(14,4,4,1)
        items=m.exact_caller_r4(reader(code))
        self.assertFalse(items[1]["r4_literal_minus_one_at_entry_on_straight_line_if_called"])

    def test_wrong_save_helper_linked_target_bounds_do_not_expose_absolute(self):
        code=source()
        code[m.PRELUDE]=bl(m.PRELUDE,0x80290000)
        h=m.thunk(reader(code),m.MEM1+0x20000)
        self.assertFalse(h["r4_is_preserved_by_exact_callee_source_verified"])
        self.assertFalse(h["source_full_game_guest_execution_proven"])

    def test_wrong_save_helper_return_opcode_refuses(self):
        code=source()
        code[TARGET+20]=0x60000000
        h=m.thunk(reader(code),m.MEM1+0x1000000)
        self.assertFalse(h["r4_is_preserved_by_exact_callee_source_verified"])

    def test_no_original_code_or_target_address_leaks(self):
        data=m.inspect(reader(source()),m.MEM1+0x1000000)
        out=json.dumps(data,sort_keys=True)
        self.assertNotIn("0x80005000",out)
        self.assertNotIn("original_PPC_opcode_word",out)
        self.assertNotIn("private_RAM_dump",out)
        self.assertFalse(data["selected_live_ball_object_receiver_proven"])
        self.assertFalse(data["wood_vs_foliage_collision_handler_verified"])


if __name__=="__main__":
    unittest.main()
