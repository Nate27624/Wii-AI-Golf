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
        source0=0x802A2880
        source1=0x802A2A50
        code[source0]=0x7C7D1B78
        code[source1]=0x7C7D1B78
        out=manager.summarize(lambda pc:code.get(pc,0))
        self.assertEqual(out["checked_direct_calls"],2)
        self.assertEqual(len(out["caller_chains"]),2)
        self.assertEqual(out["caller_chains"][0]["nearest_r29_definitions"][-1]["pc"],
                         f"0x{source0:08X}")
        self.assertEqual(out["caller_chains"][1]["nearest_r29_definitions"][-1]["pc"],
                         f"0x{source1:08X}")
        self.assertFalse(out["manager_this_register_proven"])
        self.assertFalse(out["dynamic_execution_proven"])
        self.assertFalse(out["training_allowed"])
        self.assertFalse(out["absolute_shot_heading_verified"])

    def test_refuse_corrupt_caller_or_nonword(self):
        code=synthetic_code()
        code[0x802A293C]^=1
        with self.assertRaises(ValueError):
            manager.summarize(lambda pc:code.get(pc,0))
        for bad in (-1,2**32,"word",None):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                manager.r29_candidate(bad)

if __name__=="__main__":
    unittest.main()
