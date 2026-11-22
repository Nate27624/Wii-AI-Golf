"""Synthetic original source trees versus KCL AABB frame and filtering tests."""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import sys
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location(
    "tree_kcl_frame",SCRIPTS/"p0_tree_kcl_frame_diagnostics_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def triangles(*,vertical_top=130.,include_near=True):
    vertical=(-4.,4.,-4.,4.,0.,vertical_top,0.1,4)
    low_ground=(-4.,4.,-4.,4.,-1.,1.,1.,2)
    pin_ground=(996.,1004.,996.,1004.,-1.,1.,1.,6)
    distant=(10000.,10001.,10000.,10001.,-1.,10.,1.,1)
    return ([vertical,low_ground,pin_ground] if include_near else [
        distant,distant,distant])+[distant]*2495


def tree_positions(*,shift=0.):
    return [(0.+shift,0.,0.+shift)]*47+[(1000.+shift,0.,1000.+shift)]*47


def anchors():
    return [(0.,0.,0.),(1000.,0.,1000.)]


class KclFrameDiagnosticTests(unittest.TestCase):
    def test_bbox_3d_lower_bound_uses_vertical_axis(self):
        t=triangles()[0]
        self.assertEqual(m.bbox_distance_3d((0.,0.,0.),t),0.)
        self.assertEqual(m.bbox_distance_3d((0.,150.,0.),t),20.)
        self.assertEqual(m.bbox_distance_3d((10.,150.,10.),t),
                         math.sqrt(6*6+20*20+6*6))
        self.assertEqual(m.broad.projected_bbox_lower_bound((0.,150.,0.),t),0.)

    def test_zero_range_gap_and_nonoverlap(self):
        self.assertEqual(m.axis_gap(0.,10.,12.,13.),2.)
        self.assertEqual(m.axis_gap(0.,10.,8.,13.),0.)
        self.assertEqual(m.axis_gap(20.,30.,8.,13.),7.)

    def test_simple_kcl_positive_tee_pin_control(self):
        r=m.summarize(tree_positions(),anchors(),triangles())
        self.assertTrue(r["tee_pin_both_have_3d_bbox_lower_bound_at_most_25"])
        self.assertFalse(r["tee_pin_check_establishes_frame_alignment"])
        self.assertEqual(r["face_category_profiles"]["near_vertical"]["prism_count"],1)
        self.assertEqual(r["face_category_profiles"]["near_horizontal"]["prism_count"],2497)
        all_face=r["face_category_profiles"]["all_faces"]
        self.assertEqual(all_face["trees"]["point_counts_within_3d_lower_bound_windows"]["25"],94)
        self.assertEqual(len(all_face["tee_and_pin_controls"]),2)
        self.assertEqual(all_face["tee_and_pin_controls"][0]
                         ["nearest_triangle_3d_aabb_lower_bound_source_units"]["min"],0.)

    def test_face_filter_cascade_without_height_gating(self):
        result=m.summarize(tree_positions(),anchors(),triangles())
        cascade=result["vertical_face_filter_cascade"]["50"]
        self.assertEqual(cascade["tree_count_near_vertical_no_elevation_gate"],47)
        self.assertEqual(cascade["tree_count_near_vertical_with_original_elevation_gate"],47)

    def test_original_elevation_gate_alone_can_exclude_nearby_vertical(self):
        pts=[(p[0],150.,p[2]) for p in tree_positions()]
        r=m.summarize(pts,anchors(),triangles())
        cascade=r["vertical_face_filter_cascade"]["50"]
        self.assertEqual(cascade["tree_count_near_vertical_no_elevation_gate"],47)
        self.assertEqual(cascade["tree_count_near_vertical_with_original_elevation_gate"],0)
        self.assertFalse(r["tree_hitbox_geometry_verified"])

    def test_coordinate_frame_shift_diagnosis(self):
        r=m.summarize(tree_positions(shift=20000.),anchors(),triangles())
        self.assertGreater(r["source_tree_to_kcl_bbox_axis_alignment"]["x"]
                           ["tree_kcl_aabb_axis_gap_source_units"],0.)
        self.assertGreater(r["source_tree_to_kcl_bbox_axis_alignment"]["z"]
                           ["tree_kcl_aabb_axis_gap_source_units"],0.)
        self.assertTrue(r["tee_pin_both_have_3d_bbox_lower_bound_at_most_25"])
        self.assertEqual(r["face_category_profiles"]["all_faces"]["trees"]
                         ["point_counts_within_xz_lower_bound_windows"]["1000"],0)

    def test_negative_control_tee_pin_not_always_near_mesh(self):
        other=[(25000.,0.,25000.),(26000.,0.,26000.)]
        result=m.summarize(tree_positions(),other,triangles())
        self.assertFalse(result["tee_pin_both_have_3d_bbox_lower_bound_at_most_25"])

    def test_empty_face_category_is_not_fabricated_as_colliders(self):
        r=m.summarize(tree_positions(),anchors(),[
            (-4.,4.,-4.,4.,-1.,1.,1.,1)]*2498)
        self.assertEqual(r["face_category_profiles"]["near_vertical"]["prism_count"],0)
        self.assertIsNone(r["face_category_profiles"]["near_vertical"]["trees"])
        self.assertIsNone(r["face_category_profiles"]["near_vertical"]["tee_and_pin_controls"][0])
        self.assertFalse(r["candidate_kcl_in_active_golf_ball_octree_verified"])

    def test_invalid_counts_abstain(self):
        with self.assertRaises(ValueError):
            m.summarize(tree_positions()[:-1],anchors(),triangles())
        with self.assertRaises(ValueError):
            m.summarize(tree_positions(),anchors(),triangles()[:-1])
        with self.assertRaises(ValueError):
            m.summarize(tree_positions(),anchors()[:-1],triangles())

    def test_invalid_values_and_aabb_order_abstain(self):
        bad=list(tree_positions())
        bad[0]=(float("nan"),0.,0.)
        with self.assertRaises(ValueError):
            m.summarize(bad,anchors(),triangles())
        ts=triangles()
        ts[0]=(4.,-4.,-4.,4.,0.,130.,0.1,4)
        with self.assertRaises(ValueError):
            m.summarize(tree_positions(),anchors(),ts)

    def test_output_never_claims_true_distance_or_hitboxes(self):
        import json
        r=m.summarize(tree_positions(),anchors(),triangles())
        text=json.dumps(r)
        self.assertNotIn("tree_positions",text)
        self.assertNotIn("0x9000",text)
        self.assertNotIn("native_tree_hitbox_radius",text)
        self.assertFalse(r["tree_hitbox_geometry_verified"])
        self.assertFalse(r["native_ball_tree_response_verified"])
        self.assertFalse(r["training_approved"])


if __name__=="__main__":
    unittest.main()
