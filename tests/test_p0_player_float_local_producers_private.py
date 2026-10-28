"""Fabricated ONLY PPC source bytes: six selected player-store FPR producer tests."""
from __future__ import annotations
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import audit_p0_player_float_local_producers_private as m

def w(op,rs,ra,imm):
    return (op<<26)|(rs<<21)|(ra<<16)|(imm & 0xffff)

def build():
    b=bytearray([0x60,0,0,0]*0x1000)
    for offset,disp,fs,ra in m.SITES:
        struct.pack_into(">I",b,offset,w(52,fs,ra,disp))
    return b

class SixSourceTests(unittest.TestCase):
    def test_exact_site_gates_pass_and_source_relative_only(self):
        b=bytes(build())
        self.assertTrue(m.verify_exact_sites(b))
        report=m.describe(b)
        self.assertEqual(report["site_count"],6)
        self.assertEqual(len(report["site_evidence"]),6)
        self.assertFalse(report["selected_record_receiver_identity_verified"])
        self.assertFalse(report["training_approved"])

    def test_candidate_source_site_drift_abstains_for_every_site(self):
        for offset,disp,fs,ra in m.SITES:
            b=build()
            struct.pack_into(">I",b,offset,w(52,fs,ra,disp+4))
            with self.subTest(site=offset),self.assertRaises(ValueError):
                m.verify_exact_sites(bytes(b))

    def test_nearest_fpr_load_candidate(self):
        b=build()
        off=0x1C18
        struct.pack_into(">I",b,off-8,w(48,0,31,0x48))
        report=m.describe(bytes(b))
        s=next(x for x in report["site_evidence"] if
               x["source_relative_store"]=="+0x1C18")
        self.assertEqual(s["bounded_fpr_producer_hint"]["origin_class"],"lfs")
        self.assertEqual(s["bounded_fpr_producer_hint"]["source_relative_instruction"],"+0x1C10")
        self.assertFalse(s["bounded_fpr_producer_hint"]["register_value_producer_proven"])

    def test_nearby_store_not_false_FPR_writer(self):
        b=build();off=0x1C18
        struct.pack_into(">I",b,off-4,w(52,0,31,0x44))
        p=m.nearest_fpr_clue(bytes(b),off,0)
        self.assertEqual(p["origin_class"],"no_local_FPR_producer_found")

    def test_branch_barrier_blocks_earlier_candidate(self):
        b=build();off=0x1C18
        struct.pack_into(">I",b,off-16,w(48,0,31,0x24))
        struct.pack_into(">I",b,off-8,18<<26)
        p=m.nearest_fpr_clue(bytes(b),off,0)
        self.assertEqual(p["origin_class"],"control_flow_barrier")
        self.assertFalse(p["register_value_producer_proven"])

    def test_float_compute_is_possible_not_proven(self):
        b=build();off=0x0FAC
        struct.pack_into(">I",b,off-4,(59<<26)|(0<<21)|(2<<16)|(3<<11)|(21<<1))
        p=m.nearest_fpr_clue(bytes(b),off,0)
        self.assertEqual(p["origin_class"],"fp_single_possible_writer")
        self.assertFalse(p["register_value_producer_proven"])

    def test_other_float_destination_not_same_register(self):
        b=build();off=0x0FAC
        struct.pack_into(">I",b,off-4,w(48,4,31,0x20))
        p=m.nearest_fpr_clue(bytes(b),off,0)
        self.assertEqual(p["origin_class"],"no_local_FPR_producer_found")

    def test_opaque_instruction_does_not_claim_producer(self):
        b=build();off=0x0FAC
        struct.pack_into(">I",b,off-4,0x00000000)
        p=m.nearest_fpr_clue(bytes(b),off,0)
        self.assertEqual(p["origin_class"],"no_local_FPR_producer_found")

    def test_distinct_record_and_ball_offsets_never_equated(self):
        r=m.describe(bytes(build()))
        self.assertTrue(all(x["source_unit"]=="RPGolPlayer" for x in r["site_evidence"]))
        self.assertTrue(all(not x["selected_player_record_receiver_verified"]
                            for x in r["site_evidence"]))

    def test_privacy_no_native_words_or_raw_ram_in_output(self):
        s=json.dumps(m.describe(bytes(build())))
        for forbidden in ("0x80001000","MEM1.bin","SHA256","runtime_pointer",
                          "raw_word","0xD003","private_session","ball_xyz"):
            self.assertNotIn(forbidden,s)
        self.assertFalse(m.describe(bytes(build()))["allowed_to_publish"])

    def test_bad_source_alignment_and_length_refused(self):
        with self.assertRaises(ValueError):
            m.verify_exact_sites(b"\x60\x00\x00\x00"*2)
        for i in (-4,1,len(build()),len(build())-1):
            with self.subTest(i=i),self.assertRaises(ValueError):
                m.word_at(bytes(build()),i)

    def test_sha_gate_failure_prevents_native_source_read(self):
        with patch.object(m.owner,"audit",side_effect=ValueError("bad original SHA")):
            with self.assertRaises(ValueError):
                m.audit(Path("unknown-private-session"),Path("unknown-data-root"))

    def test_python_isolated_help(self):
        script=ROOT/"scripts"/"audit_p0_player_float_local_producers_private.py"
        x=subprocess.run([sys.executable,"-I",str(script),"--help"],
                         capture_output=True,text=True,timeout=20,cwd=ROOT)
        self.assertEqual(x.returncode,0,msg=x.stderr)
        self.assertIn("--private-session",x.stdout)

if __name__=="__main__":
    unittest.main()
