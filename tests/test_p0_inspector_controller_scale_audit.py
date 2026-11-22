"""Original COLLADA bind-shape scale diagnostics: synthetic no game assets."""
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from wii_ai_golf.inspector.collada_controller_scale import controller_scale_audit
from wii_ai_golf.inspector.visual_model import VisualAssetError

class ControllerScaleAuditTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dae=Path(temp.name)/"source-private.dae"

    def scene(self, matrix, *, source="#sourceMesh"):
        m=f"<bind_shape_matrix>{matrix}</bind_shape_matrix>" if matrix else ""
        self.dae.write_text(
            '<COLLADA><library_geometries><geometry id="sourceMesh"/>'
            '</library_geometries><library_controllers>'
            '<controller id="ctl"><skin source="'+source+'">'+m+
            '</skin></controller></library_controllers>'
            '<library_visual_scenes><visual_scene><node>'
            '<instance_controller url="#ctl"/></node></visual_scene>'
            '</library_visual_scenes></COLLADA>',encoding="utf-8")

    def test_source_bind_shape_matrix_measures_not_applies_uniform_scale(self):
        self.scene(".125 0 0 0 0 .125 0 0 0 0 .125 0 0 0 0 1")
        result=controller_scale_audit(self.dae)
        self.assertEqual(result["original_controller_count"],1)
        self.assertEqual(result["original_scene_controller_instances"],1)
        self.assertEqual(result["skin_nonidentity_bind_shape_count"],1)
        self.assertEqual(result["first_bind_shape_xyz_axis_scales"],
                         [[.125,.125,.125]])
        self.assertFalse(result["native_game_world_transform_proven"])
        self.assertTrue(result["bind_shape_is_not_complete_skinning_or_kcl_mapping"])

    def test_source_nonuniform_scale_and_omitted_identity(self):
        self.scene("1 0 0 0 0 2 0 0 0 0 3 0 0 0 0 1")
        result=controller_scale_audit(self.dae)
        self.assertEqual(result["skin_nonuniform_axis_scale_count"],1)
        self.assertEqual(result["first_bind_shape_xyz_axis_scales"],[[1.,2.,3.]])
        self.scene(None)
        self.assertEqual(controller_scale_audit(self.dae)["skin_missing_bind_shape_matrix_count"],1)

    def test_external_skin_source_and_nonfinite_matrix_rejected(self):
        self.scene("1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1",
                   source="https://example.test/other.dae#geo")
        with self.assertRaises(VisualAssetError):
            controller_scale_audit(self.dae)
        self.scene("nan 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1")
        with self.assertRaises(VisualAssetError):
            controller_scale_audit(self.dae)

if __name__=="__main__":
    unittest.main()
