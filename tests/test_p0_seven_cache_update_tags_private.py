"""No real game banks; fabricated fail-closed / privacy tests only."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "scripts" / "audit_p0_seven_cache_update_tags_private.py"
spec = importlib.util.spec_from_file_location("p0_tag", FILE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def fake(n):
    return {
        "selected_index":0, "hole":1,
        "refs":{"field":100,"record":200,"ball":300,"pin":400,"start":500},
        "ball_refs":(300,600,700,800),
        "tags":((10,20),(0,0),(0,0),(0,0)),
        "cfg_bc":1,"cfg_c0":2,"cfg_c4":3,
        "pin_triplet":(40,50,60),"start_triplet":(1,2,3),
        "live_triplet":(n,n+1,n+2),
        "ball_cache_0x0f0":(8,9,10),
        "ball_cache_0x0fc":(11,12,13),
    }

def samples():
    return {n:fake(n) for n in mod.PHASES}

class TestCacheTagP0(unittest.TestCase):
    def test_four_within_shot_edges_only(self):
        r=mod.summarize(samples())
        self.assertEqual([x["edge"] for x in r["within_shot_edges"]],
                         ["1_to_2","5_to_6","6_to_7","5_to_7"])

    def test_moving_wedge_can_have_unchanged_tags(self):
        row=mod.summarize(samples())["within_shot_edges"][1]
        self.assertEqual(row["selected_live_changed_components"],3)
        self.assertFalse(row["selected_tag_0x118_changed"])

    def test_118_changed_without_f0_change(self):
        x=samples();x[6]["tags"]=((11,20),(0,0),(0,0),(0,0))
        row=mod.summarize(x)["within_shot_edges"][1]
        self.assertTrue(row["tag_118_changed_without_cache_F0_bit_change"])
        self.assertFalse(row["tag_11C_changed_without_cache_FC_bit_change"])

    def test_11c_changed_with_fc_cache(self):
        x=samples();x[6]["tags"]=((10,21),(0,0),(0,0),(0,0))
        x[6]["ball_cache_0x0fc"]=(12,12,13)
        row=mod.summarize(x)["within_shot_edges"][1]
        self.assertTrue(row["selected_tag_0x11C_changed"])
        self.assertEqual(row["selected_cache_FC_changed_components"],1)
        self.assertFalse(row["tag_11C_changed_without_cache_FC_bit_change"])

    def test_inactive_controls_not_merged_with_selected(self):
        x=samples();x[6]["tags"]=((10,20),(1,0),(0,2),(0,0))
        row=mod.summarize(x)["within_shot_edges"][1]
        self.assertEqual(row["inactive_slots_tag_0x118_changed_count"],1)
        self.assertEqual(row["inactive_slots_tag_0x11C_changed_count"],1)
        self.assertFalse(row["selected_tag_0x118_changed"])

    def test_owner_mismatch_abstains(self):
        x=samples();x[6]["selected_index"]=2
        with self.assertRaises(ValueError):mod.summarize(x)

    def test_changed_ball_reference_abstains(self):
        x=samples();x[7]["refs"]["ball"]=888
        with self.assertRaises(ValueError):mod.summarize(x)

    def test_changed_pin_abstains(self):
        x=samples();x[7]["pin_triplet"]=(40,50,61)
        with self.assertRaises(ValueError):mod.summarize(x)

    def test_changed_config_abstains(self):
        x=samples();x[7]["cfg_c4"]=99
        with self.assertRaises(ValueError):mod.summarize(x)

    def test_duplicate_source_ball_abstains(self):
        x=samples();x[1]["ball_refs"]=(300,300,700,800)
        with self.assertRaises(ValueError):mod.summarize(x)

    def test_malformed_metadata_abstains(self):
        x=samples();x[1]["tags"]=((1,),(0,0),(0,0),(0,0))
        with self.assertRaises(ValueError):mod.summarize(x)

    def test_out_of_range_metadata_abstains(self):
        x=samples();x[1]["tags"]=((0x100000000,0),(0,0),(0,0),(0,0))
        with self.assertRaises(ValueError):mod.summarize(x)

    def test_missing_phase_abstains(self):
        x=samples();del x[3]
        with self.assertRaises(ValueError):mod.summarize(x)

    def test_no_semantic_or_training_promotion(self):
        r=mod.summarize(samples())
        for key in ("cache_tag_semantics_verified","tag_is_guest_frame_counter_verified",
                    "actual_ball_world_xyz_verified","impact_verified",
                    "swing_power_verified","training_approved","allowed_to_publish",
                    "executed_cache_writer_verified"):
            self.assertIs(r[key],False)

    def test_private_values_redacted(self):
        x=samples();x[5]["tags"]=((987654321,123456789),(0,0),(0,0),(0,0))
        output=json.dumps(mod.summarize(x))
        for forbidden in ("987654321","123456789","ball_refs","(300,600"):
            self.assertNotIn(forbidden,output)

    def test_isolated_python_help(self):
        p=subprocess.run([sys.executable,"-I",str(FILE),"--help"],
                         capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("--archive",p.stdout)

if __name__ == "__main__":
    unittest.main()
