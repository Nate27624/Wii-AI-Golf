"""Only synthetic published-PPC shape tests; zero native bytes/Dolphin."""
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
import audit_p0_field_pin_start_store_provenance_private as m


def fake_unit():
    bits=bytearray(m.UNIT_HI-m.UNIT_LO)
    for pc,disp in m.GETTERS:
        word=(32<<26)|(3<<21)|(3<<16)|disp
        struct.pack_into(">I",bits,pc-m.UNIT_LO,word)
    for offset,disp,val,base in m.CANDIDATES:
        word=(36<<26)|(val<<21)|(base<<16)|disp
        struct.pack_into(">I",bits,offset,word)
    return bits


class SourceTests(unittest.TestCase):
    def test_strict_six_source_stores(self):
        b=bytes(fake_unit())
        self.assertEqual(m.verify_source(b,b),b)
        self.assertEqual(m.report(b)["candidate_site_count"],6)
        self.assertFalse(m.report(b)["pin_object_lifecycle_explained"])

    def test_no_raw_words_paths_hashes_in_report(self):
        b=bytes(fake_unit())
        s=json.dumps(m.report(b),sort_keys=True)
        for forbidden in ("0x80293810","0x90001111","B0-MEM1.bin",
                          "sha256","raw_word","user\\Dump"):
            self.assertNotIn(forbidden,s)
        self.assertFalse(m.report(b)["dynamic_ball_xyz_verified"])
        self.assertFalse(m.report(b)["training_approved"])

    def test_wrong_source_bytes_or_getter_fail_closed(self):
        b=fake_unit()
        c=bytearray(b)
        c[0x2CCC+3] ^= 1
        with self.assertRaises(ValueError):
            m.verify_source(bytes(b),bytes(c))
        c=bytearray(b)
        c[m.GETTERS[0][0]-m.UNIT_LO]^=1
        with self.assertRaises(ValueError):
            m.verify_source(bytes(c),bytes(c))

    def test_changed_candidate_register_or_immediate_fail_closed(self):
        for offset,_,_,_ in m.CANDIDATES:
            b=fake_unit()
            b[offset+1] ^= 4
            with self.subTest(offset=offset),self.assertRaises(ValueError):
                m.verify_source(bytes(b),bytes(b))

    def test_unaligned_source_or_not_in_public_text_refused(self):
        for off in (-4,1,len(fake_unit()),len(fake_unit())-1):
            with self.subTest(off=off),self.assertRaises(ValueError):
                m.instr_u32(fake_unit(),off)
        for addr in (m.UNIT_LO-4,m.UNIT_HI,m.UNIT_LO+1):
            with self.assertRaises(ValueError):
                m.source_offset(addr)

    def test_lwz_and_stw_operand_order(self):
        stw=(36<<26)|(5<<21)|(3<<16)|0x50
        self.assertEqual(m.store_fields(stw),(0x50,5,3))
        self.assertEqual(m.decode(stw)["kind"],"stw r5, signed_offset(r3)")
        self.assertIsNone(m.decode(stw)["defines"])
        lwz=(32<<26)|(31<<21)|(3<<16)|0x44
        self.assertEqual(m.decode(lwz)["defines"],31)

    def test_r31_mr_source_register_provenance(self):
        b=fake_unit()
        offset=0x2EA8
        # mr r31,r3 is alias of or r31,r3,r3 (PPC x-form)
        word=(31<<26)|(3<<21)|(31<<16)|(3<<11)|(444<<1)
        struct.pack_into(">I",b,offset-8,word)
        p=m.prior_definition(bytes(b),offset,31)
        self.assertTrue(p["nearest_linear_definition_found"])
        self.assertEqual(p["source_relative_pc"],"+0x2EA0")
        self.assertEqual(p["operation"],"mr r31, r3")
        self.assertTrue(p["not_proven_register_receiver_identity"])

    def test_prior_definition_with_branch_cannot_prove_receiver(self):
        b=fake_unit()
        off=0x2CCC
        struct.pack_into(">I",b,off-8,(14<<26)|(3<<21)|(29<<16)|0x20)
        struct.pack_into(">I",b,off-4,(16<<26))
        p=m.prior_definition(bytes(b),off,3)
        self.assertEqual(p["source_relative_pc"],"+0x2CC4")
        self.assertTrue(p["bounded_window_crosses_branch"])
        self.assertTrue(p["not_proven_register_receiver_identity"])

    def test_no_prior_def_is_explicitly_unknown(self):
        b=bytes(fake_unit())
        p=m.prior_definition(b,0x2CCC,3)
        self.assertFalse(p["nearest_linear_definition_found"])
        self.assertTrue(p["not_proven_register_receiver_identity"])

    def test_bounded_context_is_source_relative_only(self):
        r=m.report(bytes(fake_unit()))
        pcs=[x["source_relative_pc"] for x in r["bounded_context_rows"]]
        self.assertIn("+0x2CCC",pcs)
        self.assertIn("+0x2EF4",pcs)
        self.assertEqual(len(pcs),len(set(pcs)))
        self.assertLessEqual(len(pcs),100)

    def test_gate_failure_stops_before_reading_private_banks(self):
        with patch.object(m.audit,"run_local",side_effect=ValueError("bad SHA")):
            with self.assertRaises(ValueError):
                m.run_local(Path("SECRET-PRIVATE"),Path("SECRET-OTHER"))

    def test_python_isolated_help_launch(self):
        program=ROOT/"scripts"/"audit_p0_field_pin_start_store_provenance_private.py"
        run=subprocess.run([sys.executable,"-I",str(program),"--help"],
                           capture_output=True,text=True,cwd=ROOT,timeout=20)
        self.assertEqual(run.returncode,0,msg=run.stderr)
        self.assertIn("--baseline",run.stdout)
        self.assertIn("--flight",run.stdout)
        self.assertNotIn("ModuleNotFoundError",run.stderr)


if __name__=="__main__":
    unittest.main()
