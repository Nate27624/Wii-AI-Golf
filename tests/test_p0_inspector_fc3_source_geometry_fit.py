"""Synthetic-only source FC3 display transform fitting tests.

No user's original KCL, DAE, BRRES, TEX0, tree coordinates, or game RAM.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from wii_ai_golf.inspector.source_geometry_fit import (
    SurfaceFitError, fit_source_surface_display, private_fit_report,
    source_class_counts)
from wii_ai_golf.inspector.terrain import TerrainMesh
from wii_ai_golf.inspector.visual_model import PrivateVisualModel, VisualFace


def synthetic_original_source_pair(*, shift_heldout=0., no_labels=False,
                                   omit_bunker=False, omit_rough=False):
    """Four distinct original labeled patches, exact-known 2D scale/shift.

    Transform: DAE X = 3*KCL X+100, Z = 3*KCL Z-50. Unrelated scenery
    material is excluded from original playable-source camera framing.
    """
    positions=(
        ("green",6,"M_Green",(-10.,-12.)),
        ("fairway",1,"M_Fairway",(70.,5.)),
        ("bunker",3,"M_Bunker",(25.,70.)),
        ("rough",2,"M_Rough",(92.,77.)),
    )
    kverts=[]
    kvar=[]
    vverts=[]
    vfaces=[]
    mat=[]
    for name,attr,visual_id,(x,z) in positions:
        if (name=="bunker" and omit_bunker) or (
                name=="rough" and omit_rough):
            continue
        for i in range(12):
            j=i%4
            k=i//4
            px=x+j*3.8+k*.7
            pz=z+k*2.9+j*.4
            trip=((px,0.,pz), (px+1.9,0.,pz+.1),
                  (px+.4,0.,pz+1.4))
            ki=len(kverts)
            kverts.extend(trip)
            kvar.append((ki,ki+1,ki+2))
            mat.append(None if no_labels else attr)
            vi=len(vverts)
            for xx,yy,zz in trip:
                shift=shift_heldout if name=="bunker" else 0.
                vverts.append((xx*3.+100.+shift,yy,zz*3.-50.+shift))
            vfaces.append(VisualFace((vi,vi+1,vi+2),(0,1,2),visual_id))
    kcl=TerrainMesh(tuple(kverts),tuple(kvar),"2"*64,
                    "synthetic_original_kcl.obj",tuple(mat))
    visual=PrivateVisualModel(
        tuple(vverts),((0.,0.),(1.,0.),(0.,1.)),tuple(vfaces),{},
        "3"*64,"4"*64,"synthetic_fc3.dae")
    return kcl,visual


class FC3SourceTransformTests(unittest.TestCase):
    def test_source_surface_registration_recovers_exact_known_scale(self):
        terrain,visual=synthetic_original_source_pair()
        fit=fit_source_surface_display(
            terrain,visual,initial_multiplier=1.25,
            initial_offset_x=.03,initial_offset_z=-.025,
            yaw_degrees=0)
        self.assertAlmostEqual(fit.absolute_scale,3.,delta=.2)
        self.assertAlmostEqual(fit.multiplier,1.,delta=.065)
        self.assertAlmostEqual(fit.offset_x,0.,delta=.015)
        self.assertAlmostEqual(fit.offset_z,0.,delta=.015)
        self.assertEqual(fit.holdout_class,"bunker")
        self.assertLess(fit.training_score_fraction,.025)
        self.assertLess(fit.holdout_score_fraction,.05)
        self.assertGreater(fit.improvement_fraction,0.)
        self.assertFalse(fit.native_world_verified)

    def test_fit_report_does_not_include_any_original_source_positions(self):
        terrain,visual=synthetic_original_source_pair()
        result=private_fit_report(
            terrain,visual,initial_multiplier=1.12,
            initial_offset_x=.015,initial_offset_z=.01)
        self.assertEqual(result["status"],
                         "ORIGINAL_SURFACE_DISPLAY_FIT_CANDIDATE")
        self.assertTrue(result["independent_surface_heldout_gate_passed"])
        self.assertEqual(result["original_kcl_sha256"],"2"*64)
        self.assertEqual(result["original_dae_sha256"],"3"*64)
        self.assertFalse(result["native_world_verified"])
        self.assertFalse(result["game_collision_or_training_approved"])
        self.assertNotIn("source_kcl_to_visual_offset",result)
        self.assertNotIn("source_positions",result)
        self.assertNotIn("trees",result)

    def test_independent_bunker_failure_not_promoted(self):
        terrain,visual=synthetic_original_source_pair(shift_heldout=100.)
        result=private_fit_report(terrain,visual,initial_multiplier=1.,
                                  initial_offset_x=0.,initial_offset_z=0.)
        self.assertEqual(result["status"],
                         "ORIGINAL_SURFACE_FIT_FAILED_HOLDOUT_GATE")
        self.assertFalse(result["independent_surface_heldout_gate_passed"])
        self.assertGreater(result[
            "optimized_held_out_error_percent_of_diagonal"],6.)

    def test_requires_sha_bound_original_kcl_labels(self):
        terrain,visual=synthetic_original_source_pair(no_labels=True)
        result=private_fit_report(terrain,visual)
        self.assertEqual(result["status"],"SOURCE_GEOMETRY_FIT_DECLINED")
        self.assertIn("face IDs missing",result["reason"])
        counts=source_class_counts(terrain,visual)
        self.assertFalse(counts["source_kcl_has_recognized_ogws_ids"])
        self.assertTrue(counts["source_dae_has_corresponding_materials"])

    def test_missing_independent_holdout_refuses_scale_claim(self):
        terrain,visual=synthetic_original_source_pair(
            omit_bunker=True,omit_rough=True)
        with self.assertRaisesRegex(SurfaceFitError,"No separately"):
            fit_source_surface_display(terrain,visual)

    def test_rough_can_serve_as_independent_holdout(self):
        terrain,visual=synthetic_original_source_pair(omit_bunker=True)
        result=private_fit_report(
            terrain,visual,initial_multiplier=1.15,
            initial_offset_x=.015,initial_offset_z=.01)
        self.assertEqual(result["held_out_material"],"rough")
        self.assertTrue(result["independent_surface_heldout_gate_passed"])

    def test_invalid_operator_manual_scale_rejected(self):
        terrain,visual=synthetic_original_source_pair()
        for scale in (0.,-1.,float("nan"),float("inf"),5.):
            with self.subTest(scale=scale):
                result=private_fit_report(
                    terrain,visual,initial_multiplier=scale)
                self.assertEqual(result["status"],"SOURCE_GEOMETRY_FIT_DECLINED")
                self.assertFalse(result["native_world_verified"])


if __name__=="__main__":
    unittest.main()
