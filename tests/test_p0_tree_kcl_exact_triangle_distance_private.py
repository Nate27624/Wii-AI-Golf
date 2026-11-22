"""Synthetic point-to-triangle exact distances and original KCL source gates."""
from __future__ import annotations
import importlib.util
import math
from pathlib import Path
import sys
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location(
    "kcl_exact",SCRIPTS/"p0_tree_kcl_exact_triangle_distance_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def geometry():
    tri1=((0.,0.,0.),(10.,0.,0.),(0.,0.,10.))
    tri2=((0.,0.,0.),(0.,10.,0.),(0.,0.,10.))
    far=((10000.,0.,10000.),(10001.,0.,10000.),(10000.,0.,10001.))
    return tri1,tri2,far


def bound(tri,face_y,flag):
    return (
        min(v[0] for v in tri),max(v[0] for v in tri),
        min(v[2] for v in tri),max(v[2] for v in tri),
        min(v[1] for v in tri),max(v[1] for v in tri),
        face_y,flag,tri,
    )


def fixtures():
    h,v,far=geometry()
    faces=[bound(h,1.,1),bound(v,0.,4)]
    faces += [bound(far,1.,12)]*2496
    trees=[(1.,1.,1.)]*47+[(1000.,0.,1000.)]*47
    controls=[(1.,0.,1.),(2.,0.,2.)]
    return trees,controls,faces


class KclActualTriangleTests(unittest.TestCase):
    def test_interior_3d_triangle_distance(self):
        a,b,c=geometry()[0]
        self.assertAlmostEqual(m.triangle_sq_3d((2.,5.,2.),a,b,c),25.)
        self.assertAlmostEqual(m.triangle_sq_3d((2.,0.,2.),a,b,c),0.)

    def test_outside_triangle_aabb_is_zero_but_real_dist_positive(self):
        a,b,c=geometry()[0]
        p=(10.,0.,10.)
        self.assertAlmostEqual(m.triangle_sq_3d(p,a,b,c),50.)
        self.assertAlmostEqual(m.horizontal_projected_sq(p,(a,b,c)),50.)
        bounds=bound((a,b,c),1.,1)
        self.assertEqual(m.broad.projected_bbox_lower_bound(p,bounds),0.)

    def test_near_triangle_vertex_and_edges(self):
        a,b,c=geometry()[0]
        self.assertAlmostEqual(m.triangle_sq_3d((12.,0.,0.),a,b,c),4.)
        self.assertAlmostEqual(m.horizontal_projected_sq((12.,0.,0.),(a,b,c)),4.)
        self.assertAlmostEqual(m.triangle_sq_3d((-2.,0.,-3.),a,b,c),13.)

    def test_vertical_projected_triangle_line_segment_fallback(self):
        a,b,c=geometry()[1]
        self.assertAlmostEqual(m.horizontal_projected_sq((3.,3.,3.),(a,b,c)),9.)
        self.assertAlmostEqual(m.triangle_sq_3d((3.,3.,3.),a,b,c),9.)
        self.assertIsNone(m.project_barycentric((0.,3.),
                           (a[0],a[2]),(b[0],b[2]),(c[0],c[2])))

    def test_ground_y_interpolation_only_when_projected_inside(self):
        a,b,c=geometry()[0]
        self.assertAlmostEqual(m.ground_clearance((2.,4.,2.),(a,b,c)),4.)
        self.assertAlmostEqual(m.ground_clearance((2.,-5.,2.),(a,b,c)),-5.)
        self.assertIsNone(m.ground_clearance((9.,0.,9.),(a,b,c)))

    def test_degenerate_3d_triangle_uses_segments(self):
        a,b,c=(0.,0.,0.),(5.,0.,0.),(10.,0.,0.)
        self.assertAlmostEqual(m.triangle_sq_3d((5.,2.,0.),a,b,c),4.)

    def test_source_parser_backward_compatibility_default_eight_fields(self):
        import importlib.util
        file=SCRIPTS.parent/"tests"/"test_p0_tree_kcl_spatial_broadphase_private.py"
        spec2=importlib.util.spec_from_file_location("kcl_fixture_test",file)
        test=importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(test)
        data=test.kcl_fixture()
        plain=m.broad.parse_candidate(data,0,required_prisms=3)
        verts=m.broad.parse_candidate(data,0,required_prisms=3,include_vertices=True)
        self.assertIsNotNone(plain)
        self.assertIsNotNone(verts)
        self.assertEqual(len(plain[0][0]),8)
        self.assertEqual(len(verts[0][0]),9)
        self.assertEqual(len(verts[0][0][8]),3)
        self.assertEqual(plain[1],verts[1])

    def test_full_94_tree_synthetic_source_aggregation(self):
        trees,controls,faces=fixtures()
        result=m.summarize(trees,controls,faces)
        self.assertEqual(result["source_94_tree_records"],94)
        self.assertEqual(result["source_2498_kcl_prism_faces"],2498)
        allface=result["actual_triangle_distance_profiles"]["all_faces"]
        self.assertGreaterEqual(
            allface["tree_nearest_actual_triangle"]
            ["points_within_actual_3d_triangle_windows"]["5"],47)
        self.assertEqual(result["terrain_vertical_surface_clearance"]["trees"]
                         ["points_with_xz_inside_any_near_horizontal_face"],47)
        self.assertEqual(result["terrain_vertical_surface_clearance"]["tee"]
                         ["points_with_xz_inside_any_near_horizontal_face"],1)
        self.assertEqual(result["terrain_vertical_surface_clearance"]["pin"]
                         ["points_with_xz_inside_any_near_horizontal_face"],1)
        self.assertFalse(result["native_tree_collider_shape_verified"])
        self.assertFalse(result["ball_contact_response_verified"])
        self.assertFalse(result["training_approved"])

    def test_exact_lower_bound_gaps_nonnegative(self):
        trees,controls,faces=fixtures()
        report=m.nearest_profiles(trees[:1],faces)
        self.assertGreaterEqual(
            report["actual_minus_triangle_aabb_lower_bound_3d_source_units"]["min"],-0.001)
        self.assertGreaterEqual(
            report["actual_minus_triangle_aabb_lower_bound_xz_source_units"]["min"],-0.001)

    def test_invalid_counts_and_3d_source_points_fail_closed(self):
        trees,controls,faces=fixtures()
        for t,c,f in ((trees[:-1],controls,faces),
                      (trees,controls[:-1],faces),
                      (trees,controls,faces[:-1])):
            with self.assertRaises(ValueError):
                m.summarize(t,c,f)
        trees[0]=(float("nan"),0.,0.)
        with self.assertRaises(ValueError):
            m.summarize(trees,controls,faces)

    def test_aggregate_only_no_physics_or_private_coordinate_export(self):
        import json
        trees,controls,faces=fixtures()
        result=m.summarize(trees,controls,faces)
        txt=json.dumps(result)
        self.assertNotIn("original_triangle_vertices",txt)
        self.assertNotIn("tree_positions",txt)
        self.assertNotIn("0x90000000",txt)
        self.assertFalse(result["native_kcl_octree_reachability_verified"])
        self.assertTrue(result["actual_triangle_proximity_is_not_collision_ownership"])


if __name__=="__main__":
    unittest.main()
