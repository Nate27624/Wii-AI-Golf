"""Entirely synthetic P0 cache-endpoint ranking tests, never reads private RAM."""
from __future__ import annotations
from copy import deepcopy
import importlib.util
import math
from pathlib import Path
import struct
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts"/"audit_p0_wedge_cache_endpoint_order_private.py"
spec=importlib.util.spec_from_file_location("p0_endpoint",SCRIPT)
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

def bits(x):
    return struct.unpack(">I",struct.pack(">f",float(x)))[0]

def v(x,y=0,z=0):
    return (bits(x),bits(y),bits(z))

def mk(ball,cc,pin=20,start=-2,f0=40,fc=-20):
    return {
        "selected_index":0, "hole":1,"ball_obj":11,"field":22,
        "pin_obj":33,"start_obj":44,"cfg_bc":0,"cfg_c0":2,"cfg_c4":3,
        "pin":v(pin),
        "triplets":{
            "ball_object_0x030":v(ball),"source_current_start":v(start),
            "ball_cache_0x0cc":v(cc),"ball_cache_0x0f0":v(f0),
            "ball_cache_0x0fc":v(fc)
        }
    }

def samples():
    return {1:mk(0,0),2:mk(4,4),5:mk(0,10),6:mk(4,10),7:mk(10,10)}

class EndpointTests(unittest.TestCase):
    def test_positive_wedge_approaches_stable_cache(self):
        r=audit.analyze_samples(samples())
        self.assertTrue(r["cache_stable_within_wedge"]["+0xCC"])
        self.assertTrue(r["CC_candidate_distance_strictly_decreases_5_to_6_to_7"])
        self.assertTrue(r["CC_equals_current_exactly_in_phase_7"])
        self.assertFalse(r["CC_equals_PIN_exactly_in_phase_7"])

    def test_control_driver_cc_moves_with_current(self):
        r=audit.analyze_samples(samples())
        self.assertEqual(r["driver_1_to_2_current_changed_components"],1)
        self.assertEqual(r["driver_1_to_2_CC_changed_components"],1)
        self.assertTrue(r["driver_first_ball_equals_first_CC"])
        self.assertTrue(r["driver_second_ball_equals_second_CC"])

    def test_pin_candidate_may_also_get_closer(self):
        r=audit.analyze_samples(samples())
        self.assertTrue(r["PIN_candidate_distance_strictly_decreases_5_to_6_to_7"])
        self.assertFalse(r["START_candidate_distance_strictly_decreases_5_to_6_to_7"])

    def test_distance_to_CC_competitor_ranks(self):
        r=audit.analyze_samples(samples())
        self.assertTrue(r["wedge_phase_rows"][2]["CC_closer_to_current_than_pin"])
        self.assertTrue(r["wedge_phase_rows"][2]["CC_closer_to_current_than_F0"])
        self.assertTrue(r["wedge_phase_rows"][2]["CC_closer_to_current_than_FC"])
        self.assertIsNone(r["wedge_phase_rows"][0]["distance_to_CC_less_than_prior_phase"])

    def test_non_monotone_invalidates_endpoint_approach(self):
        s=samples()
        s[6]["triplets"]["ball_object_0x030"]=v(-1)
        r=audit.analyze_samples(s)
        self.assertFalse(r["CC_candidate_distance_strictly_decreases_5_to_6_to_7"])
        self.assertFalse(r["wedge_phase_rows"][1]["distance_to_CC_less_than_prior_phase"])

    def test_cc_movement_reported_not_falsely_stable(self):
        s=samples();s[6]["triplets"]["ball_cache_0x0cc"]=v(9)
        r=audit.analyze_samples(s)
        self.assertFalse(r["cache_stable_within_wedge"]["+0xCC"])

    def test_pin_pointer_switch_fail_closed(self):
        s=samples();s[6]["pin_obj"]=99
        with self.assertRaisesRegex(ValueError,"ABSTAIN"):
            audit.analyze_samples(s)

    def test_config_selector_change_fail_closed(self):
        for key in ("cfg_bc","cfg_c0","cfg_c4"):
            s=samples();s[6][key]=99
            with self.subTest(key=key),self.assertRaises(ValueError):
                audit.analyze_samples(s)

    def test_tee_or_pin_vector_change_fail_closed(self):
        for k in ("pin","source_current_start"):
            s=samples()
            if k=="pin":
                s[6]["pin"]=v(19)
            else:
                s[6]["triplets"][k]=v(-3)
            with self.subTest(key=k), self.assertRaises(ValueError):
                audit.analyze_samples(s)

    def test_owner_mismatch_fail_closed(self):
        s=samples();s[7]["selected_index"]=1
        with self.assertRaises(ValueError):
            audit.analyze_samples(s)

    def test_hole_mismatch_fail_closed(self):
        s=samples();s[2]["hole"]=3
        with self.assertRaises(ValueError):
            audit.analyze_samples(s)

    def test_missing_phase_rejected(self):
        s=samples();s.pop(7)
        with self.assertRaisesRegex(ValueError,"Exactly"):
            audit.analyze_samples(s)

    def test_nan_inf_unbounded_rejected(self):
        for val in (float("nan"),float("inf"),1000001):
            s=samples();s[6]["triplets"]["ball_object_0x030"]=v(val)
            with self.subTest(val=val),self.assertRaises(ValueError):
                audit.analyze_samples(s)

    def test_bitpatterns_invalid_rejected(self):
        for w in (-1,2**32,True,1.5):
            with self.subTest(w=w), self.assertRaises(ValueError):
                audit.float3((w,0,0))

    def test_candidate_axis_sign_consistency_only(self):
        r=audit.analyze_samples(samples())
        self.assertEqual(r["selected_ball_component_directions_consistent_5_6_and_6_7"],
                         [True,False,False])

    def test_no_private_words_or_physical_promotions(self):
        s=samples()
        r=audit.analyze_samples(s)
        text=str(r)
        self.assertNotIn("'triplets'",text)
        self.assertNotIn("'ball_obj'",text)
        self.assertNotIn("'pin_obj'",text)
        self.assertNotIn("private bank SHA",text)
        for key in ("cache_endpoint_semantics_verified","physical_world_XYZ_verified",
                    "ball_velocity_verified","game_power_verified","score_verified",
                    "approved_for_training","same_guest_frame_machine_verified"):
            with self.subTest(key=key):
                self.assertIs(r[key],False)

    def test_python_isolated_cli(self):
        p=subprocess.run([sys.executable,"-I",str(SCRIPT),"--help"],
                         cwd=str(ROOT),capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("--archive",p.stdout)

if __name__=="__main__":
    unittest.main()
