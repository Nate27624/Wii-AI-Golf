"""Synthetic-only P0 selected player 51-word phase mask tests."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import audit_p0_seven_record_phase_masks_private as m

def phase():
    return {
        "selected_index":0,"hole":1,
        "owners":tuple(range(7)),
        "cfg_bc":0,"cfg_c0":0,"cfg_c4":0,
        "whole_record":tuple([0]*51),
        "triplets":{"source_current_start":(1,2,3)},
        "pin":(5,6,7),
    }

def words(**by_offset):
    a=[0]*51
    for offset,value in by_offset.items():
        a[int(offset,16)//4]=value
    return tuple(a)

def samples():
    s={n:phase() for n in m.PHASES}
    s[1]["whole_record"]=words(**{"034":1})
    s[2]["whole_record"]=words(**{"034":2, "038":4})
    s[5]["whole_record"]=words(**{"074":0,"090":0,"094":0,"098":0})
    s[6]["whole_record"]=words(**{"074":1,"090":2,"094":1,"098":0})
    s[7]["whole_record"]=words(**{"074":0,"090":4,"094":1,"098":9})
    return s

class RecordPhaseTests(unittest.TestCase):
    def test_driver_changed_relative_only(self):
        r=m.summarize(samples())
        self.assertEqual(r["driver_D1_to_D2_changed_relative_offsets"],
                         ["+0x034","+0x038"])
        self.assertEqual(r["driver_D1_to_D2_changed_word_count"],2)

    def test_wedge_two_temporal_intervals_and_net(self):
        r=m.summarize(samples())
        self.assertEqual(r["wedge_5_to_6_changed_relative_offsets"],
                         ["+0x074","+0x090","+0x094"])
        self.assertEqual(r["wedge_6_to_7_changed_relative_offsets"],
                         ["+0x074","+0x090","+0x098"])
        self.assertEqual(r["wedge_5_to_7_changed_relative_offsets"],
                         ["+0x090","+0x094","+0x098"])

    def test_returned_word_distinct_from_late_only(self):
        r=m.summarize(samples())
        self.assertEqual(r["wedge_changed_then_returned_to_W5_relative_offsets"],
                         ["+0x074"])
        self.assertEqual(r["wedge_changed_only_in_6_to_7_relative_offsets"],
                         ["+0x098"])
        self.assertEqual(r["wedge_changed_only_in_5_to_6_relative_offsets"],
                         ["+0x094"])

    def test_mid_and_late_word_can_both_change_without_return(self):
        r=m.summarize(samples())
        self.assertEqual(r["wedge_changed_in_both_intervals_relative_offsets"],
                         ["+0x074","+0x090"])
        self.assertNotIn("+0x090",r["wedge_changed_then_returned_to_W5_relative_offsets"])

    def test_driver_and_wedge_specific_offsets(self):
        r=m.summarize(samples())
        self.assertEqual(r["driver_changes_not_seen_in_wedge_relative_offsets"],
                         ["+0x034","+0x038"])
        self.assertEqual(r["wedge_net_changes_overlap_driver_relative_offsets"],[])
        self.assertEqual(r["wedge_net_changes_not_seen_in_driver_relative_offsets"],
                         ["+0x090","+0x094","+0x098"])

    def test_selected_owner_mismatch_abstains(self):
        s=samples()
        s[6]["owners"]=tuple(list(s[6]["owners"])[:-1]+[999])
        with self.assertRaises(ValueError):m.summarize(s)

    def test_source_hole_and_slot_mismatch_abstain(self):
        for k,v in (("hole",10),("selected_index",1)):
            s=samples();s[7][k]=v
            with self.subTest(k=k),self.assertRaises(ValueError):m.summarize(s)

    def test_pin_start_and_selector_change_abstain(self):
        for what in ("pin","source_current_start","cfg_bc","cfg_c0","cfg_c4"):
            s=samples()
            if what=="source_current_start":s[7]["triplets"][what]=(7,8,9)
            elif what=="pin":s[7][what]=(0,0,0)
            else:s[7][what]=22
            with self.subTest(what=what),self.assertRaises(ValueError):m.summarize(s)

    def test_missing_phase_or_partial_record_abstains(self):
        s=samples();del s[6]
        with self.assertRaises(ValueError):m.summarize(s)
        s=samples();s[6]["whole_record"]=tuple([0]*50)
        with self.assertRaises(ValueError):m.summarize(s)

    def test_same_state_has_zero_changed_masks_not_forced_signal(self):
        s={n:phase() for n in m.PHASES}
        r=m.summarize(s)
        self.assertEqual(r["wedge_5_to_6_changed_relative_offsets"],[])
        self.assertEqual(r["wedge_6_to_7_changed_relative_offsets"],[])
        self.assertFalse(r["impact_state_verified"])

    def test_no_raw_values_pointers_floats_or_files_printed(self):
        r=m.summarize(samples())
        data=json.dumps(r)
        for secret in ("whole_record","owners","9000ABCD","private_path",
                       "MEM2.bin","raw_word",'"pin":','"ball":'):
            self.assertNotIn(secret,data)
        for flag in ("shot_power_verified","impact_state_verified","ball_velocity_verified",
                     "physical_ball_xyz_verified","training_approved","allowed_to_publish"):
            self.assertIs(r[flag],False)

    def test_manifest_fails_before_mem_read(self):
        with patch.object(m.seven,"_check_archive",side_effect=ValueError("bad sha")):
            with self.assertRaises(ValueError):
                m.analyze(Path("not-a-real-archive"))

    def test_python_isolated_cli(self):
        script=ROOT/"scripts"/"audit_p0_seven_record_phase_masks_private.py"
        p=subprocess.run([sys.executable,"-I",str(script),"--help"],
                         capture_output=True,text=True,cwd=ROOT,timeout=20)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("--archive",p.stdout)

if __name__=="__main__":
    unittest.main()
