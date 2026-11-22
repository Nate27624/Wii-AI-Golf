"""Synthetic-only source KCL reconstruction vs tree position broadspatial falsifiers."""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import struct
import sys
import unittest

DIR=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(DIR))
spec=importlib.util.spec_from_file_location(
    "tree_kcl_spatial",DIR/"p0_tree_kcl_spatial_broadphase_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def kcl_fixture(attrs=(1,6,12)):
    """Three triangles from structurally valid original-format KCL."""
    po,no,ps=0x3c,0x60,0x90
    octo=ps+16*len(attrs)
    out=bytearray(max(octo+16,512))
    struct.pack_into(">4I",out,0,po,no,ps-16,octo)
    struct.pack_into(">f",out,0x10,30.)
    struct.pack_into(">3I",out,0x2C,0,0,0)
    for i,p in enumerate(((0.,0.,0.),(10.,0.,0.),(0.,0.,10.))):
        struct.pack_into(">3f",out,po+i*12,*p)
    for i,n in enumerate(((0.,1.,0.),(0.,0.,1.),(1.,0.,0.),
                          (math.sqrt(.5),0.,math.sqrt(.5)))):
        struct.pack_into(">3f",out,no+i*12,*n)
    for i,attr in enumerate(attrs):
        struct.pack_into(">f6H",out,ps+i*16,1.,0,0,1,2,3,attr)
    return out


def triangles_fixture():
    near=(-4.,4.,-4.,4.,0.,130.,0.1,4)
    far=(10000.,10001.,10000.,10001.,0.,10.,1.0,1)
    return [near]+[far]*2497


def tree_fixture():
    return [(0.,0.,0.)]*47+[(1000.,0.,1000.)]*47


class TreeKclSpatialTests(unittest.TestCase):
    def test_exact_source_categorical_inventory(self):
        self.assertEqual(sum(m.EXPECTED_FLAGS.values()),2498)
        self.assertEqual(m.COUNT,94)
        self.assertEqual(m.STRIDE,84)

    def test_true_kcl_face_reconstruction_from_prism_basis(self):
        result=m.parse_candidate(kcl_fixture(),0,required_prisms=3)
        self.assertIsNotNone(result)
        triangles,hist=result
        self.assertEqual(len(triangles),3)
        self.assertEqual(hist,{1:1,6:1,12:1})
        for t in triangles:
            self.assertEqual(t[6],1.0)
            self.assertEqual(t[4],0.)
            self.assertEqual(t[5],0.)
            self.assertGreater(t[1]-t[0],0.)
            self.assertGreater(t[3]-t[2],0.)

    def test_original_native_requires_full_2498(self):
        self.assertIsNone(m.parse_candidate(kcl_fixture(),0))

    def test_truncated_or_bad_prism_refuses(self):
        buf=kcl_fixture()
        self.assertIsNone(m.parse_candidate(buf[:128],0,required_prisms=3))
        bad=kcl_fixture()
        struct.pack_into(">H",bad,0x90+4,0xffff)
        self.assertIsNone(m.parse_candidate(bad,0,required_prisms=3))

    def test_invalid_source_normal_fails(self):
        bad=kcl_fixture()
        struct.pack_into(">f",bad,0x60+4,20.)
        self.assertIsNone(m.parse_candidate(bad,0,required_prisms=3))

    def test_invalid_nan_geometry_fails(self):
        bad=kcl_fixture()
        struct.pack_into(">f",bad,0x90,float("nan"))
        self.assertIsNone(m.parse_candidate(bad,0,required_prisms=3))

    def test_bbox_distance_is_lower_bound_not_geometric_contact(self):
        t=triangles_fixture()[0]
        self.assertEqual(m.projected_bbox_lower_bound((0.,0.,0.),t),0.)
        self.assertEqual(m.projected_bbox_lower_bound((10.,0.,0.),t),6.)
        self.assertAlmostEqual(m.projected_bbox_lower_bound((10.,0.,10.),t),
                               math.hypot(6.,6.))
        # y intentionally ignored, as this is only horizontal lower bound.
        self.assertEqual(m.projected_bbox_lower_bound((0.,1000.,0.),t),0.)

    def test_vertical_nearby_counts_and_controls(self):
        r=m.summarize(tree_fixture(),triangles_fixture(),
                      [(10.,0.,0.),(2000.,0.,2000.)])
        self.assertEqual(r["candidate_vertical_faces"],1)
        p=next(x for x in r["spatial_window_profiles"]
               if x["xz_aabb_lower_bound_window_source_units"]==25.
               and x["face_max_height_above_tree_centre_min_source_units"]==75.)
        self.assertEqual(p["trees_with_one_or_more_candidate_vertical_faces"],47)
        self.assertEqual(p["trees_with_five_or_more_candidate_vertical_faces"],0)
        self.assertEqual(p["median_candidate_faces_per_tree"],0.5)
        self.assertEqual(p["tee_and_pin_control_face_counts"],[1,0])
        self.assertEqual(p["candidate_flags_tallied_with_repetition"],{"0x0004":47})
        self.assertFalse(p["true_triangle_distance_verified"])
        self.assertFalse(r["tree_specific_collision_mesh_verified"])
        self.assertFalse(r["training_approved"])

    def test_elevation_and_normal_filters(self):
        hs=m.contacts_lower_bound((0.,150.,0.),triangles_fixture())
        self.assertEqual(sum(hs[(200.,0.)].values()),0)
        self.assertEqual(sum(hs[(200.,75.)].values()),0)

    def test_wrong_counts_or_nan_trees_fail_closed(self):
        triangles=triangles_fixture()
        controls=[(0.,0.,0.),(5.,0.,5.)]
        with self.assertRaises(ValueError):
            m.summarize(tree_fixture()[:-1],triangles,controls)
        with self.assertRaises(ValueError):
            m.summarize(tree_fixture(),triangles[:-1],controls)
        trees=tree_fixture()
        trees[0]=(float("nan"),0.,0.)
        with self.assertRaises(ValueError):
            m.summarize(trees,triangles,controls)

    def test_never_exposes_private_coordinates_or_hitbox_radii(self):
        import json
        r=m.summarize(tree_fixture(),triangles_fixture(),
                      [(10.,0.,0.),(2000.,0.,2000.)])
        text=json.dumps(r)
        self.assertNotIn("tree_positions",text)
        self.assertNotIn("0x90000000",text)
        self.assertNotIn("radii",text)
        self.assertFalse(r["candidate_kcl_octree_active_for_ball_verified"])


if __name__=="__main__":
    unittest.main()
