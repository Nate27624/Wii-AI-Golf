"""Native-free PPC source-global direct xref tests. No game memory required."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_p0_global_ball_source_xrefs_private as mod


def ins(op,rt=3,ra=13,imm=-100):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&0xffff)


class SourceGlobalXrefsTests(unittest.TestCase):
    def setUp(self):
        self.words={mod.prev.GLOBAL_LOAD_PC:ins(32)}
        self.reader=lambda pc:self.words.get(pc,0x60000000)

    def test_known_global_load_only(self):
        result=mod.classify_source_refs(self.reader,-100)
        self.assertTrue(result["known_global_ball_load_instruction_confirmed"])
        self.assertEqual(result["global_slot_direct_r13_reference_counts"]["direct_lwz_read"],1)
        self.assertEqual(result["global_slot_direct_r13_reference_counts"]["direct_stw_write"],0)
        self.assertFalse(result["source_slot_direct_writer_identified_in_these_units"])
        self.assertTrue(result["no_direct_store_cannot_disprove_indirect_writer"])

    def test_direct_store_distinguished_from_read(self):
        self.words[0x8029B250]=ins(36,4)
        result=mod.classify_source_refs(self.reader,-100)
        self.assertTrue(result["source_slot_direct_writer_identified_in_these_units"])
        self.assertEqual(result["global_slot_direct_r13_reference_counts"]["direct_stw_write"],1)
        self.assertEqual(result["global_slot_direct_r13_reference_counts"]["direct_lwz_read"],1)
        self.assertIn({"source_unit":"RPGolSimulateManager","unit_relative_pc":"+0x0010",
                       "source_access_type":"direct_stw_write"},
                      result["source_global_r13_reference_sites"])

    def test_wrong_offset_and_register_not_a_match(self):
        self.words[0x8029B250]=ins(36,3,13,-99)
        self.words[0x8029B254]=ins(36,3,12,-100)
        result=mod.classify_source_refs(self.reader,-100)
        self.assertEqual(result["global_slot_direct_r13_reference_counts"]["direct_stw_write"],0)

    def test_update_store_class_distinct(self):
        self.words[0x8029B250]=ins(37,3)
        result=mod.classify_source_refs(self.reader,-100)
        self.assertEqual(result["global_slot_direct_r13_reference_counts"]["direct_stwu_write_update"],1)

    def test_address_formation_not_identified_as_store(self):
        self.words[0x8029B250]=ins(14,3)
        result=mod.classify_source_refs(self.reader,-100)
        self.assertEqual(result["global_slot_direct_r13_reference_counts"]["addi_address_formation"],1)
        self.assertFalse(result["source_slot_direct_writer_identified_in_these_units"])

    def test_wrong_known_global_read_refuses(self):
        self.words[mod.prev.GLOBAL_LOAD_PC]=ins(36)
        with self.assertRaises(ValueError):
            mod.classify_source_refs(self.reader,-100)

    def test_unsigned_out_of_range_displacement_refuses(self):
        for offset in (-32769,32768,None,1.25):
            with self.subTest(offset=offset),self.assertRaises(ValueError):
                mod.classify_source_refs(self.reader,offset)

    def test_source_sites_cap_32_and_counts_complete(self):
        base=0x8029B240
        for i in range(40):
            self.words[base+4*i]=ins(36,3)
        result=mod.classify_source_refs(self.reader,-100)
        self.assertEqual(result["global_slot_direct_r13_reference_counts"]["direct_stw_write"],40)
        self.assertEqual(len(result["source_global_r13_reference_sites"]),32)
        self.assertEqual(result["more_source_sites_not_printed"],9)

    def test_output_does_not_include_raw_opcodes_or_private_pointer(self):
        self.words[0x8029B250]=ins(36,3)
        report=mod.classify_source_refs(self.reader,-100)
        txt=json.dumps(report)
        self.assertNotIn("0x906d",txt.lower())
        self.assertNotIn("private_heap",txt)
        self.assertNotIn("0x90001234",txt)
        self.assertNotIn("bank_sha",txt)
        self.assertEqual(report["source_golf_text_units_examined"],6)
        self.assertGreater(report["golf_source_code_words_examined"],10000)

    def test_isolated_cli_import(self):
        path=Path(mod.__file__)
        result=subprocess.run([sys.executable,"-I",str(path),"--help"],
                              cwd=path.parents[2],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("--dump-directory",result.stdout)


if __name__=="__main__":
    unittest.main()
