"""Synthetic tests of source-backed PPC function/caller graph, no native archive."""
import importlib.util
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
P=ROOT/"scripts"/"audit_p0_club_controller_callgraph_private.py"
spec=importlib.util.spec_from_file_location("p0clubgraph",P)
x=importlib.util.module_from_spec(spec)
spec.loader.exec_module(x)

BASE=0x8029E62C
CTRL=0x8019B214
U={x.PLAYER:(BASE,BASE+0x1000),
   "Pack/RPKernel/RPSysController.cpp":(CTRL,CTRL+0x200)}
F=[(CTRL,CTRL+0x20,"get_controller","Pack/RPKernel/RPSysController.cpp"),
   (BASE,BASE+0x10,"f1",x.PLAYER),
   (BASE+0x10,BASE+0x20,"f2",x.PLAYER)]

def d(op,rs=3,ra=3,imm=0):
    return (op<<26)|(rs<<21)|(ra<<16)|(imm & 65535)

def call(src,dst):
    displacement=dst-src
    assert displacement % 4==0 and -(1<<25)<=displacement<(1<<25)
    return (18<<26)|(displacement & 0x03fffffc)|1

def records_for_two_funcs(include_controller=True):
    code1=struct.pack(">4I",d(14,3,0,1),d(38,3,31,0x34),
                        d(38,0,31,0x35),call(BASE+12,BASE+16))
    code2=struct.pack(">4I",call(BASE+16,CTRL) if include_controller else 0x60000000,
                        d(11,3,0,3),d(38,3,31,0x30),0x4e800020)
    mem=bytearray(BASE-x.base.MEM1+32)
    pos=BASE-x.base.MEM1
    mem[pos:pos+16]=code1
    mem[pos+16:pos+32]=code2
    return x.static_instruction_records(mem,U,[z for z in F if z[3]==x.PLAYER])

class TestClubFunctionGraph(unittest.TestCase):
    def test_public_function_index_is_available_and_qualified(self):
        payload=json.loads(x.FUNCS.read_text("utf-8"))
        units=x.base.source_units(json.loads(x.base.INDEX.read_text("utf-8")))
        f=x.parse_public_functions(payload,units)
        self.assertGreaterEqual(len(f),400)
        p=x.function_at(0x8029E62C,f)
        self.assertIsNotNone(p)
        self.assertEqual(p[0],0x8029E62C)
        self.assertEqual(p[3],x.PLAYER)

    def test_public_index_tampering_rejected(self):
        payload=json.loads(x.FUNCS.read_text("utf-8"))
        units=x.base.source_units(json.loads(x.base.INDEX.read_text("utf-8")))
        payload["upstream_git_blob_sha"]="unverified"
        with self.assertRaises(x.base.Abstain):
            x.parse_public_functions(payload,units)

    def test_index_out_of_bound_rejected(self):
        payload=json.loads(x.FUNCS.read_text("utf-8"))
        units=x.base.source_units(json.loads(x.base.INDEX.read_text("utf-8")))
        payload["functions"][0][1]=0x900000
        with self.assertRaises(x.base.Abstain):
            x.parse_public_functions(payload,units)

    def test_function_interior_lookup_uses_bounded_function(self):
        self.assertEqual(x.function_at(BASE+12,F)[2],"f1")
        self.assertEqual(x.function_at(BASE+16,F)[2],"f2")
        self.assertIsNone(x.function_at(BASE+32,F))
        self.assertIsNone(x.function_at(BASE-4,F))

    def test_controller_call_and_static_upstream(self):
        report=x.analyze(records_for_two_funcs(),F,U,limit=5)
        self.assertEqual(report["direct_golf_to_input_unit_calls"],1)
        self.assertEqual(report["static_direct_calls_from_golf"],2)
        self.assertEqual(report["golf_to_input_callsite_examples"][0]
                         ["destination_source"],
                         "Pack/RPKernel/RPSysController.cpp")
        anchor=report["player_34_writer_function_anchors"][0]
        self.assertTrue(anchor["source_pair_plus_35_nearby"])
        self.assertFalse(anchor["selected_player_receiver_proven"])
        self.assertFalse(report["game_executed_function_verified"])

    def test_nonlink_branch_is_not_call(self):
        u={x.PLAYER:(BASE,BASE+16)}
        f=[(BASE,BASE+16,"f1",x.PLAYER)]
        blob=struct.pack(">4I",0x48000008,d(38,3,31,0x34),
                            d(38,3,31,0x35),0x4e800020)
        mem=bytearray(BASE-x.base.MEM1+16)
        mem[BASE-x.base.MEM1:]=blob
        r=x.static_instruction_records(mem,u,f)
        self.assertEqual(r[0]["calls"],[])
        report=x.analyze(r,f,u)
        self.assertEqual(report["static_direct_calls_from_golf"],0)

    def test_direct_edge_missing_controller_no_claim(self):
        report=x.analyze(records_for_two_funcs(False),F,U,limit=5)
        self.assertEqual(report["direct_golf_to_input_unit_calls"],0)
        self.assertTrue(report["direct_calls_miss_indirect_dispatch"])

    def test_no_spurious_cross_function_flag_pair(self):
        fake=[{"start":BASE,"end":BASE+4,"owner":x.PLAYER,
               "name":"a","calls":[],"small_comparisons":0,
               "bit_tests":0,"branches":0,
               "stores":[(BASE,{"op":"stb","base":3,"reg":4,"disp":0x34})]},
              {"start":BASE+4,"end":BASE+8,"owner":x.PLAYER,
               "name":"b","calls":[],"small_comparisons":0,
               "bit_tests":0,"branches":0,
               "stores":[(BASE+4,{"op":"stb","base":3,"reg":0,"disp":0x35})]}]
        f=[(BASE,BASE+4,"a",x.PLAYER),(BASE+4,BASE+8,"b",x.PLAYER)]
        r=x.analyze(fake,f,U)
        self.assertFalse(r["player_34_writer_function_anchors"][0]
                         ["source_pair_plus_35_nearby"])


    def test_focused_digest_resolves_public_callee(self):
        report=x.analyze(records_for_two_funcs(),F,U,limit=15)
        digest=x.focused_input_digest(report)
        self.assertEqual(digest["direct_input_source_calls"],1)
        self.assertEqual(digest["resolved_input_calls"][0]
                         ["callee_public_function"],"get_controller")
        self.assertEqual(digest["resolved_input_calls"][0]
                         ["caller_public_function"],"f2")
        self.assertFalse(digest["club_id_field_verified"])
        self.assertFalse(digest["training_approved"])

    def test_public_real_egg_and_wpad_function_ranges(self):
        payload=json.loads(x.FUNCS.read_text("utf-8"))
        units=x.base.source_units(json.loads(x.base.INDEX.read_text("utf-8")))
        functions=x.parse_public_functions(payload,units)
        self.assertGreaterEqual(len(functions),1300)
        named=[f[2] for f in functions]
        self.assertTrue(any("getFSStickButton" in name for name in named))
        self.assertTrue(any("WPAD" in name for name in named))
        self.assertTrue(any(0x802A79F8 <= f[0] < 0x802C7924 for f in functions))

    def test_bad_report_limit_refused(self):
        with self.assertRaises(x.base.Abstain):
            x.analyze([],[],U,limit=0)

    def test_no_private_native_words_in_report(self):
        result=x.analyze(records_for_two_funcs(),F,U)
        self.assertNotIn("raw",json.dumps(result))
        self.assertFalse(result["selected_club_variable_verified"])
        self.assertFalse(result["training_approved"])

if __name__=="__main__":
    unittest.main()
