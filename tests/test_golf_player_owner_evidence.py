"""License-free synthetic test of conservative RPGolPlayer source-vtable evidence."""
from __future__ import annotations
import json
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.audit.golf_player_owner_evidence import audit_player_owner


def sample():
    a=bytearray(0x4BF8D4);b=bytearray(0x7000)
    a[:8]=b"RSPE01\x00\x01"
    def m1(off,n):struct.pack_into(">I",a,off,n)
    def m2(off,n):struct.pack_into(">I",b,off,n)
    m1(0x4BF4D8,0x80001000)
    m1(0x4BF8C4,0x90001000)
    m1(0x4BF868,0x90001100)
    m1(0x4BF8D0,0x90001200)
    m1(0x1000+0x0C,0x90000100)
    m1(0x1000+0x18,5)
    m2(0x100+0x1C,5)
    m2(0x100+0x20,0x80001000)
    m2(0x100+0x54,2)
    m2(0x100+0x9C,0x90000300)
    m2(0x300,0x803C77A8)
    m2(0x304,0x90000100)
    m2(0x300+0x30,0x90002000)
    m2(0x2000,0x803C7CD0)
    for i in range(8):
        m1(0x3C7CD0+4*i,0x8029E700 + i*8)
    m2(0x1200,0x803C7DD0)
    for i in range(4):
        m1(0x3C7DD0+4*i,0x802A2300+i*8)
    m2(0x1000+0x94,4)
    m2(0x1000+0x98,1)
    m2(0x1100+0x3C,6)
    m2(0x1100+0x48,31)
    return a,b


class PlayerOwnerSourceTests(unittest.TestCase):
    def test_one_main_to_player_code_source_candidate(self):
        a,b=sample()
        r=audit_player_owner(a,b,strict_size=False)
        self.assertEqual(r["main_words_screened"],64)
        self.assertEqual(r["candidate_count"],1)
        self.assertEqual(r["player_data_and_text_cross_unit_candidates"][0][
            "owner_relative_offset"],"+0x030")
        self.assertEqual(r["player_data_and_text_cross_unit_candidates"][0][
            "first_twelve_table_words_in_player_text_unit"],8)
        self.assertTrue(r["player_manager_source_table_candidate"])
        self.assertFalse(r["actual_C++_dynamic_type_verified"])
        self.assertFalse(r["swing_power_verified"])

    def test_pointer_without_player_data_region_not_a_player(self):
        a,b=sample()
        struct.pack_into(">I",b,0x2000,0x803C77A8)
        r=audit_player_owner(a,b,strict_size=False)
        self.assertEqual(r["candidate_count"],0)

    def test_player_data_without_functions_not_a_player(self):
        a,b=sample()
        for i in range(8):
            struct.pack_into(">I",a,0x3C7CD0+4*i,0)
        r=audit_player_owner(a,b,strict_size=False)
        self.assertEqual(r["candidate_count"],0)

    def test_duplicate_field_pointers_are_not_unique_owner_evidence(self):
        a,b=sample()
        struct.pack_into(">I",b,0x300+0x34,0x90002000)
        r=audit_player_owner(a,b,strict_size=False)
        self.assertEqual(r["candidate_count"],2)
        self.assertFalse(r["unique_source_player_like_candidate"])

    def test_main_chain_wrong_scene_fails_closed(self):
        a,b=sample()
        struct.pack_into(">I",b,0x100+0x20,0)
        with self.assertRaises(ValueError):
            audit_player_owner(a,b,strict_size=False)

    def test_no_private_pointers_in_output(self):
        a,b=sample()
        text=json.dumps(audit_player_owner(a,b,strict_size=False))
        for bad in ("0x90002000", "0x803C7CD0", "8029E700",
                    "0x80001000", "bytes_hex", "mem2.raw"):
            self.assertNotIn(bad,text)

    def test_strict_native_memory_size_default(self):
        a,b=sample()
        with self.assertRaises(ValueError):
            audit_player_owner(a,b)

if __name__=="__main__":
    unittest.main()
