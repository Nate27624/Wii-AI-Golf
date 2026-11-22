"""Synthetic evidence gates for material-based display-only KCL/DAE registration."""
from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from wii_ai_golf.inspector.material_alignment import (
    MaterialAlignmentError, derive_material_alignment, alignment_diagnostic)
from wii_ai_golf.inspector.terrain import TerrainMesh
from wii_ai_golf.inspector.visual_model import PrivateVisualModel, VisualFace
from wii_ai_golf.inspector.unified_source_view import (
    prepare_comparison_kcl, source_to_visual_display, overlay_summary)
from wii_ai_golf.inspector.textured_preview import TexturedPreviewWindow


def fixture(*, missing_holdout=False, shifted_bunker=False,
            wrong_green_footprint=False, warning=True):
    # Three independent source-labeled local patches represent green,
    # fairway and bunker in KCL and original visual DAE. Transform X/Z by
    # EXACTLY 90° and 2.0 scale; no game assets or fake source physics.
    faces=[]
    native=[]
    labels=[]
    vis_faces=[]
    vis=[]
    uvs=((0.,0.),(1.,0.),(0.,1.))
    categories=[("green",6,"M_Green",(0.,0.,0.)),
                ("fairway",1,"M_Fairway",(10.,0.,0.))]
    if not missing_holdout:
        categories.append(("bunker",3,"M_Bunker",(0.,0.,20.)))
    for name,attr,material,(x,y,z) in categories:
        base=len(native)
        native.extend(((x,y,z),(x+2.,y,z),(x,y,z+2.)))
        faces.append((base,base+1,base+2))
        labels.append(attr)
        vb=len(vis)
        for xx,yy,zz in native[base:base+3]:
            # +Y 90°: (x,z)->(-2z,2x). Deliberate translation.
            X=100.-2.*zz
            Z=-50.+2.*xx
            if name=="bunker" and shifted_bunker:
                X+=12.
            if name=="green" and wrong_green_footprint:
                X+=(xx-x)*6.
                Z+=(zz-z)*6.
            vis.append((X,2.*yy+3.,Z))
        vis_faces.append(VisualFace(
            (vb,vb+1,vb+2),(0,1,2),material))
    terrain=TerrainMesh(tuple(native),tuple(faces),"synthetic-kcl",
                        "synthetic-source",tuple(labels))
    visual=PrivateVisualModel(tuple(vis),uvs,tuple(vis_faces),{},
                              "synthetic-dae","synthetic","synthetic",
                              source_scene_warning=(
                                  "GEOMETRY-ONLY ORIGINAL-TEXTURE PREVIEW"
                                  if warning else None))
    return terrain,visual


class Var:
    def __init__(self,v):self.v=v
    def get(self):return self.v
    def set(self,v):self.v=v


class MaterialFitTests(unittest.TestCase):
    def test_plain_obj_unlabeled_faces_are_not_mistaken_for_kcl_classes(self):
        from wii_ai_golf.inspector.material_alignment import source_class_counts
        terrain,visual=fixture()
        unlabeled=replace(
            terrain,face_materials=tuple(None for _ in terrain.faces))
        counts=source_class_counts(unlabeled,visual)
        self.assertEqual(counts["categories"]["green"]["kcl_source_faces"],0)
        self.assertEqual(counts["categories"]["green"]["visual_source_faces"],1)
        self.assertFalse(counts["kcl_source_ogws_labels_recognized"])
        diag=alignment_diagnostic(unlabeled,visual)
        self.assertEqual(diag["status"],"SOURCE_DISPLAY_REGISTRATION_DECLINED")
        self.assertIn("KCL green=0 fairway=0",diag["reason"])
        self.assertIn("-labels-PRIVATE.json",diag["reason"])
        self.assertEqual(diag["source_class_counts"]["categories"]["fairway"][
            "visual_source_faces"],1)
        self.assertFalse(diag["native_world_proven"])

    def test_dae_materials_missing_identified_separately_from_source_kcl(self):
        terrain, visual=fixture()
        stripped=replace(visual,faces=tuple(replace(face,material="M_Other")
                             for face in visual.faces))
        result=alignment_diagnostic(terrain,stripped)
        self.assertEqual(result["status"],"SOURCE_DISPLAY_REGISTRATION_DECLINED")
        self.assertIn("KCL green=1 fairway=1",result["reason"])
        self.assertIn("DAE green=0 fairway=0",result["reason"])
        self.assertIn("SAME course",result["reason"])
        self.assertTrue(result["source_class_counts"][
            "kcl_source_ogws_labels_recognized"])
        self.assertFalse(result["source_class_counts"][
            "visual_source_material_labels_recognized"])

    def test_independently_verified_scale_yaw_translation(self):
        terrain,visual=fixture()
        alignment=derive_material_alignment(terrain,visual)
        self.assertAlmostEqual(alignment.scale,2.)
        self.assertAlmostEqual(alignment.yaw_degrees,90.)
        self.assertAlmostEqual(alignment.holdout_error_fraction,0.)
        self.assertAlmostEqual(alignment.green_area_ratio,1.)
        comp=prepare_comparison_kcl(
            terrain, visual,material_alignment=alignment)
        for source,world in zip(terrain.vertices,visual.vertices):
            self.assertAlmostEqual(source_to_visual_display(source,comp)[0],world[0])
            self.assertAlmostEqual(source_to_visual_display(source,comp)[1],world[1])
            self.assertAlmostEqual(source_to_visual_display(source,comp)[2],world[2])
        self.assertEqual(comp.vertices,tuple(alignment.apply(p)
                                             for p in terrain.vertices))
        self.assertIn("MATERIAL-LANDMARK",overlay_summary(comp))
        self.assertIn("bunker",overlay_summary(comp))
        self.assertIn("UNVERIFIED",overlay_summary(comp))
        info=alignment_diagnostic(terrain,visual)
        self.assertEqual(info["status"],"SOURCE_MATERIAL_DISPLAY_FIT_CANDIDATE")
        self.assertFalse(info["native_world_proven"])
        self.assertEqual(info["uniform_scale"],2.)

    def test_heldout_bunker_mismatch_declines_wrong_scale(self):
        terrain,visual=fixture(shifted_bunker=True)
        with self.assertRaisesRegex(MaterialAlignmentError,"bunker location residual"):
            derive_material_alignment(terrain,visual)
        self.assertEqual(alignment_diagnostic(terrain,visual)["status"],
                         "SOURCE_DISPLAY_REGISTRATION_DECLINED")

    def test_source_green_footprint_mismatch_declines_wrong_scale(self):
        terrain,visual=fixture(wrong_green_footprint=True)
        with self.assertRaisesRegex(MaterialAlignmentError,"green footprint"):
            derive_material_alignment(terrain,visual)

    def test_two_landmarks_insufficient_to_claim_alignment(self):
        terrain,visual=fixture(missing_holdout=True)
        with self.assertRaisesRegex(MaterialAlignmentError,"independent"):
            derive_material_alignment(terrain,visual)

    def test_unsupported_collada_auto_uses_measured_not_bounds_fit(self):
        terrain,visual=fixture()
        view=TexturedPreviewWindow.__new__(TexturedPreviewWindow)
        view.model=visual
        view.mode=Var("Textures")
        view.display_rotation=Var(0)
        view.comparison_status=Var("none")
        view.schedule=Mock()
        view.set_collision_terrain(terrain)
        self.assertEqual(view.mode.get(),"Both")
        self.assertIsNotNone(view.comparison_kcl.source_material_fit)
        self.assertAlmostEqual(view.comparison_kcl.source_scale,2.)
        self.assertIn("independent bunker residual",view.comparison_status.get())
        self.assertEqual(view._source_terrain,terrain)
        self.assertEqual(view.schedule.call_count,1)

    def test_incomplete_scene_without_holdout_hides_misleading_xray(self):
        terrain,visual=fixture(missing_holdout=True)
        view=TexturedPreviewWindow.__new__(TexturedPreviewWindow)
        view.model=visual
        view.mode=Var("Both")
        view.display_rotation=Var(0)
        view.comparison_status=Var("none")
        view.schedule=Mock()
        view.set_collision_terrain(terrain)
        self.assertEqual(view.mode.get(),"Textures")
        self.assertIsNone(view.comparison_kcl)
        self.assertIn("AUTO-OVERLAY DECLINED",view.comparison_status.get())
        self.assertIn("No independent",view.comparison_status.get())
        # Explicit operator yaw remains separately labeled as unverified.
        view.set_display_rotation(180)
        self.assertIsNotNone(view.comparison_kcl)
        self.assertIn("MANUAL BOUNDS-FIT",view.comparison_status.get())
        view.set_display_rotation(0)
        self.assertIsNone(view.comparison_kcl)
        self.assertEqual(view.mode.get(),"Textures")

    def test_normal_original_scene_retains_backward_compatibility(self):
        terrain,visual=fixture(missing_holdout=True,warning=False)
        view=TexturedPreviewWindow.__new__(TexturedPreviewWindow)
        view.model=visual
        view.mode=Var("Textures")
        view.display_rotation=Var(0)
        view.comparison_status=Var("none")
        view.schedule=Mock()
        view.set_collision_terrain(terrain)
        self.assertEqual(view.mode.get(),"Both")
        self.assertIsNone(view.comparison_kcl.source_material_fit)
        self.assertIn("bounds fit",view.comparison_status.get())

if __name__=="__main__":
    unittest.main()
