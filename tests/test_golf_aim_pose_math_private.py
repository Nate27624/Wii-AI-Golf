"""Synthetic B0-B3 angle/rotation/quaternion tests, no game RAM or ROM."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_golf_aim_pose_math_private as x


def sample(angle=2.22,location=1.0,qangle=0.65,scalar=5,confound=2):
    return {
        "selected_index":0,"hole":1,
        "angle":angle,
        "rot2":(math.sin(angle),math.cos(angle),
                -math.cos(angle),math.sin(angle)),
        "location_like":(-location,location,3*location),
        "quaternion_a":(0.0,math.sin(qangle),0.0,math.cos(qangle)),
        "quaternion_b":(math.sin(qangle/4),0.0,0.0,math.cos(qangle/4)),
        "scalar":scalar,
        "idle_confound":confound,
        "other_slot_words":((0,)*len(x.FIELD_OFFSETS),)*3,
    }


def stages():
    return [
        sample(),
        sample(confound=3),
        sample(angle=1.85,location=1.4,qangle=0.52,scalar=6,confound=4),
        sample(angle=1.85,location=1.4,qangle=0.52,scalar=6,confound=4),
    ]


class GolfAimPoseMathTests(unittest.TestCase):
    def test_coupled_angle_rotation_and_quaternion_shape(self):
        out=x.summarize(stages(),visible_aim=True,operator_same_session=True,
                        bank_pairs_distinct=True)
        self.assertTrue(out["pose_like_structure_supported_by_no_shot_evidence"])
        self.assertTrue(out["rotation2_matrix_consistent_all_phases"])
        self.assertTrue(out["two_quaternion_like_groups_near_unit_norm_all_phases"])
        self.assertTrue(out["unselected_slots_static_in_target_offsets"])
        self.assertTrue(out["selected_pose_fields_stable_in_idle_controls"])
        self.assertTrue(out["selected_pose_fields_changed_during_visible_aim"])
        self.assertEqual(out["phase_changes"][1]["location_like_vec3_component_change_count"],3)
        self.assertEqual(out["phase_changes"][1]["first_quaternion_component_change_count"],2)
        self.assertFalse(out["typed_actual_aim_angle_verified"])
        self.assertFalse(out["approved_for_training"])

    def test_corrupt_rotation_sign_falsifies_structure(self):
        data=stages()
        data[2]["rot2"]=(0.0,0.0,0.0,0.0)
        out=x.summarize(data,visible_aim=True,operator_same_session=True,
                        bank_pairs_distinct=True)
        self.assertFalse(out["rotation2_matrix_consistent_all_phases"])
        self.assertFalse(out["pose_like_structure_supported_by_no_shot_evidence"])

    def test_nonunit_quaternion_falsifies_structure(self):
        data=stages()
        data[3]["quaternion_a"]=(2.0,0.0,0.0,0.0)
        out=x.summarize(data,visible_aim=True,operator_same_session=True,
                        bank_pairs_distinct=True)
        self.assertFalse(out["two_quaternion_like_groups_near_unit_norm_all_phases"])
        self.assertFalse(out["pose_like_structure_supported_by_no_shot_evidence"])

    def test_wrong_slot_and_hole_fails_closed(self):
        for field,value in [("selected_index",1),("hole",2)]:
            data=stages()
            data[1][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                x.summarize(data)

    def test_nonfinite_values_fail_closed(self):
        for field,value in [("angle",float("nan")),
                            ("quaternion_a",(float("inf"),0,0,0))]:
            data=stages()
            data[1][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                x.summarize(data)

    def test_missing_provenance_never_promotes_even_plausible_structure(self):
        data=stages()
        for flags in ({},{"visible_aim":True},{"operator_same_session":True},
                      {"bank_pairs_distinct":True}):
            with self.subTest(flags=flags):
                report=x.summarize(data,**flags)
                self.assertFalse(report[
                    "pose_like_structure_supported_by_no_shot_evidence"])

    def test_unselected_slot_change_rejects_positive_specificity(self):
        data=stages()
        others=list(data[2]["other_slot_words"])
        p=list(others[1]);p[3]=1;others[1]=tuple(p)
        data[2]["other_slot_words"]=tuple(others)
        report=x.summarize(data,visible_aim=True,operator_same_session=True,
                           bank_pairs_distinct=True)
        self.assertFalse(report["unselected_slots_static_in_target_offsets"])
        self.assertFalse(report["pose_like_structure_supported_by_no_shot_evidence"])

    def test_idle_angle_change_violates_no_shot_stability(self):
        data=stages()
        data[1]=sample(angle=1.92,location=1.4,qangle=0.62,scalar=6)
        report=x.summarize(data,visible_aim=True,operator_same_session=True,
                           bank_pairs_distinct=True)
        self.assertFalse(report["selected_pose_fields_stable_in_idle_controls"])
        self.assertFalse(report["pose_like_structure_supported_by_no_shot_evidence"])

    def test_no_raw_float_array_or_heap_address_in_report(self):
        report=x.summarize(stages(),visible_aim=True,operator_same_session=True,
                           bank_pairs_distinct=True)
        output=json.dumps(report)
        for forbidden in ('"rot2"', '"location_like"', '"quaternion_a"',
                          '"quaternion_b"', '"angle"', '"scalar"', '0x9100',
                          '"other_slot_words"', '"idle_confound"', 'mem2.raw'):
            self.assertNotIn(forbidden,output)
        for key in ("typed_quaternion_or_position_semantics_verified",
                    "club_head_pose_verified","real_swing_power_verified",
                    "ball_motion_or_world_xyz_verified",
                    "allowed_to_publish","approved_for_training"):
            self.assertFalse(report[key])

    def test_wrong_phase_count_fails(self):
        with self.assertRaises(ValueError):
            x.summarize(stages()[:3])

if __name__=="__main__":
    unittest.main()
