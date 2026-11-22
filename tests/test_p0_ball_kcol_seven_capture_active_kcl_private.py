"""Synthetic-only original seven-capture KCL active-resource source profile tests."""
from __future__ import annotations

from pathlib import Path
import importlib.util
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/"scripts"
sys.path.insert(0,str(SCRIPTS))


def load():
    spec=importlib.util.spec_from_file_location(
        "seven_kcol_profile",SCRIPTS/"p0_ball_kcol_seven_capture_active_kcl_private.py")
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


m=load()


def make_rows(class13=0):
    return [
        {"capture":i,"same_kcol_instance_pointer_as_capture1":True,
         "same_prism_base_pointer_as_capture1":True,
         "all_active_buffers_match_terrain":True,
         "active_prism_histogram_matches_existing_terrain":True,
         "class13_count_in_verified_active_prisms":class13}
        for i in range(1,8)
    ]


def prism_bytes(materials):
    out=bytearray(16*len(materials))
    for i,code in enumerate(materials):
        struct.pack_into(">H",out,16*i+14,code)
    return bytes(out)


class OriginalSevenKCLSourceTests(unittest.TestCase):
    def test_exact_prism_class_histogram(self):
        data=prism_bytes([1,12,7,1,13,13,0])
        self.assertEqual(m.classify_usable_prisms(data,7),
                         {0:1,1:2,7:1,12:1,13:2})

    def test_absent_13_distinct_from_other_type(self):
        hist=m.classify_usable_prisms(prism_bytes([1,7,12,12]),4)
        self.assertEqual(hist.get(13,0),0)
        self.assertEqual(sum(hist.values()),4)

    def test_dummy_slot_is_not_usable_payload(self):
        data=prism_bytes([13,1,2])
        # A dummy record that happens to contain 13 must not be counted.
        self.assertEqual(m.classify_usable_prisms(data[16:],2),{1:1,2:1})

    def test_invalid_prism_lengths_abstain(self):
        for data,number in ((b"",1),(b"\0"*15,1),(b"\0"*32,1)):
            with self.subTest(n=len(data),count=number):
                with self.assertRaises(ValueError):
                    m.classify_usable_prisms(data,number)

    def test_original_seven_complete_and_no_physics_claim(self):
        s=m.aggregate(make_rows())
        self.assertTrue(s["all_seven_active_kcl_same_2498_terrain_resource"])
        self.assertTrue(s["all_seven_active_prism_class13_counts_zero"])
        self.assertFalse(s["tree_hitbox_geometry_proven"])
        self.assertFalse(s["ball_velocity_semantics_proven"])
        self.assertFalse(s["training_approved"])
        self.assertFalse(s["other_kcl_resource_excluded_globally"])
        self.assertFalse(s["non_kcl_tree_collision_excluded"])

    def test_one_class13_prevents_zero_claim(self):
        rows=make_rows()
        rows[5]["class13_count_in_verified_active_prisms"]=1
        self.assertFalse(m.aggregate(rows)["all_seven_active_prism_class13_counts_zero"])

    def test_per_capture_mismatch_prevents_complete_identity(self):
        rows=make_rows()
        rows[2]["all_active_buffers_match_terrain"]=False
        self.assertFalse(m.aggregate(rows)["all_seven_active_kcl_same_2498_terrain_resource"])

    def test_all_seven_required_in_order(self):
        rows=make_rows()
        for bad in (rows[:-1],list(reversed(rows)),
                    [{**r,"capture":99} if r["capture"]==4 else r for r in rows]):
            with self.assertRaises(ValueError):
                m.aggregate(bad)

    def test_other_resource_not_excluded_even_when_all_match(self):
        result=m.aggregate(make_rows())
        self.assertFalse(result["class13_tree_event_proven"])
        self.assertFalse(result["other_kcl_resource_excluded_globally"])


if __name__=="__main__":
    unittest.main()
