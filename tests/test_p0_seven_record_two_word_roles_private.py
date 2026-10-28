"""Synthetic-only selected record+0x030/+0x090 type/alias controls."""
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
import audit_p0_seven_record_two_word_roles_private as m

def fword(x):
    return struct.unpack(">I",struct.pack(">f",float(x)))[0]

def words(a,b):
    v=[0]*51
    v[0x30//4]=a
    v[0x90//4]=b
    return tuple(v)

def snap(a,b,ball):
    return {
        "selected_index":0,"hole":1,
        "owners":(1,2,3,4,5,6,7),
        "cfg_bc":42,"cfg_c0":43,"cfg_c4":44,
        "whole_record":words(a,b),
        "triplets":{
            "ball_object_0x030":tuple(fword(t) for t in ball),
            "ball_cache_0x0cc":tuple(fword(t) for t in (8,9,10)),
            "source_current_start":tuple(fword(t) for t in (0,0,0)),
        },
        "pin":tuple(fword(t) for t in (12,0,4))
    }

def fixture():
    return {
        1:snap(fword(2),0x9000A010,(2,10,0)),
        2:snap(fword(4),0x9000A014,(4,10,0)),
        5:snap(fword(1),0x9000A018,(1,10,0)),
        6:snap(fword(2),0x9000A01C,(2,7,0)),
        7:snap(fword(3),0x9000A020,(3,4,0)),
    }

class TwoWordRoleTests(unittest.TestCase):
    def test_same_component_alias_for_float_word_and_unsupported_other(self):
        r=m.report(fixture())
        one=r["fields"][0]
        self.assertEqual(one["record_relative_offset"],"+0x030")
        self.assertEqual(one["same_one_ball_component_alias_all_three_wedge_phases"],[True,False,False])
        self.assertEqual(one["wedge_distinct_u32_bitpatterns"],3)
        self.assertEqual(one["wedge_f32_direction_steps"],["up","up"])
        self.assertTrue(one["same_direction_as_ball_f32_component_across_both_wedge_edges"][0])
        self.assertFalse(one["physical_interpretation_verified"])

    def test_pointer_shaped_bits_can_also_look_like_bounded_float(self):
        r=m.report(fixture())
        second=r["fields"][1]
        self.assertTrue(all(second["native_mem1_or_mem2_pointer_shaped_in_phase_order_D1_D2_W5_W6_W7"]))
        # Shape overlap: a native address's bits can encode a finite tiny f32.
        # The analyzer must not infer either semantic type from this pattern.
        self.assertEqual(second["bounded_f32_candidate_in_wedge_5_6_7"],[True]*3)
        self.assertFalse(m.report(fixture())["pointer_shape_proves_live_pointer"])
        self.assertFalse(m.report(fixture())["float_shape_or_direction_proves_numeric_semantics"])
        self.assertFalse(second["same_one_ball_component_alias_all_three_wedge_phases"][0])

    def test_equal_current_word_does_not_claim_physics(self):
        r=m.report(fixture())
        self.assertIs(r["actual_ball_world_xyz_verified"],False)
        self.assertIs(r["ball_velocity_verified"],False)
        self.assertIs(r["training_approved"],False)

    def test_driver_word_and_wedge_changed_same_timing(self):
        for item in m.report(fixture())["fields"]:
            self.assertTrue(item["changed_wedge_5_to_6"])
            self.assertTrue(item["changed_wedge_6_to_7"])
            self.assertTrue(item["changed_driver_D1_to_D2"])

    def test_invariant_word_is_a_negative_control(self):
        x=fixture()
        for n in m.PHASES:
            v=list(x[n]["whole_record"])
            v[0x90//4]=123
            x[n]["whole_record"]=tuple(v)
        r=m.report(x)["fields"][1]
        self.assertEqual(r["wedge_distinct_u32_bitpatterns"],1)
        self.assertFalse(r["changed_wedge_5_to_6"])
        self.assertFalse(r["changed_wedge_6_to_7"])

    def test_false_alias_when_one_wedge_phase_differs(self):
        x=fixture()
        v=list(x[6]["whole_record"]);v[0x30//4]=fword(77)
        x[6]["whole_record"]=tuple(v)
        self.assertFalse(m.report(x)["fields"][0]["same_one_ball_component_alias_all_three_wedge_phases"][0])

    def test_three_point_record_scalar_affine_relation_is_only_candidate(self):
        x=fixture()
        for phase,val in ((5,1),(6,2),(7,3)):
            words=list(x[phase]["whole_record"])
            words[0x90//4]=fword(2*val+5)
            x[phase]["whole_record"]=tuple(words)
        rel=m.report(x)["relationship"]
        self.assertEqual(rel["wedge_player_030_equals_player_090_word_by_phase_W5_W6_W7"],
                         [False,False,False])
        self.assertTrue(rel["wedge_player_090_affine_to_player_030_three_points_candidate"])
        self.assertTrue(rel["wedge_player_030_affine_to_ball_component_0_three_points_candidate"])
        self.assertTrue(rel["wedge_player_090_affine_to_ball_component_0_three_points_candidate"])
        self.assertFalse(rel["wedge_player_030_minus_090_is_numeric_constant"])
        self.assertFalse(rel["three_point_affinity_proves_physical_mapping"])

    def test_constant_scalar_difference_candidate(self):
        x=fixture()
        for phase,val in ((5,1),(6,2),(7,3)):
            words=list(x[phase]["whole_record"])
            words[0x90//4]=fword(val+5)
            x[phase]["whole_record"]=tuple(words)
        rel=m.report(x)["relationship"]
        self.assertTrue(rel["wedge_player_030_minus_090_is_numeric_constant"])
        self.assertTrue(rel["wedge_player_090_affine_to_player_030_three_points_candidate"])

    def test_non_affine_three_point_relationship_rejected(self):
        x=fixture()
        for phase,val in ((5,10),(6,25),(7,11)):
            words=list(x[phase]["whole_record"])
            words[0x90//4]=fword(val)
            x[phase]["whole_record"]=tuple(words)
        rel=m.report(x)["relationship"]
        self.assertFalse(rel["wedge_player_090_affine_to_player_030_three_points_candidate"])
        self.assertFalse(rel["wedge_player_030_minus_090_is_numeric_constant"])

    def test_pointer_tiny_float_shape_does_not_force_affine_mapping(self):
        rel=m.report(fixture())["relationship"]
        self.assertIsNone(rel["wedge_player_090_affine_to_player_030_three_points_candidate"])
        self.assertIsNone(rel["wedge_player_090_affine_to_ball_component_0_three_points_candidate"])
        self.assertFalse(rel["three_point_affinity_proves_physical_mapping"])

    def test_nonfinite_scalar_gives_unknown_relation_not_false(self):
        x=fixture()
        words=list(x[6]["whole_record"])
        words[0x90//4]=0x7fc00000
        x[6]["whole_record"]=tuple(words)
        rel=m.report(x)["relationship"]
        self.assertIsNone(rel["wedge_player_090_affine_to_player_030_three_points_candidate"])
        self.assertIsNone(rel["wedge_player_030_minus_090_is_numeric_constant"])
        self.assertEqual(rel["wedge_player_030_vs_090_float_order_by_phase_W5_W6_W7"][1],
                         "unclassified")

    def test_source_owner_hole_config_mismatch_abstain(self):
        for key,value in (("selected_index",2),("hole",4),("cfg_c4",9)):
            x=fixture();x[6][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):m.report(x)

    def test_selected_ball_start_pin_guard_abstain(self):
        for key in ("ball_object_0x030","source_current_start","pin"):
            x=fixture()
            if key=="pin":x[6]["pin"]=(1,2,3)
            else:x[6]["triplets"][key]=(1,2,3)
            # Only candidate ball changes are allowed; test actual controls.
            if key=="ball_object_0x030":
                x[6]["triplets"][key]=(1,2)  # bad vector width
            with self.subTest(key=key),self.assertRaises(ValueError):m.report(x)

    def test_source_record_51_word_gate(self):
        x=fixture();x[7]["whole_record"]=x[7]["whole_record"][:50]
        with self.assertRaises(ValueError):m.report(x)

    def test_bad_float_nonfinite_rejected_as_shape_not_process_failure(self):
        x=fixture()
        v=list(x[6]["whole_record"]);v[0x30//4]=0x7fc00000
        x[6]["whole_record"]=tuple(v)
        row=m.report(x)["fields"][0]
        self.assertFalse(row["bounded_f32_candidate_in_wedge_5_6_7"][1])
        self.assertEqual(row["wedge_f32_direction_steps"],["unclassified","unclassified"])

    def test_private_output_contains_no_game_data_words(self):
        data=json.dumps(m.report(fixture()))
        for forbidden in ("9000A010","owner_ids","whole_record","mem1.raw",
                          "private_path","raw_float","0x9000","sha256"):
            self.assertNotIn(forbidden,data)
        self.assertFalse(m.report(fixture())["allowed_to_publish"])

    def test_sha_gate_before_any_snapshot_read(self):
        with patch.object(m.base,"read_samples",side_effect=ValueError("bad SHA")):
            with self.assertRaises(ValueError):
                m.analyze(Path("secret-local-bank"))

    def test_isolated_cli_help(self):
        program=ROOT/"scripts"/"audit_p0_seven_record_two_word_roles_private.py"
        run=subprocess.run([sys.executable,"-I",str(program),"--help"],
                           capture_output=True,text=True,timeout=20,cwd=ROOT)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertIn("--archive",run.stdout)

if __name__=="__main__":
    unittest.main()
