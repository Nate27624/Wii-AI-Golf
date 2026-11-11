"""Synthetic four-checkpoint null-control tests, no real game binary."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent/"src"))
from test_golf_player_owner_evidence import sample
from wii_ai_golf.audit.golf_player_four_phase import compare_player_control_pairs


def fixture():
    pairs=[sample() for _ in range(4)]
    def change(stage,offset,value):
        struct.pack_into(">I",pairs[stage][1],0x2000+offset,value)
    change(2,0x40,7) # aim: transient -> B1
    for i in range(1,4):
        change(i,0x44,i) # timer/control changes in every state
    change(2,0x48,5) # aim: persists through B3
    change(3,0x48,5)
    change(3,0x4C,8) # changed only at return
    return pairs


class PlayerFourPhaseTests(unittest.TestCase):
    def test_idle_rejected_and_aim_candidates_triaged(self):
        a=compare_player_control_pairs(fixture(),strict_size=False)
        c=a["counters"]
        self.assertEqual(c["idle_B0_B1_changed_words"],1)
        self.assertEqual(c["aim_B1_B2_changed_words"],3)
        self.assertEqual(c["return_B2_B3_changed_words"],3)
        self.assertEqual(c["stable_idle_changed_aim_words"],2)
        self.assertEqual(c["aim_only_reverted_to_B1_words"],1)
        self.assertEqual(c["aim_only_persisted_at_B3_words"],1)
        self.assertEqual(a["candidates"][0]["candidate_player_relative_offset"],"+0x040")
        self.assertFalse(a["power_verified"])

    def test_gameplay_mode_mismatch_fails_closed(self):
        a=fixture()
        struct.pack_into(">I",a[2][1],0x1000+0x94,3)
        with self.assertRaises(ValueError):
            compare_player_control_pairs(a,strict_size=False)

    def test_player_candidate_source_provenance_checked_each_phase(self):
        a=fixture()
        struct.pack_into(">I",a[3][1],0x2000,0)
        with self.assertRaises(ValueError):
            compare_player_control_pairs(a,strict_size=False)

    def test_unknown_relative_word_is_not_promoted_to_power(self):
        r=compare_player_control_pairs(fixture(),strict_size=False)
        self.assertFalse(r["actual_cpp_type_verified"])
        self.assertFalse(r["clock_controls_complete"])
        self.assertFalse(r["club_angle_verified"])
        self.assertTrue(all(not c["physical_semantics_verified"] for c in r["candidates"]))

    def test_no_absolute_pointers_or_private_bytes(self):
        r=json.dumps(compare_player_control_pairs(fixture(),strict_size=False))
        for bad in ("0x90002000","0x803C7CD0","bytes_hex","mem2.raw"):
            self.assertNotIn(bad,r)
        self.assertIn("+0x040",r)
        self.assertFalse(compare_player_control_pairs(
            fixture(),strict_size=False)["allowed_to_publish"])

    def test_requires_four_complete_pairs(self):
        with self.assertRaises(ValueError):
            compare_player_control_pairs(fixture()[:3],strict_size=False)

    def test_native_memory_size_gate(self):
        with self.assertRaises(ValueError):
            compare_player_control_pairs(fixture())

if __name__ == "__main__":
    unittest.main()
