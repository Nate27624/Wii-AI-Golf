"""Fabricated-only PPC ABI and strict Golf lookup-message fallthrough tests."""
from __future__ import annotations
from pathlib import Path
import json
import subprocess
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_p0_golf_message_arg_pairs_private as a

UNIT="Pack/RPSports/RPGolScene/RPGolScene_unsplit.o"
START=0x802A79F8
FIND=0x80196280
MSG=0x80199148
TEXT=0x8019931C

def branch(pc,dest,link=True):
    delta=dest-pc
    if delta%4 or not -(1<<25)<=delta<(1<<25):
        raise ValueError("fixture branch out of range")
    return (18<<26)|(delta&0x03FFFFFC)|int(link)

def li(reg,number): return (14<<26)|(reg<<21)|(number&65535)

def addi(reg,base,value=0): return (14<<26)|(reg<<21)|(base<<16)|(value&65535)

def lwz(reg,base,disp=0): return (32<<26)|(reg<<21)|(base<<16)|(disp&65535)

def mr(rd,rs): return (31<<26)|(rs<<21)|(rd<<16)|(rs<<11)|(444<<1)

def fixture(lookup=0x20,sink=0x38,method=MSG,extra=()):
    words={lookup:branch(START+lookup,FIND),
           sink:branch(START+sink,method)}
    words.update(dict(extra))
    content=bytearray(b"\x60\x00\x00\x00"*160)
    for off,word in words.items():
        content[off:off+4]=word.to_bytes(4,"big")
    return bytes(content)

def scan(data):
    return a.extract_pairs(data,START,UNIT)

class GolfUIMessagePairTests(unittest.TestCase):
    def test_tight_lookup_then_one_message_arg(self):
        counts=scan(fixture(extra=((0x2C,li(7,1)),
                                   (0x30,lwz(8,28,0x10)))))
        self.assertEqual(counts[:2],(1,1))
        self.assertEqual(len(counts[2]),1)
        row=counts[2][0]
        self.assertTrue(row["linear_receiver_return_candidate"])
        self.assertEqual(row["argc_post_lookup_last_assignment_class"],"one")
        self.assertEqual(row["first_argument_post_lookup_source_class"],
                         "source_memory_load")
        self.assertFalse(row["pane_identity_or_result_ui_verified"])

    def test_lookup_then_zero_args_is_label_candidate(self):
        row=scan(fixture(extra=((0x30,li(7,0)),)))[2][0]
        self.assertEqual(row["argc_post_lookup_last_assignment_class"],"zero")
        self.assertFalse(row["formatting_numeric_value_verified"])

    def test_lookup_then_multiple_args(self):
        row=scan(fixture(extra=((0x30,li(7,3)),)))[2][0]
        self.assertEqual(row["argc_post_lookup_last_assignment_class"],
                         "small_positive")

    def test_sprintf_not_an_ui_method(self):
        code=fixture(method=0x800B75D8)
        x=scan(code)
        self.assertEqual(x[0],1)
        self.assertEqual(x[1],0)
        self.assertEqual(x[2],[])

    def test_settext_has_r5_argcount_and_r6_value(self):
        row=scan(fixture(method=TEXT,
            extra=((0x2C,li(5,1)),(0x30,mr(6,28)))))[2][0]
        self.assertEqual(row["method_kind"],"set_text")
        self.assertEqual(row["argc_post_lookup_last_assignment_class"],"one")
        self.assertEqual(row["first_argument_post_lookup_source_class"],
                         "mr_from_nonvolatile_or_other_register")

    def test_intervening_branch_is_barrier(self):
        result=scan(fixture(extra=((0x30,branch(START+0x30,
                                              START+0x34,False)),)))
        self.assertEqual(result[2],[])

    def test_intervening_call_is_barrier(self):
        result=scan(fixture(extra=((0x30,branch(START+0x30,
                                              0x8029CCBC,True)),)))
        self.assertEqual(result[2],[])

    def test_r3_write_makes_receiver_unverified(self):
        row=scan(fixture(extra=((0x2C,addi(3,31,0)),)))[2][0]
        self.assertTrue(row["receiver_r3_possible_clobber"])
        self.assertFalse(row["linear_receiver_return_candidate"])

    def test_r3_lmw_ambiguity_detected(self):
        lmw=(46<<26)|(3<<21)|(1<<16)|0x40
        row=scan(fixture(extra=((0x30,lmw),)))[2][0]
        self.assertTrue(row["receiver_r3_possible_clobber"])

    def test_source_count_unknown_if_r7_comes_from_before_lookup(self):
        row=scan(fixture(extra=((0x10,li(7,1)),)))[2][0]
        self.assertEqual(row["argc_post_lookup_last_assignment_class"],
                         "unresolved")

    def test_no_pair_outside_0x40(self):
        self.assertEqual(scan(fixture(lookup=0x20,sink=0x68))[2],[])

    def test_closest_lookup_preferred(self):
        code=bytearray(fixture())
        code[0x28:0x2C]=branch(START+0x28,FIND).to_bytes(4,"big")
        counts=scan(bytes(code))
        self.assertEqual(len(counts[2]),1)
        self.assertEqual(counts[2][0]["lookup_offset"],"+0x00028")

    def test_same_unit_only_no_fake_cross_unit_pairs(self):
        code=fixture()
        s=a.summarize(*((1,1,[]) if not scan(code)[2] else (1,1,scan(code)[2])))
        self.assertFalse(s["hitting_green_result_display_and_message_ids_verified"])

    def test_safety_summary_no_private_bytes_or_proof(self):
        look,sinks,rows=scan(fixture(extra=((0x2C,li(7,1)),)))
        report=a.summarize(look,sinks,rows)
        text=json.dumps(report)
        self.assertNotIn("0x80199148",text)
        self.assertNotIn("0x804",text)
        self.assertNotIn("B0-MEM1.bin",text)
        self.assertFalse(report["typed_numeric_value_source_or_units_verified"])
        self.assertFalse(report["training_approved"])

    def test_invalid_sport_or_malformed_instruction_abstains(self):
        with self.assertRaises(a.base.UntrustedInput):
            a.extract_pairs(fixture(),START,"Pack/RPSports/RPBoxScene/foo.o")
        with self.assertRaises(a.base.UntrustedInput):
            a.extract_pairs(b"abc",START,UNIT)

    def test_cli_help_native_free(self):
        p=Path(a.__file__).resolve()
        r=subprocess.run([sys.executable,"-I",str(p),"--help"],
                         cwd=p.parents[2],capture_output=True,text=True,timeout=12)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn("--baseline",r.stdout)

if __name__=="__main__":unittest.main()
