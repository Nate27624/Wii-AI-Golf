"""P0 original 72/22 resource-vs-ground material source join falsifiers."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import sys
import unittest

DIR=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(DIR))
spec=importlib.util.spec_from_file_location(
    "p0_surface_join",DIR/"p0_tree_kcl_surface_group_join_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def synthetic_rows(swapped=0,*,nonuniform=18):
    rows=[]
    for i in range(94):
        group=0 if i<72 else 1
        material=4 if i<72 else 2
        if i<swapped:
            material=2 if material==4 else 4
        if 72<=i<72+swapped:
            material=4
        scale=(1.,1.5,2.) if i<nonuniform else (2.,2.,2.)
        rows.append((
            [0x80000011,0x80000022][group],
            [0x80000033,0x80000044][group],
            scale,material,0.1+i*.01,
        ))
    return rows


class NativeTreeSurfaceJoinTests(unittest.TestCase):
    def test_exact_matching_72_22_source_joint_group(self):
        result=m.group_rows(synthetic_rows())
        self.assertTrue(result["per_tree_group_to_surface_category_correspondence_exact"])
        self.assertEqual(len(result["source_tree_group_rows"]),2)
        large,small=result["source_tree_group_rows"]
        self.assertEqual(large["tree_count"],72)
        self.assertEqual(small["tree_count"],22)
        self.assertEqual(large["nearest_ground_kcl_prism_flag_counts"],{"0x0002":0,"0x0004":72})
        self.assertEqual(small["nearest_ground_kcl_prism_flag_counts"],{"0x0002":22,"0x0004":0})
        self.assertEqual(large["nonuniform_xyz_scale_count"],18)
        self.assertFalse(result["native_ball_response_proven"])

    def test_equal_marginal_not_equal_joint(self):
        row=synthetic_rows()
        large=list(row[0])
        small=list(row[72])
        large[3]=2
        small[3]=4
        row[0]=tuple(large)
        row[72]=tuple(small)
        r=m.group_rows(row)
        self.assertFalse(r["per_tree_group_to_surface_category_correspondence_exact"])
        self.assertEqual(r["source_tree_group_rows"][0]
                         ["nearest_ground_kcl_prism_flag_counts"],
                         {"0x0002":1,"0x0004":71})
        self.assertEqual(r["source_tree_group_rows"][1]
                         ["nearest_ground_kcl_prism_flag_counts"],
                         {"0x0002":21,"0x0004":1})

    def test_bad_flag_counts_fail_closed(self):
        row=synthetic_rows()
        row[0]=(*row[0][:3],4,row[0][4])
        row[72]=(*row[72][:3],4,row[72][4])
        with self.assertRaises(ValueError):
            m.group_rows(row)

    def test_unknown_group_numbers_fail_closed(self):
        row=synthetic_rows()
        row[0]=(0xDEADBEEF,0xABACABAD,*row[0][2:])
        with self.assertRaises(ValueError):
            m.group_rows(row)

    def test_missing_or_extra_tree_fail_closed(self):
        row=synthetic_rows()
        for bad in (row[:-1],[*row,row[0]]):
            with self.assertRaises(ValueError):
                m.group_rows(bad)

    def test_nonfinite_scale_or_distance_fail_closed(self):
        row=synthetic_rows()
        row[0]=(row[0][0],row[0][1],
                (float("nan"),2.,2.),4,.01)
        with self.assertRaises(ValueError):
            m.group_rows(row)
        row=synthetic_rows()
        row[0]=(*row[0][:4],float("inf"))
        with self.assertRaises(ValueError):
            m.group_rows(row)

    def test_no_synthetic_source_words_leak(self):
        result=json.dumps(m.group_rows(synthetic_rows()))
        for private in ("0x80000011","0x80000022","0x80000033","0x80000044"):
            self.assertNotIn(private,result)
        self.assertNotIn("source_tree_positions",result)
        self.assertNotIn("tree_hitbox_radii",result)

    def test_no_collider_promoted_from_perfect_association(self):
        result=m.group_rows(synthetic_rows())
        self.assertTrue(result["per_tree_group_to_surface_category_correspondence_exact"])
        self.assertFalse(result["tree_model_class_identity_proven"])
        self.assertFalse(result["tree_collision_object_geometry_proven"])
        self.assertFalse(result["native_ball_response_proven"])
        self.assertFalse(result["training_approved"])

    def test_nearest_face_flags_are_source_geom(self):
        # Ground at (y=0), vertical caller remains separate physics proof.
        tri=((0.,0.,0.),(10.,0.,0.),(0.,0.,10.))
        f=(0.,10.,0.,10.,0.,0.,1.,4,tri)
        surface,d,idx=m.nearest_surface((1.,2.,1.),[f])
        self.assertEqual(surface,4)
        self.assertAlmostEqual(d,2.)
        self.assertEqual(idx,0)

    def test_output_group_ids_do_not_depend_on_raw_word_values(self):
        a=m.group_rows(synthetic_rows())
        rows=synthetic_rows()
        normalized=[
            (123456 if r[0]==0x80000011 else 987654,
             111222 if r[1]==0x80000033 else 555666,
             r[2],r[3],r[4]) for r in rows]
        b=m.group_rows(normalized)
        self.assertEqual(a,b)


if __name__=="__main__":
    unittest.main()
