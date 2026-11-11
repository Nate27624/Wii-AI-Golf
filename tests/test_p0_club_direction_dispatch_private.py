"""Synthetic exact-public-function Up/Down shared dispatch tests."""
import importlib.util
from pathlib import Path
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
P=ROOT/"scripts"/"audit_p0_club_direction_dispatch_private.py"
spec=importlib.util.spec_from_file_location("club_dispatch",P)
x=importlib.util.module_from_spec(spec)
spec.loader.exec_module(x)

PC=x.DISPATCH
OWNER="Pack/RPSports/RPGolScene/RPGolScene_unsplit.o"
U={OWNER:(PC,PC+0x4000)}
def op(p,rt=3,ra=3,imm=0):
    return (p<<26)|(rt<<21)|(ra<<16)|(imm&0xffff)
def synthetic(*w):
    f=(PC,PC+4*len(w),"f_test",OWNER)
    return struct.pack(">"+("I"*len(w)),*w),f

class TestSourceDirectionDispatch(unittest.TestCase):
    def test_compare_direction_argument_immediate(self):
        code,f=synthetic(op(11,4,4,1),0x4e800020)
        result=x.audit_function(code,f,[f],U,30)
        self.assertEqual(result["r4_uses_are_syntactic_only"][0]["immediate"],1)
        self.assertFalse(result["dpad_to_selected_club_value_proven"])

    def test_nonstack_store_displacement_not_semantics(self):
        code,f=synthetic(op(11,4,4,0),op(36,3,29,0x340),0x4e800020)
        r=x.audit_function(code,f,[f],U,30)
        self.assertEqual(r["nonstack_store_sites"][0]["field_displacement"],0x340)
        self.assertFalse(r["nonstack_store_sites"][0]["selected_club_owner_verified"])

    def test_stack_store_excluded(self):
        code,f=synthetic(op(36,3,1,0x20),op(11,4,4,0))
        self.assertEqual(x.audit_function(code,f,[f],U,30)["nonstack_store_count"],0)

    def test_callee_public_symbol_provided(self):
        to=PC+0x2000
        lo=PC
        branch=(18<<26)|((to-lo)&0x03fffffc)|1
        code,f=synthetic(branch,0x4e800020)
        callee=(to,to+16,"callee_synthetic",OWNER)
        r=x.audit_function(code,f,[f,callee],U,30)
        self.assertEqual(r["direct_calls"][0]["callee_public_name"],"callee_synthetic")
        self.assertFalse(r["direct_calls"][0]["argument_proven_interprocedural"])

    def test_outside_function_bytes_abstain(self):
        code,f=synthetic(op(11,4,4,1))
        with self.assertRaises(x.source.Abstain):
            x.audit_function(code[:-1],f,[f],U,30)

    def test_small_report_limit_abstain(self):
        code,f=synthetic(op(11,4,4,1))
        with self.assertRaises(x.source.Abstain):
            x.audit_function(code,f,[f],U,20)

    def test_source_approved_function_starts_exist(self):
        import json
        spans=x.source.source_units(json.loads(x.source.INDEX.read_text("utf-8")))
        funcs=x.graph.parse_public_functions(
            json.loads(x.graph.FUNCS.read_text("utf-8")),spans)
        for name,pc in x.PUBLIC_TARGETS.items():
            f=x.graph.function_at(pc,funcs)
            self.assertIsNotNone(f,name)
            self.assertEqual(f[0],pc)
            self.assertTrue(f[3].startswith(x.graph.GOLF_PREFIX))

    def test_manager_direction_argument_not_deduced_from_callee(self):
        code,f=synthetic(op(11,4,4,1))
        r=x.audit_function(code,f,[f],U,30)
        self.assertFalse(r["selected_club_field_verified"])
        self.assertTrue(r["indirect_dispatch_and_register_provenance_unresolved"])
        self.assertFalse(r["training_approved"])

if __name__=="__main__":
    unittest.main()
