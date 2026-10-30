"""Synthetic-only PPC golf tree allocation/stride/field access audit tests."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location("tree_ppc",SCRIPTS/"p0_tree_ppc_indexing_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def dform(op,rt,ra,imm):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&65535)


def branch(pc,target,link=1):
    delta=target-pc
    if delta%4 or not -(1<<25)<=delta<(1<<25):
        raise ValueError
    return (18<<26)|(delta & 0x03FFFFFC)|(link&1)


def slwi(ra,rs,shift):
    return (21<<26)|(rs<<21)|(ra<<16)|(shift<<11)|((31-shift)<<1)


class PPCDecode(unittest.TestCase):
    def test_mulli_0x80_stride_candidate(self):
        pc=m.WINDOWS["field_pmp_processing"][0]
        x=m.decode_word(pc,dform(7,4,3,0x80),"field_pmp_processing")
        self.assertEqual(x[0][0],"mulli")
        self.assertEqual(x[0][1]["immediate"],0x80)
        self.assertEqual(x[0][1]["window_relative_offset"],"+0x0000")

    def test_mulli_negative_immediate_bounded(self):
        pc=m.WINDOWS["field_pmp_processing"][0]
        x=m.decode_word(pc,dform(7,4,3,-128),"field_pmp_processing")
        self.assertEqual(x[0][1]["immediate"],-128)

    def test_mulli_huge_immediate_suppressed(self):
        pc=m.WINDOWS["field_pmp_processing"][0]
        self.assertEqual(m.decode_word(pc,dform(7,4,3,5000),"field_pmp_processing"),[])

    def test_slwi_4_bytes(self):
        pc=m.WINDOWS["tree_object_code"][0]
        x=m.decode_word(pc,slwi(6,5,2),"tree_object_code")
        self.assertEqual(x[0][1]["multiplier_power_of_two"],4)

    def test_slwi_invalid_mask_not_promoted(self):
        pc=m.WINDOWS["tree_object_code"][0]
        self.assertEqual(m.decode_word(pc,slwi(6,5,2)|(10<<1),"tree_object_code"),[])

    def test_field_pointer_access_0x20(self):
        pc=m.WINDOWS["field_pmp_processing"][0]
        x=m.decode_word(pc,dform(32,9,31,0x20),"field_pmp_processing")
        self.assertEqual(x[0][1]["field_offset"],"+0x20")
        self.assertEqual(x[0][1]["mnemonic"],"lwz")

    def test_field_count_access_0x1c(self):
        pc=m.WINDOWS["field_pmp_processing"][0]
        x=m.decode_word(pc,dform(36,9,31,0x1c),"field_pmp_processing")
        self.assertEqual(x[0][1]["field_offset"],"+0x1C")
        self.assertEqual(x[0][1]["mnemonic"],"stw")

    def test_tree_constructor_direct_call(self):
        pc=m.WINDOWS["field_pmp_processing"][0]
        target=m.UNITS["MapObjTree"][0]+0x10
        x=m.decode_word(pc,branch(pc,target),"field_pmp_processing")
        self.assertEqual(x[0][0],"tree_call_or_jump")
        self.assertEqual(x[0][1]["target_public_unit"],"MapObjTree")
        self.assertTrue(x[0][1]["linked_call"])

    def test_out_of_unit_branch_not_as_tree(self):
        pc=m.WINDOWS["field_pmp_processing"][0]
        target=pc+0x100
        self.assertEqual(m.decode_word(pc,branch(pc,target),"field_pmp_processing"),[])

    def test_public_intervals_nonoverlap(self):
        for a,b in m.WINDOWS.values():
            self.assertLess(a,b)
            self.assertEqual(a%4,0)
            self.assertEqual(b%4,0)
        self.assertEqual(m.UNITS["MapObjTree"],(0x80296238,0x80296EA8))

    def test_summary_no_raw_instructions(self):
        scan_pc=m.WINDOWS["field_pmp_processing"][0]
        instr={
            scan_pc:dform(7,4,3,0x58),
            scan_pc+4:dform(32,9,31,0x20),
            scan_pc+8:branch(scan_pc+8,m.UNITS["MapObjTree"][0]+0x10)
        }
        summary=m.analyze_bounded_ppc(lambda addr:instr.get(addr,0))
        s=summary["field_pmp_processing"]
        self.assertEqual(s["potential_index_multiplier_counts"][0]["immediate"],0x58)
        self.assertEqual(s["tree_code_direct_branch_sites"][0]["target_public_unit"],"MapObjTree")
        self.assertEqual(s["field_offset_access_sites"][0]["field_offset"],"+0x20")
        self.assertFalse(s["object_stride_verified"])
        import json
        raw=json.dumps(summary)
        self.assertNotIn("0x80296248",raw)
        self.assertNotIn("0x9000",raw)
        self.assertNotIn("origin",raw)


if __name__=="__main__":
    unittest.main()
