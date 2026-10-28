"""Native-free PPC branch-sensitive local candidate test for global slot store."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import review_p0_global_slot_store_cfg as mod


def dform(op,reg,base,imm):
    return op<<26 | reg<<21 | base<<16 | (imm&0xffff)

def b(pc,dst,linked=False):
    return 18<<26 | ((dst-pc)&0x03fffffc) | int(linked)

def bc(pc,dst,linked=False):
    # bc with no link, unconstrained condition. Both outcomes possible.
    return 16<<26 | ((dst-pc)&0xfffc) | int(linked)

def fixture():
    words={pc:0x60000000 for pc in range(mod.START,mod.STORE_PC+4,4)}
    words[mod.ADDI_PC]=dform(14,3,0,1)
    words[mod.STORE_PC]=dform(36,3,13,-100)
    return words


class BoundedCFG(unittest.TestCase):
    def test_single_path_nonzero_literal_addi_candidate(self):
        words=fixture()
        out=mod.analyze(words.__getitem__,-100)
        self.assertEqual(out["addi_base_register_class"],"r0_zero_base")
        self.assertEqual(out["addi_immediate_class"],"positive")
        self.assertIn("addi_literal_nonzero",out["bounded_cfg_reaching_r3_candidate_classes"])
        self.assertFalse(out["addi_constructs_zero_literal"])
        self.assertFalse(out["full_function_cfg_or_reaching_definition_proven"])

    def test_literal_zero_source_is_only_candidate_not_runtime_proof(self):
        words=fixture()
        words[mod.ADDI_PC]=dform(14,3,0,0)
        out=mod.analyze(words.__getitem__,-100)
        self.assertTrue(out["addi_constructs_zero_literal"])
        self.assertFalse(out["store_runtime_value_verified"])
        self.assertFalse(out["source_global_owner_created_here_verified"])

    def test_branch_bypasses_addi_causes_multiple_candidates(self):
        words=fixture()
        words[mod.START+4]=bc(mod.START+4,mod.ADDI_PC+4)
        out=mod.analyze(words.__getitem__,-100)
        self.assertIn("unknown_entry_r3",out["bounded_cfg_reaching_r3_candidate_classes"])
        self.assertIn("addi_literal_nonzero",out["bounded_cfg_reaching_r3_candidate_classes"])
        self.assertTrue(out["bounded_cfg_multiple_candidate_sources"])

    def test_unconditional_branch_skip_addi(self):
        words=fixture()
        words[mod.START+4]=b(mod.START+4,mod.ADDI_PC+4)
        out=mod.analyze(words.__getitem__,-100)
        self.assertEqual(out["bounded_cfg_reaching_r3_candidate_classes"],["unknown_entry_r3"])

    def test_branch_after_addi_to_store_keeps_candidate_local(self):
        words=fixture()
        words[mod.ADDI_PC+4]=bc(mod.ADDI_PC+4,mod.STORE_PC)
        out=mod.analyze(words.__getitem__,-100)
        self.assertTrue(out["bounded_cfg_branch_sites"])
        self.assertEqual(out["bounded_cfg_reaching_r3_candidate_classes"],["addi_literal_nonzero"])
        self.assertTrue(out["external_entries_to_window_not_excluded"])

    def test_jump_outside_window_prevents_definite_source(self):
        words=fixture()
        words[mod.ADDI_PC+4]=b(mod.ADDI_PC+4,mod.STORE_PC+8)
        out=mod.analyze(words.__getitem__,-100)
        self.assertTrue(out["bounded_cfg_escape_or_unknown_control_flow"])
        self.assertFalse(out["bounded_cfg_paths_reach_store"])

    def test_bl_clobbers_volatile_r3(self):
        words=fixture()
        words[mod.ADDI_PC+4]=b(mod.ADDI_PC+4,mod.STORE_PC+0x40,linked=True)
        out=mod.analyze(words.__getitem__,-100)
        self.assertTrue(out["bounded_cfg_escape_or_unknown_control_flow"])
        self.assertEqual(out["bounded_cfg_reaching_r3_candidate_classes"],["unknown_after_call"])

    def test_other_r3_load_overwrites_previous_addi(self):
        words=fixture()
        words[mod.ADDI_PC+8]=dform(32,3,31,0)
        out=mod.analyze(words.__getitem__,-100)
        self.assertEqual(out["bounded_cfg_reaching_r3_candidate_classes"],["other_r3_value_assignment"])

    def test_ra_destination_logical_overwrites_prior_r3_addi(self):
        # All these PPC integer instructions use rA (bits 16..20) as
        # destination and rS (bits 21..25) as their source.
        for op in (24,25,26,27,28,29):
            with self.subTest(op=op):
                words=fixture()
                words[mod.ADDI_PC+8]=dform(op,4,3,1)
                out=mod.analyze(words.__getitem__,-100)
                self.assertEqual(
                    out["bounded_cfg_reaching_r3_candidate_classes"],
                    ["ra_form_r3_assignment_unknown"])
                self.assertNotIn(
                    "addi_literal_nonzero",
                    out["bounded_cfg_reaching_r3_candidate_classes"])
                self.assertFalse(out["full_function_cfg_or_reaching_definition_proven"])

    def test_ra_destination_rotate_overwrites_prior_addi(self):
        for op in (20,21,23):
            with self.subTest(op=op):
                words=fixture()
                words[mod.ADDI_PC+8]=dform(op,4,3,1)
                out=mod.analyze(words.__getitem__,-100)
                self.assertEqual(
                    out["bounded_cfg_reaching_r3_candidate_classes"],
                    ["ra_form_r3_assignment_unknown"])

    def test_r3_as_source_only_does_not_invalidate_addi(self):
        # rS=3 but rA=4: source is r3, destination is another register.
        for op in (20,21,23,24,25,26,27,28,29):
            with self.subTest(op=op):
                words=fixture()
                words[mod.ADDI_PC+8]=dform(op,3,4,1)
                out=mod.analyze(words.__getitem__,-100)
                self.assertEqual(
                    out["bounded_cfg_reaching_r3_candidate_classes"],
                    ["addi_literal_nonzero"])

    def test_ra_write_after_branch_keeps_multiple_path_sources(self):
        words=fixture()
        words[mod.START+4]=bc(mod.START+4,mod.ADDI_PC+12)
        words[mod.ADDI_PC+8]=dform(24,4,3,0)
        out=mod.analyze(words.__getitem__,-100)
        self.assertIn(
            "ra_form_r3_assignment_unknown",
            out["bounded_cfg_reaching_r3_candidate_classes"])
        self.assertIn(
            "unknown_entry_r3",
            out["bounded_cfg_reaching_r3_candidate_classes"])
        self.assertTrue(out["bounded_cfg_multiple_candidate_sources"])
        self.assertFalse(out["store_runtime_value_verified"])

    def test_lmw_writes_r3_even_when_first_destination_is_lower(self):
        for first,expected in (
            (0,"lmw_range_overwrites_r3"),
            (1,"lmw_range_overwrites_r3"),
            (2,"lmw_range_overwrites_r3"),
            (3,"lmw_range_overwrites_r3"),
            (4,"addi_literal_nonzero"),
        ):
            with self.subTest(first=first):
                words=fixture()
                words[mod.ADDI_PC+8]=dform(46,first,4,0)
                out=mod.analyze(words.__getitem__,-100)
                self.assertEqual(
                    out["bounded_cfg_reaching_r3_candidate_classes"],
                    [expected])

    def test_stmw_reads_r3_but_never_redefines_r3(self):
        words=fixture()
        words[mod.ADDI_PC+8]=dform(47,3,4,0)
        out=mod.analyze(words.__getitem__,-100)
        self.assertEqual(
            out["bounded_cfg_reaching_r3_candidate_classes"],
            ["addi_literal_nonzero"])

    def test_integer_and_floating_update_base_r3_writes(self):
        # GPR load-update variants; source/destination rT is not r3.
        for op in (33,35,41,43):
            with self.subTest(op=op):
                words=fixture()
                words[mod.ADDI_PC+8]=dform(op,0,3,4)
                out=mod.analyze(words.__getitem__,-100)
                self.assertEqual(
                    out["bounded_cfg_reaching_r3_candidate_classes"],
                    ["integer_load_update_base_r3"])
        # GPR stores and FPR load/store update forms write the rA base.
        for op in (37,39,45,49,51,53,55):
            with self.subTest(op=op):
                words=fixture()
                words[mod.ADDI_PC+8]=dform(op,0,3,4)
                out=mod.analyze(words.__getitem__,-100)
                self.assertEqual(
                    out["bounded_cfg_reaching_r3_candidate_classes"],
                    ["memory_update_base_r3"])

    def test_plain_memory_stores_and_fpr_ops_do_not_write_gpr_r3(self):
        for op in (36,38,44,47,48,50,52,54):
            with self.subTest(op=op):
                words=fixture()
                words[mod.ADDI_PC+8]=dform(op,3,4,0)
                out=mod.analyze(words.__getitem__,-100)
                self.assertEqual(
                    out["bounded_cfg_reaching_r3_candidate_classes"],
                    ["addi_literal_nonzero"])
                self.assertFalse(out["store_runtime_execution_verified"])

    def test_wrong_stw_or_addi_refuses(self):
        words=fixture()
        words[mod.STORE_PC]=dform(36,3,12,-100)
        with self.assertRaises(ValueError): mod.analyze(words.__getitem__,-100)
        words=fixture()
        words[mod.ADDI_PC]=dform(32,3,0,1)
        with self.assertRaises(ValueError): mod.analyze(words.__getitem__,-100)

    def test_invalid_displacement_refuses(self):
        words=fixture()
        for val in (-32769,32768,3.2,None):
            with self.subTest(val=val),self.assertRaises(ValueError):
                mod.analyze(words.__getitem__,val)

    def test_branch_target_does_not_export_guest_addresses_or_private(self):
        words=fixture()
        words[mod.START+4]=bc(mod.START+4,mod.STORE_PC+4)
        out=mod.analyze(words.__getitem__,-100)
        data=json.dumps(out)
        self.assertNotIn("8029A0",data)
        self.assertNotIn("0x900",data)
        self.assertNotIn("sha256",data)
        self.assertTrue(out["external_entries_to_window_not_excluded"])
        self.assertFalse(out["model_training_approved"])

    def test_loop_bounded(self):
        words=fixture()
        words[mod.START+4]=bc(mod.START+4,mod.START)
        out=mod.analyze(words.__getitem__,-100)
        self.assertTrue(out["bounded_cfg_paths_reach_store"])

    def test_source_static_module_does_not_run_dolphin(self):
        words=fixture()
        out=mod.analyze(words.__getitem__,-100)
        self.assertFalse(out["store_runtime_execution_verified"])
        self.assertFalse(out["physical_ball_position_verified"])


if __name__=="__main__":
    unittest.main()
