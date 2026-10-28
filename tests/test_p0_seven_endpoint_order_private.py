"""Fabricated candidate vectors; NEVER real Dolphin banks, addresses or files."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import audit_p0_seven_endpoint_order_private as m

def words(v):
    return tuple(struct.unpack(">I",struct.pack(">f",float(x)))[0] for x in v)

def sample(ball=(0,0,0),cc=(0,0,0)):
    return {
      "selected_index":0,"hole":1,
      "owner_ids":(1,2,3,4,5,6,7),
      "cfg_bc":8,"cfg_c0":9,"cfg_c4":10,
      "triplets":{
         "ball_object_0x030":words(ball),
         "ball_cache_0x0cc":words(cc),
         "ball_cache_0x0f0":words((7,8,9)),
         "ball_cache_0x0fc":words((4,5,6)),
         "source_current_start":words((10,0,0))},
      "pin":words((1,0,0)),
    }

def fixture():
    return {
        1:sample((9,9,9),(3,3,3)),
        2:sample((0,0,0),(0,0,0)),
        5:sample((-1,8,2)),
        6:sample((-.5,5,1)),
        7:sample((0,0,0)),
    }

class EndpointTests(unittest.TestCase):
    def test_endpoint_candidate_reaches_unchanged_cc(self):
        r=m.summarize(fixture())
        self.assertTrue(r["wedge_stable_selected_owner_and_geometry"])
        self.assertTrue(r["wedge_cache_CC_bitwise_constant"])
        self.assertTrue(r["wedge_ball_reaches_unchanged_cache_CC_at_W7"])
        self.assertEqual(r["wedge_current_ball_equal_cache_CC_components"],[0,0,3])
        self.assertEqual(r["wedge_ball_to_cache_CC_candidate_distance_step_relation"],
                         ["decreased","decreased"])
        self.assertFalse(r["driver_D1_to_D2_cache_CC_stable"])
        self.assertFalse(r["physical_ball_xyz_verified"])

    def test_pin_not_cache_and_not_ball_at_w7(self):
        r=m.summarize(fixture())
        self.assertFalse(r["wedge_cache_CC_equals_pin"])
        self.assertFalse(r["wedge_ball_equals_pin_at_W7"])
        self.assertEqual(r["wedge_ball_to_pin_candidate_distance_step_relation"],
                         ["decreased","decreased"])

    def test_indeterminate_first_distance_step_is_not_forced(self):
        x=fixture()
        x[6]["triplets"]["ball_object_0x030"]=words((-1,8,-2))
        r=m.summarize(x)
        self.assertEqual(r["wedge_ball_to_cache_CC_candidate_distance_step_relation"][0],
                         "equal_within_numeric_tolerance")

    def test_owner_mismatch_refused(self):
        x=fixture();x[6]["owner_ids"]=(1,2,3,4,5,999,7)
        with self.assertRaises(ValueError):m.summarize(x)

    def test_selector_mismatch_refused(self):
        for key in ("cfg_bc","cfg_c0","cfg_c4"):
            x=fixture();x[6][key]=100
            with self.subTest(key=key),self.assertRaises(ValueError):m.summarize(x)

    def test_changed_pin_or_start_refused(self):
        for key,value in (("pin",words((2,0,0))),
                          ("triplets",None)):
            x=fixture()
            if key=="pin":x[6]["pin"]=value
            else:x[6]["triplets"]["source_current_start"]=words((11,0,0))
            with self.subTest(key=key),self.assertRaises(ValueError):m.summarize(x)

    def test_changed_cc_refused(self):
        x=fixture()
        x[6]["triplets"]["ball_cache_0x0cc"]=words((1,0,0))
        with self.assertRaises(ValueError):m.summarize(x)

    def test_no_candidate_motion_refused(self):
        x=fixture()
        x[6]["triplets"]["ball_object_0x030"]=x[5]["triplets"]["ball_object_0x030"]
        with self.assertRaises(ValueError):m.summarize(x)

    def test_malformed_unknown_or_nonfinite_word_refused(self):
        for val in ((0x7fc00000,0,0),(0x7f800000,0,0),(0,1)):
            x=fixture();x[6]["triplets"]["ball_object_0x030"]=val
            with self.subTest(val=val),self.assertRaises(ValueError):m.summarize(x)

    def test_no_private_numeric_vectors_or_pointers_in_report(self):
        report=m.summarize(fixture())
        public=json.dumps(report)
        for forbidden in ("owner_ids","private_path","sha256","ball_object_0x030",
                          "0x9000","raw_float","MEM1.bin","(9, 9, 9)"):
            self.assertNotIn(forbidden,public)
        self.assertFalse(report["allowed_to_publish"])
        self.assertFalse(report["training_approved"])
        self.assertFalse(report["same_boot_across_phases_machine_verified"])

    def test_missing_shot_phase_refused(self):
        x=fixture();x.pop(6)
        with self.assertRaises(ValueError):m.summarize(x)

    def test_driver_geometry_not_stable_not_comparable(self):
        x=fixture();x[2]["owner_ids"]=(1,2,3,4,999,6,7)
        r=m.summarize(x)
        self.assertFalse(r["driver_D1_to_D2_same_source_owner_and_geometry"])
        self.assertIsNone(r["driver_D1_to_D2_cache_CC_stable"])

    def test_original_archive_gate_invoked_before_any_read(self):
        with patch.object(m.seven,"_check_archive",side_effect=ValueError("SHA failed")):
            with self.assertRaises(ValueError):
                m.analyze(Path("nonexistent-private"))

    def test_isolated_python_help_smoke(self):
        script=ROOT/"scripts"/"audit_p0_seven_endpoint_order_private.py"
        run=subprocess.run([sys.executable,"-I",str(script),"--help"],
                           capture_output=True,text=True,timeout=20,cwd=ROOT)
        self.assertEqual(run.returncode,0,msg=run.stderr)
        self.assertIn("--archive",run.stdout)
        self.assertNotIn("ModuleNotFoundError",run.stderr)

if __name__=="__main__":
    unittest.main()
