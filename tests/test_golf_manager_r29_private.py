"""Synthetic tests for read-only source manager r29 provenance candidates."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"tests"))

import audit_golf_manager_r29_private as manager
from test_golf_selected_aim_callers_private import synthetic_code

class ManagerR29SourceTests(unittest.TestCase):
    def test_detect_real_ppc_r29_source_hypotheses(self):
        self.assertEqual(manager.r29_candidate(0x7C7D1B78),"mr_r29_from_r3")
        self.assertEqual(manager.r29_candidate((32<<26)|(29<<21)|(1<<16)|0xC),
                         "GPR_r29_destination_candidate")
        self.assertEqual(manager.r29_candidate(0x807D0334),None)

    def test_selected_call_chains_inspect_nearest_candidate_not_physics(self):
        code=synthetic_code()
        code[manager.METHOD_ENTRY]=manager.METHOD_PROLOGUE_WORD
        code[manager.R29_THIS_PC]=manager.R29_THIS_WORD
        code[manager.FIRST_SELECTED_READ_PC]=manager.FIRST_SELECTED_READ_WORD
        code[0x802A2880]=0x3BA00000  # older unrelated register candidate
        out=manager.summarize(lambda pc:code.get(pc,0))
        self.assertEqual(out["checked_direct_calls"],2)
        self.assertEqual(len(out["caller_chains"]),2)
        for chain in out["caller_chains"]:
            self.assertEqual(chain["nearest_r29_definitions"][-1]["pc"],
                             f"0x{manager.R29_THIS_PC:08X}")
        self.assertTrue(out["manager_this_register_proven"])
        self.assertTrue(out["manager_r29_saved_from_entry_r3_source_verified"])
        self.assertTrue(out["source_selected_pointer_read_from_manager_r29_verified"])
        self.assertTrue(out["no_recognized_r29_reassignment_before_both_calls"])
        self.assertFalse(out["r29_reassignment_detector_exhaustive"])
        self.assertFalse(out["manager_r29_runtime_identity_independently_verified"])
        self.assertFalse(out["dynamic_execution_proven"])
        self.assertFalse(out["training_allowed"])
        self.assertFalse(out["absolute_shot_heading_verified"])

    def test_refuse_corrupt_caller_or_nonword(self):
        code=synthetic_code()
        code.update({
            manager.METHOD_ENTRY:manager.METHOD_PROLOGUE_WORD,
            manager.R29_THIS_PC:manager.R29_THIS_WORD,
            manager.FIRST_SELECTED_READ_PC:manager.FIRST_SELECTED_READ_WORD,
        })
        for pc in (manager.METHOD_ENTRY, manager.R29_THIS_PC,
                   manager.FIRST_SELECTED_READ_PC, 0x802A293C):
            bad_code=dict(code)
            bad_code[pc]^=1
            with self.subTest(pc=hex(pc)),self.assertRaises(ValueError):
                manager.summarize(lambda addr:bad_code.get(addr,0))
        code[0x802A2A00]=0x3BA00000  # li r29,0 after source-this assignment
        with self.assertRaises(ValueError):
            manager.summarize(lambda addr:code.get(addr,0))
        for bad in (-1,2**32,"word",None):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                manager.r29_candidate(bad)

if __name__=="__main__":
    unittest.main()
