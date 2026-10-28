"""Synthetic-only regression for selected-record source caller signatures."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_golf_selected_aim_callers_private as audit

def synthetic_code():
    words={
        audit.CALLEE_TRANSFER_PC:audit.CALLEE_TRANSFER_WORD,
        0x802A2940:0xC022C8A0,
        0x802A2944:0xC0030074,
        0x802A2948:0xFC010000,
        0x802A294C:0x7C000026,
        0x802A2950:0x54001FFE,
        0x802A2954:0x68000001,
        0x802A2958:0x2C000000,
        0x802A295C:0x408200FC,
        0x802A2960:0x7F84E378,
        0x802A2964:0x7F65DB78,
        0x802A2B04:0x7F84E378,
        0x802A2B08:0x7F65DB78,
    }
    for load_pc,load_word,call_pc,call_word in audit.CALLS:
        words[load_pc]=load_word
        words[call_pc]=call_word
    return words

class CallerSignatureTests(unittest.TestCase):
    def test_exact_two_direct_calls_and_conservative_semantics(self):
        words=synthetic_code()
        x=audit.check_source(words.__getitem__)
        self.assertEqual(x["source_direct_calls_verified"],2)
        self.assertTrue(x["callee_preserves_argument_r3_in_r29"])
        self.assertFalse(x["manager_r29_runtime_identity_independently_verified"])
        self.assertFalse(x["selected_player_pointer_source_contract_verified"])
        self.assertFalse(x["actual_shot_heading_verified"])
        self.assertFalse(x["training_allowed"])
        for c in x["call_sites"]:
            self.assertTrue(c["argument_r3_loaded_from_r29_plus_0x334"])
            self.assertTrue(c["r3_preserved_to_direct_call_on_checked_path"])

    def test_corrupt_load_call_intermediate_and_callee_fail_closed(self):
        for pc in (
            audit.CALLEE_TRANSFER_PC,0x802A293C,0x802A2944,
            0x802A2960,0x802A2968,0x802A2B00,0x802A2B08,0x802A2B0C
        ):
            words=synthetic_code()
            words[pc]^=1
            with self.subTest(pc=hex(pc)),self.assertRaises(ValueError):
                audit.check_source(words.__getitem__)

    def test_direct_bl_decode(self):
        for _,_,pc,word in audit.CALLS:
            self.assertEqual(audit.decode_bl_target(word,pc),audit.CALLEE)
        self.assertIsNone(audit.decode_bl_target(0x807D0334,0x802A293C))
        self.assertIsNone(audit.decode_bl_target(0x4BFFC3C4,0x802A2968))
        for v in (-1,2**32,"bad",None):
            with self.subTest(v=v),self.assertRaises(ValueError):
                audit.decode_bl_target(v,0x802A2968)

if __name__=="__main__":
    unittest.main()
