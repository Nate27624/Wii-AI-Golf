"""Synthetic Rev1 PPC code-range tests; no game binary in repository."""
from __future__ import annotations
import json
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from wii_ai_golf.audit.golf_cached_ppc_access import analyze_cached_ppc,UNITS,BASE

def fixture():
    b=bytearray(0x2A3600)
    b[:8]=b"RSPE01\x00\x01"
    for low,high in UNITS.values():
        for pc in range(low,high,4):
            struct.pack_into(">I",b,pc-BASE,0x60000000)
        for i in range(8):
            struct.pack_into(">I",b,low-BASE+4*i,(32<<26)|(3<<16)|0x30)
    low=UNITS["RPGolPlayer"][0]
    for i,d in enumerate((0x48,0x4C,0x50)):
        struct.pack_into(">I",b,low-BASE+(8+i)*4,
                         (52<<26)|(30<<16)|d)
    return b

class CachedPpcSourceTests(unittest.TestCase):
    def test_decode_cached_mem1_without_dol(self):
        d=analyze_cached_ppc(fixture(),strict_size=False)
        self.assertEqual(d["source_units"]["RPGolPlayer"]["aligned_instructions_checked"],3833)
        self.assertEqual(d["source_units"]["RPGolMain"]["aligned_instructions_checked"],538)
        self.assertEqual(d["source_units"]["RPGolPlayerManager"]["aligned_instructions_checked"],1236)
        self.assertEqual(d["source_units"]["RPGolPlayer"]["decoded_d_form_memory_instructions"],11)
        self.assertTrue(any(x["code_unit"]=="RPGolPlayer"
                            and x["candidate_relative_offset"]=="+0x048"
                            and x["base_register"]=="r30"
                            and x["float_stores"]==1
                            for x in d["top_candidate_operand_rows"]))
        self.assertFalse(d["actual_field_semantics_verified"])
        self.assertFalse(d["swing_power_verified"])

    def test_negative_disp_and_non_d_form_rejected(self):
        b=fixture()
        low=UNITS["RPGolPlayer"][0]
        struct.pack_into(">I",b,low-BASE+10*4,(52<<26)|(30<<16)|0xFFF8)
        d=analyze_cached_ppc(b,strict_size=False)
        self.assertFalse(any(x["candidate_relative_offset"]=="+0xFF8"
                             for x in d["top_candidate_operand_rows"]))
        struct.pack_into(">I",b,low-BASE+9*4,(31<<26)|(30<<16)|0x2E)
        d=analyze_cached_ppc(b,strict_size=False)
        self.assertFalse(any(x["candidate_relative_offset"]=="+0x04C"
                             for x in d["top_candidate_operand_rows"]))

    def test_bounded_output(self):
        d=analyze_cached_ppc(fixture(),strict_size=False,max_rows=2)
        self.assertEqual(len(d["top_candidate_operand_rows"]),2)
        self.assertEqual(d["operand_rows_omitted"],
                         d["all_candidate_operand_rows"]-2)

    def test_bad_revision_rejected(self):
        b=fixture()
        b[7]=0
        with self.assertRaises(ValueError):
            analyze_cached_ppc(b,strict_size=False)

    def test_missing_code_rejected(self):
        b=fixture()
        low,high=UNITS["RPGolPlayer"]
        b[low-BASE:high-BASE]=bytes(high-low)
        with self.assertRaises(ValueError):
            analyze_cached_ppc(b,strict_size=False)

    def test_requires_native_size(self):
        with self.assertRaises(ValueError):
            analyze_cached_ppc(fixture())

    def test_private_instruction_words_never_exported(self):
        result=json.dumps(analyze_cached_ppc(fixture(),strict_size=False))
        for word in ("60000000","80630030","Dolphin Emulator",
                     "bytes_hex","0x90002000","raw_instruction_word"):
            self.assertNotIn(word,result)
        self.assertFalse(json.loads(result)["allowed_to_publish"])
        self.assertTrue(json.loads(result)["receiver_register_not_proven_this"])

if __name__=="__main__":
    unittest.main()
