"""Read-only visual diagnostic must use the SAME SHA-verified KCL IDs as UI.

All fixtures are synthetic; no source DAE, Wii ROM or operator-private XYZ.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"))

from diagnose_inspector_visual_loading import diagnose
from test_p0_inspector_material_alignment import fixture
from wii_ai_golf.inspector.asset_preferences import AssetSelections
from wii_ai_golf.inspector.terrain_labels import LABEL_KIND


class DiagnosedSourceIDsTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder=Path(temp.name)/"Projects"
        self.folder.mkdir()
        self.obj=self.folder/"hole01-collision-candidate-PRIVATE.obj"
        self.dae=self.folder/"glf_course_fc1.dae"
        self.dae.write_text("<COLLADA/>",encoding="ascii")
        self.obj.write_bytes(
            b"v 0 0 0\nv 1 0 0\nv 0 0 1\nf 1 2 3\n")
        self.label=self.folder/"hole01-collision-candidate-labels-PRIVATE.json"
        self.visual=fixture()[1]

    def write_labels(self,*,valid=True):
        self.label.write_text(json.dumps({
            "kind":LABEL_KIND,"version":1,
            "geometry_obj_sha256": (
                hashlib.sha256(self.obj.read_bytes()).hexdigest()
                if valid else "0"*64),
            "source_hole_index":1,"faces":1,
            "source_attributes":[6],"training_approved":False,
            "allowed_to_publish":False,
        }),encoding="ascii")

    def run_diag(self,*,saved_label=None):
        prefs=AssetSelections(
            terrain_obj=str(self.obj.resolve()),
            visual_dae=str(self.dae.resolve()),
            terrain_labels=(str(saved_label) if saved_label else None))
        with patch("diagnose_inspector_visual_loading.load_asset_selections",
                   return_value=prefs), patch(
                   "diagnose_inspector_visual_loading.load_private_dae_visual_model",
                   return_value=self.visual), patch(
                   "diagnose_inspector_visual_loading.prepare_textures",
                   return_value={}), patch(
                   "diagnose_inspector_visual_loading.controller_scale_audit",
                   return_value={"skin_controller_count":12}), patch(
                   "diagnose_inspector_visual_loading.accelerated_available",
                   return_value=False):
            return diagnose(str(self.dae))

    def test_matching_source_sidecar_autoloaded_and_counts_visible(self):
        self.write_labels()
        result=self.run_diag()
        self.assertEqual(result["kcl_surface_labels_status"],
                         "PAIRED_SHA_BOUND_IDS_ACCEPTED")
        self.assertFalse(result["saved_kcl_surface_label_path_present"])
        counts=result["kcl_to_visual_display_fit"]["source_class_counts"]
        self.assertEqual(counts["categories"]["green"]["kcl_source_faces"],1)
        self.assertTrue(counts["kcl_source_ogws_labels_recognized"])
        self.assertEqual(result["original_controller_scale_audit"][
            "skin_controller_count"],12)

    def test_absent_source_sidecar_reports_missing_kcl_not_missing_dae(self):
        result=self.run_diag()
        self.assertEqual(result["kcl_surface_labels_status"],
                         "NO_SHA_BOUND_SOURCE_IDS_FOUND")
        self.assertIn("KCL green=0",result["kcl_to_visual_display_fit"]["reason"])
        self.assertEqual(
            result["kcl_to_visual_display_fit"]["source_class_counts"][
                "categories"]["fairway"]["visual_source_faces"],1)
        self.assertFalse(result["kcl_to_visual_display_fit"]["native_world_proven"])

    def test_bad_saved_source_sidecar_does_not_silently_use_good_sibling(self):
        self.write_labels()
        saved=self.folder/"wrong-saved-labels-PRIVATE.json"
        saved.write_text(json.dumps({
            "kind":LABEL_KIND,"version":1,
            "geometry_obj_sha256":"0"*64,
            "source_hole_index":1,"faces":1,
            "source_attributes":[6],"training_approved":False,
            "allowed_to_publish":False}),encoding="ascii")
        result=self.run_diag(saved_label=saved)
        self.assertEqual(result["kcl_surface_labels_status"],
                         "SOURCE_IDS_DECLINED")
        self.assertEqual(result["kcl_to_visual_display_fit"][
            "source_class_counts"]["categories"]["green"]["kcl_source_faces"],0)
        self.assertIn("TerrainError",result["kcl_surface_labels_reason"])


if __name__=="__main__":
    unittest.main()
