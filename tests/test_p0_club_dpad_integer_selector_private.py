"""Source-bounded synthetic tests for D-pad-shaped club integer selectors."""
import importlib.util
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
P=ROOT/"scripts"/"audit_p0_club_dpad_integer_selector_private.py"
spec=importlib.util.spec_from_file_location("club_dpad_scan",P)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

START=0x802B4794
UNIT="Pack/RPSports/RPGolScene/RPGolScene_unsplit.o"
U={UNIT:(START,START+0x800)}

def encode(op,reg=3,base=3,imm=0):
    return (op<<26)|(reg<<21)|(base<<16)|(imm & 0xffff)

def rlwinm(rs,ra,sh,mb,me,rc=1):
    return (21<<26)|(rs<<21)|(ra<<16)|(sh<<11)|(mb<<6)|(me<<1)|rc

def make(words,start=START):
    data=bytearray(start-m.source.MEM1+len(words)*4)
    struct.pack_into(">"+("I"*len(words)),data,start-m.source.MEM1,*words)
    return data,(start,start+len(words)*4,"synthetic",UNIT)

class TestDpadSelectorStatic(unittest.TestCase):
    def test_public_wii_direction_bits(self):
        self.assertEqual((m.UP,m.DOWN),(0x8,0x4))
        self.assertEqual(m.rotate_mask(28,28),0x8)
        self.assertEqual(m.rotate_mask(29,29),0x4)
        self.assertEqual(m.rotate_mask(28,29),0xC)
        self.assertEqual(m.rotate_mask(30,2),0xc0000003)

    def test_andi_mask_pair_with_step_and_integer_store(self):
        words=[encode(28,imm=8),
               encode(14,3,3,1),
               encode(36,3,30,0x28),
               encode(28,imm=4),
               encode(14,3,3,-1)]
        data,f=make(words)
        r=m.collect_function(data,f,U)
        self.assertTrue(r["has_both_up_and_down_bit_shapes"])
        self.assertEqual(len(r["nearby_ordinal_steps"]),2)
        self.assertEqual(r["nearby_nonstack_integer_stores"][0]
                         ["candidate_field_displacement"],"+0x028")
        self.assertFalse(r["club_selector_source_verified"])

    def test_rlwinm_exact_bit_test_no_rotation(self):
        w=rlwinm(3,3,0,28,28)
        self.assertEqual(m.immediate_button_test(w)["bits"],8)
        w2=rlwinm(3,3,0,29,29)
        self.assertEqual(m.immediate_button_test(w2)["bits"],4)
        self.assertIsNone(m.immediate_button_test(rlwinm(3,3,2,28,28)))

    def test_a_button_and_unrelated_mask_not_dpad(self):
        self.assertIsNone(m.immediate_button_test(encode(28,imm=0x800)))
        self.assertIsNone(m.immediate_button_test(encode(29,imm=0x800)))
        self.assertIsNone(m.immediate_button_test(encode(28,imm=0x20)))

    def test_immediate_load_not_counted_as_increment(self):
        self.assertIsNone(m.ordinal_step(encode(14,3,0,1)))
        self.assertEqual(m.ordinal_step(encode(14,3,3,-1))["step"],-1)

    def test_single_direction_kept_as_possible_split_handler(self):
        data,f=make([encode(28,imm=8),encode(38,3,31,0x35)])
        r=m.collect_function(data,f,U)
        self.assertFalse(r["has_both_up_and_down_bit_shapes"])
        self.assertFalse(r["stored_object_receiver_proven"])

    def test_stack_only_write_not_candidate(self):
        data,f=make([encode(28,imm=8),encode(36,3,1,0x30)])
        r=m.collect_function(data,f,U)
        self.assertFalse(r["nearby_nonstack_integer_stores"])

    def test_deterministic_ordering_and_no_training_claim(self):
        up=[encode(28,imm=8),encode(14,3,3,1),encode(36,3,30,0x30)]
        down=[encode(28,imm=4),encode(14,3,3,-1),encode(36,3,30,0x30)]
        words=up+down
        data,f=make(words)
        result=m.analyze_bank(data,[f],U)
        self.assertEqual(result["functions_with_both_up_down_shapes"],1)
        self.assertFalse(result["selected_club_field_verified"])
        self.assertFalse(result["training_approved"])

    def test_bad_source_scope_abstain(self):
        data,f=make([encode(28,imm=8)])
        with self.assertRaises(m.source.Abstain):
            m.analyze_bank(data,[(START,START+40,"bad",UNIT)],U)

    def test_original_public_function_map_qualifies(self):
        funcs=m.graph.parse_public_functions(
            json.loads(m.graph.FUNCS.read_text("utf-8")),
            m.source.source_units(json.loads(m.source.INDEX.read_text("utf-8"))))
        self.assertGreaterEqual(len(funcs),1300)
        self.assertTrue(any("Scene_unsplit.o" in f[3] for f in funcs))

if __name__=="__main__":
    unittest.main()
