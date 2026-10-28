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
