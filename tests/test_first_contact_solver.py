"""Synthetic regression only; never evidence of native Wii trajectory parity."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

FILE=Path(__file__).resolve().parents[1]/"src/wii_ai_golf/physics/first_contact.py"
spec=importlib.util.spec_from_file_location("s003_first_contact_solver", FILE)
fc=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=fc
spec.loader.exec_module(fc)


def ground():
    return fc.Triangle((-10,0,-10),(0,0,10),(10,0,-10),face_id=9,material="synthetic")


class FirstContactTests(unittest.TestCase):
    def test_point_face(self):
        h=fc.segment_hit((0,5,0),(0,-1,0),ground())
        self.assertAlmostEqual(h[0],5/6)
        self.assertEqual(h[1],(0,0,0))
        self.assertEqual(h[3],"face")

    def test_swept_face(self):
        h=fc.segment_hit((0,5,0),(0,-1,0),ground(),.5)
        self.assertAlmostEqual(h[0],.75)
        self.assertAlmostEqual(h[1][1],.5)
        self.assertAlmostEqual(h[2][1],0)

    def test_edge(self):
        tri=fc.Triangle((0,0,0),(2,0,0),(0,2,0))
        h=fc.segment_hit((1,-1,1),(1,-1,-1),tri,1.2)
        self.assertIsNotNone(h)
        self.assertEqual(h[3],"edge")
        self.assertAlmostEqual(h[2][1],0)

    def test_vertex(self):
        tri=fc.Triangle((0,0,0),(2,0,0),(0,2,0))
        h=fc.segment_hit((-1,-1,1),(-1,-1,-1),tri,1.5)
        self.assertIsNotNone(h)
        self.assertEqual(h[3],"vertex")
        self.assertEqual(h[2],(0,0,0))

    def test_winding_and_vertical(self):
        tri=fc.Triangle((0,0,0),(0,0,2),(0,2,0))
        for t in (tri,fc.Triangle(tri.c,tri.b,tri.a)):
            h=fc.segment_hit((-1,.5,.5),(1,.5,.5),t,.5)
            self.assertAlmostEqual(h[0],.25)
            self.assertEqual(h[3],"face")

    def test_tunnel_and_competing_faces(self):
        upper=fc.Triangle((-10,1,-10),(0,1,10),(10,1,-10),face_id=7)
        h1=fc.segment_hit((0,5,0),(0,-10,0),upper,.5)
        h0=fc.segment_hit((0,5,0),(0,-10,0),ground(),.5)
        self.assertLess(h1[0],h0[0])

    def test_miss(self):
        self.assertIsNone(fc.segment_hit((20,5,20),(20,-5,20),ground(),.5))

    def test_initial_overlap_fails_closed(self):
        with self.assertRaises(ValueError):
            fc.segment_hit((0,.2,0),(0,-3,0),ground(),.5)

    def test_negative_radius_fails_closed(self):
        with self.assertRaises(ValueError):
            fc.segment_hit((0,5,0),(0,-5,0),ground(),-.5)

    def test_bad_geometry_fails_closed(self):
        with self.assertRaises(ValueError):
            fc.Triangle((0,0,0),(1,0,0),(2,0,0))

    def test_motion_sequence(self):
        n=fc.step_airborne(fc.State((0,1,0),(.01,.05,0)))
        self.assertAlmostEqual(n.position[0],.01)
        self.assertAlmostEqual(n.position[1],1.048)
        self.assertAlmostEqual(n.velocity[1],.048*.999000013)

    def test_unknown_tree_abstains(self):
        r=fc.predict_first_contact((0,1,0),(0,-.1,0),[ground()])
        self.assertEqual(r["status"],"ABSTAIN_TREE_CLEARANCE_UNKNOWN")

    def test_point_vs_sphere_prediction(self):
        kw={"acceleration":(0,0,0),"assume_tree_free":True,"max_steps":10}
        point=fc.predict_first_contact((0,5,0),(0,-1,0),[ground()],**kw)
        sphere=fc.predict_first_contact((0,5,0),(0,-1,0),[ground()],
                                        contact_mode="swept_kcol_query_0p5",**kw)
        self.assertEqual(point["status"],"PROVISIONAL_FIRST_CONTACT")
        self.assertLess(sphere["time_numerical_steps"],point["time_numerical_steps"])
        self.assertAlmostEqual(sphere["ball_center_xyz"][1],.5)
        self.assertAlmostEqual(point["ball_center_xyz"][1],0)
        self.assertFalse(point["training_approved"])

    def test_no_hit_horizon(self):
        r=fc.predict_first_contact((0,5,0),(0,1,0),[ground()],
                                   acceleration=(0,0,0),assume_tree_free=True,max_steps=10)
        self.assertEqual(r["status"],"NO_CONTACT_IN_HORIZON")

    def test_material_is_uninterpreted(self):
        r=fc.predict_first_contact((0,5,0),(0,-1,0),[ground()],
                                   acceleration=(0,0,0),assume_tree_free=True,max_steps=10)
        self.assertEqual(r["material_uninterpreted"],"synthetic")
        self.assertEqual(r["face_id"],9)

    def test_obj_local_read(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"mesh.obj"
            p.write_text("v -2 0 -2\nv 2 0 -2\nv 2 0 2\nv -2 0 2\nusemtl unknown_material\nf 1 2 3 4\n")
            mesh=fc.read_obj(p)
            self.assertEqual(len(mesh),2)
            self.assertEqual(mesh[1].material,"unknown_material")

    def test_obj_bad_indices(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"mesh.obj"
            p.write_text("v 0 0 0\nf 1 2 3\n")
            with self.assertRaises(ValueError):
                fc.read_obj(p)

    def test_spin_force_explicit_but_unverified(self):
        s=fc.State((0,1,0),(1,1,0),speed_like=2,lift=2,lateral=3,
                   spin_axis=(0,0,1))
        n=fc.step_airborne(s)
        self.assertAlmostEqual(n.lift,2*.9985)
        self.assertAlmostEqual(n.lateral,3*.997)



    def test_explicit_spin_does_not_silently_disappear(self):
        with self.assertRaises(ValueError):
            fc.State((0,1,0),(1,1,0),speed_like=2,lift=2)
        with self.assertRaises(ValueError):
            fc.State((0,1,0),(1,1,0),speed_like=2,lateral=3,spin_axis=(1,1,0))
        good=fc.step_airborne(fc.State((0,1,0),(1,1,0),speed_like=2,lift=2,spin_axis=(0,0,1)))
        base=fc.step_airborne(fc.State((0,1,0),(1,1,0)))
        self.assertNotEqual(good.velocity,base.velocity)

    def test_explicit_trajectory_point_vs_swept(self):
        samples=[(5.,(0,5,0),(0,-1,0)),(11.,(0,-1,0),(0,-1,0))]
        point=fc.predict_contact_from_trajectory(samples,[ground()],assume_tree_free=True)
        sphere=fc.predict_contact_from_trajectory(samples,[ground()],contact_mode="swept_kcol_query_0p5",assume_tree_free=True)
        self.assertAlmostEqual(point["contact_t"],10.)
        self.assertAlmostEqual(sphere["contact_t"],9.5)
        self.assertEqual(sphere["ball_center_xyz"],(0,.5,0))
        self.assertEqual(sphere["surface_contact_xyz"],(0,0,0))
        self.assertEqual(point["time_base"],"caller_supplied_unverified")
        self.assertNotIn("time_numerical_steps",point)
        self.assertFalse(sphere["training_approved"])

    def test_trajectory_competing_surfaces(self):
        upper=fc.Triangle((-10,1,-10),(0,1,10),(10,1,-10),face_id=7)
        samples=[(0.,(0,5,0),(0,-10,0)),(1.,(0,-10,0),(0,-10,0))]
        result=fc.predict_contact_from_trajectory(samples,[ground(),upper],assume_tree_free=True)
        self.assertEqual(result["face_id"],7)
        self.assertAlmostEqual(result["contact_t"],4/15)

    def test_trajectory_winding_permutation(self):
        a=ground()
        b=fc.Triangle(a.c,a.b,a.a,face_id=9)
        samples=[(0.,(0,5,0),(0,-6,0)),(1.,(0,-1,0),(0,-6,0))]
        p=fc.predict_contact_from_trajectory(samples,[a],assume_tree_free=True)
        q=fc.predict_contact_from_trajectory(samples,[b],assume_tree_free=True)
        self.assertEqual(p["ball_center_xyz"],q["ball_center_xyz"])
        self.assertEqual(p["contact_t"],q["contact_t"])

    def test_trajectory_translation(self):
        delta=(100,20,-200)
        orig=ground()
        shifted=fc.Triangle(*(fc.add(p,delta) for p in (orig.a,orig.b,orig.c)))
        s=[(2.,(0,5,0),(0,-6,0)),(8.,(0,-1,0),(0,-6,0))]
        shifted_s=[(t,fc.add(p,delta),v) for t,p,v in s]
        r=fc.predict_contact_from_trajectory(s,[orig],assume_tree_free=True)
        q=fc.predict_contact_from_trajectory(shifted_s,[shifted],assume_tree_free=True)
        self.assertAlmostEqual(r["contact_t"],q["contact_t"])
        for i in range(3):
            self.assertAlmostEqual(r["surface_contact_xyz"][i]+delta[i],q["surface_contact_xyz"][i])

    def test_trajectory_fail_closed(self):
        samples=[(0.,(0,5,0),(0,-1,0)),(1.,(0,-1,0),(0,-1,0))]
        bad=[[],[samples[0]],
             [(0.,samples[0][1],samples[0][2]),(0.,samples[1][1],samples[1][2])],
             [(0.,samples[0][1],samples[0][2]),(-1.,samples[1][1],samples[1][2])],
             [(0.,samples[0][1],samples[0][2]),(1.,samples[1][1],(float("nan"),0,0))]]
        for item in bad:
            with self.subTest(item=item),self.assertRaises(ValueError):
                fc.predict_contact_from_trajectory(item,[ground()],assume_tree_free=True)
        self.assertEqual(fc.predict_contact_from_trajectory(samples,[ground()])["status"],
                         "ABSTAIN_TREE_CLEARANCE_UNKNOWN")

    def test_obj_vertex_zero_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"mesh.obj"
            p.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 0 2 3\n")
            with self.assertRaises(ValueError):
                fc.read_obj(p)

    def test_explicit_trajectory_no_hit(self):
        samples=[(0.,(20,5,20),(0,-1,0)),(1.,(20,-1,20),(0,-1,0))]
        result=fc.predict_contact_from_trajectory(samples,[ground()],assume_tree_free=True)
        self.assertEqual(result["status"],"NO_CONTACT_IN_HORIZON")

if __name__=="__main__":
    unittest.main()
