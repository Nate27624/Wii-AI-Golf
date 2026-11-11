"""Source-only DAE scene transform audit and no-write RAM alignment gates."""
from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
from dataclasses import replace
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from wii_ai_golf.inspector.visual_model import VisualAssetError
from wii_ai_golf.inspector.collada_scene_graph import source_scene_instances
import xml.etree.ElementTree as ET
from wii_ai_golf.inspector.scene_alignment_audit import (
    RegistrationAuditError, audit_collada_scene, audit_surface_registration)
from test_p0_inspector_unified_source_view import scene
from p0_inspect_course_alignment_private import (
    source_gated_live_anchors, main as alignment_audit_main)


def _bits(value):
    return int.from_bytes(struct.pack(">f", float(value)), "big")


class PrivateSceneAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dae = Path(self.temp.name) / "course-PRIVATE.dae"

    def _scene(self, transform: str, *, up: str = "Y_UP"):
        self.dae.write_text(
            '<?xml version="1.0"?><COLLADA>'
            '<asset><up_axis>' + up + '</up_axis></asset>'
            '<library_visual_scenes><visual_scene id="private">'
            '<node id="course"><instance_geometry url="#visual"/>'
            + transform +
            '</node></visual_scene></library_visual_scenes>'
            '<scene><instance_visual_scene url="#private"/></scene>'
            '</COLLADA>', encoding="utf-8")

    def test_audit_detects_ignored_node_rotation_and_translation(self):
        self._scene('<matrix>'
                    '-1 0 0 0 0 1 0 0 0 0 -1 0 200 0 300 1'
                    '</matrix>')
        report = audit_collada_scene(self.dae)
        self.assertEqual(report["visual_scene_count"], 1)
        self.assertEqual(report["geometry_instance_count"], 1)
        self.assertEqual(report["nonidentity_transform_count"], 1)
        self.assertEqual(report["transform_counts"]["matrix"], 1)
        self.assertTrue(report["active_scene_target_present"])
        self.assertTrue(report["current_loader_applies_visual_scene_transforms"])
        self.assertTrue(report["source_authored_dae_transform_is_not_native_kcl_mapping"])
        self.assertIn(180., report["matrix_xz_yaw_degrees_hypotheses"])

    def test_identity_scene_is_not_mislabeled_as_rotated(self):
        self._scene('<matrix>'
                    '1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1'
                    '</matrix>')
        report = audit_collada_scene(self.dae)
        self.assertEqual(report["nonidentity_transform_count"], 0)
        self.assertEqual(report["matrix_xz_yaw_degrees_hypotheses"], [])

    def test_source_scene_node_rotations_are_flagged(self):
        self._scene('<rotate>0 1 0 180</rotate>'
                    '<translate>20 0 30</translate>'
                    '<scale>1 1 1</scale>')
        report = audit_collada_scene(self.dae)
        self.assertEqual(report["transform_counts"], {
            "rotate": 1, "scale": 1, "translate": 1})
        self.assertEqual(report["nonidentity_transform_count"], 2)

    def test_reject_external_entity_invalid_axis_nonfinite_matrix(self):
        self._scene("<matrix>1 2</matrix>")
        with self.assertRaises(RegistrationAuditError):
            audit_collada_scene(self.dae)
        self._scene("<matrix>" + " ".join(["1"]*15+["nan"]) + "</matrix>")
        with self.assertRaises(RegistrationAuditError):
            audit_collada_scene(self.dae)
        self._scene("", up="UNKNOWN_UP")
        with self.assertRaises(RegistrationAuditError):
            audit_collada_scene(self.dae)
        self.dae.write_text('<!DOCTYPE x [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
                            '<COLLADA/>', encoding="utf-8")
        with self.assertRaises(RegistrationAuditError):
            audit_collada_scene(self.dae)

    def test_source_scene_inventory_exposes_unsupported_active_tags(self):
        self._scene('<instance_controller url="#skin"/>' +
                    '<instance_node url="#other"/>' +
                    '<lookat>0 0 1 0 0 0 0 1 0</lookat>')
        result = audit_collada_scene(self.dae)
        self.assertTrue(result["active_scene_resolved_for_inventory"])
        self.assertEqual(result["active_unsupported_construct_counts"], {
            "instance_controller": 1, "instance_node": 1, "lookat": 1})
        self.assertTrue(result["active_scene_requires_unimplemented_processing"])
        self.assertTrue(result["unsupported_constructs_are_not_safely_ignorable"])
        # The actual source geometry loader still fails closed rather than
        # dropping a controller and claiming accurate course registration.
        with self.assertRaisesRegex(
                VisualAssetError,
                "Unsupported original scene graph transform/controller"):
            source_scene_instances(ET.parse(self.dae).getroot())

    def test_scene_only_inventory_never_calls_original_art_loader_or_memory(self):
        self._scene('<instance_controller url="#skin"/>')
        out = StringIO()
        with patch("p0_inspect_course_alignment_private.load_private_dae_visual_model",
                   side_effect=AssertionError("Should not render private DAE")), \
             patch("p0_inspect_course_alignment_private.load_private_obj",
                   side_effect=AssertionError("Should not read KCL")), \
             patch("p0_inspect_course_alignment_private.source_gated_live_anchors",
                   side_effect=AssertionError("Should not contact Dolphin")), \
             redirect_stdout(out):
            exit_code = alignment_audit_main((
                "--scene-only", "--visual-dae", str(self.dae)))
        self.assertEqual(exit_code, 0)
        data = json.loads(out.getvalue())
        self.assertEqual(data["status"], "SOURCE_COLLADA_SCENE_INVENTORY_ONLY")
        self.assertEqual(data["dae_visual_scene"]
                         ["active_unsupported_construct_counts"],
                         {"instance_controller": 1})
        self.assertFalse(data["game_world_alignment_verified"])
        self.assertFalse(data["training_approved"])

    def test_original_style_skin_controller_inventory_no_fabricated_geometry(self):
        # Synthetic Collada with skin-controlled course geometry, matching
        # the operator's 12 instance_controller / 0 instance_geometry shape.
        # Controller IDs, joint names, transforms and source arrays are fake.
        identity = "1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"
        xml = (
            '<COLLADA><asset><up_axis>Y_UP</up_axis></asset>'
            '<library_geometries><geometry id="synthetic_mesh"/></library_geometries>'
            '<library_controllers><controller id="test_skin"><skin source="#synthetic_mesh">'
            '<bind_shape_matrix>' + identity + '</bind_shape_matrix>'
            '<source id="synthetic_joints"><Name_array id="j_names" count="1">'
            'fakeBone</Name_array></source>'
            '<source id="synthetic_inverse"><float_array id="matrices" count="16">'
            + identity + '</float_array><technique_common><accessor source="#matrices"'
            ' count="1" stride="16"/></technique_common></source>'
            '<joints><input semantic="JOINT" source="#synthetic_joints"/>'
            '<input semantic="INV_BIND_MATRIX" source="#synthetic_inverse"/></joints>'
            '<vertex_weights count="3"><input semantic="JOINT" offset="0" '
            'source="#synthetic_joints"/><input semantic="WEIGHT" offset="1" '
            'source="#synthetic_weights"/><vcount>1 1 1</vcount>'
            '<v>0 0 0 0 0 0</v></vertex_weights>'
            '</skin></controller></library_controllers>'
            '<library_visual_scenes><visual_scene id="golf">'
            '<node id="golfRoot"><instance_controller url="#test_skin">'
            '<skeleton>#fakeBone</skeleton></instance_controller>'
            '</node></visual_scene></library_visual_scenes>'
            '<scene><instance_visual_scene url="#golf"/></scene></COLLADA>'
        )
        self.dae.write_text(xml, encoding="utf-8")
        result = audit_collada_scene(self.dae)
        self.assertEqual(result["geometry_instance_count"], 0)
        self.assertTrue(result["active_scene_requires_unimplemented_processing"])
        controllers = result["controllers"]
        self.assertEqual(controllers["controller_definition_count"], 1)
        self.assertEqual(controllers["active_controller_instance_count"], 1)
        self.assertEqual(controllers["active_controller_kind_counts"], {"skin": 1})
        detail, = controllers["active_controller_structural_summaries"]
        self.assertTrue(detail["source_geometry_resolved"])
        self.assertEqual(detail["joint_name_count"], 1)
        self.assertEqual(detail["inverse_bind_matrix_count"], 1)
        self.assertEqual(detail["weighted_vertex_count"], 3)
        self.assertEqual(detail["max_influences_per_vertex"], 1)
        self.assertTrue(detail["vcount_matches_declared"])
        self.assertEqual(detail["bind_shape_matrix_state"], "IDENTITY")
        self.assertEqual(detail["skeleton_reference_count"], 1)
        self.assertFalse(detail["static_skinning_evaluated"])
        self.assertFalse(controllers["native_world_alignment_verified"])
        serialized = json.dumps(controllers)
        self.assertNotIn("fakeBone", serialized)
        self.assertNotIn("synthetic_mesh", serialized)
        self.assertNotIn("test_skin", serialized)

    def test_skin_controller_reports_nonidentity_and_unresolved_refs(self):
        xml = (
            '<COLLADA><library_controllers>'
            '<controller id="c"><skin source="#missing_mesh">'
            '<bind_shape_matrix>1 0 0 0 0 1 0 0 0 0 1 0 5 0 0 1'
            '</bind_shape_matrix></skin></controller></library_controllers>'
            '<library_visual_scenes><visual_scene id="s"><node>'
            '<instance_controller url="#c"/>'
            '<instance_controller url="#unresolved"/>'
            '</node></visual_scene></library_visual_scenes>'
            '<scene><instance_visual_scene url="#s"/></scene></COLLADA>'
        )
        self.dae.write_text(xml, encoding="utf-8")
        controls = audit_collada_scene(self.dae)["controllers"]
        self.assertEqual(controls["active_controller_kind_counts"],
                         {"UNRESOLVED": 1, "skin": 1})
        skin, missing = controls["active_controller_structural_summaries"]
        self.assertEqual(skin["bind_shape_matrix_state"], "NONIDENTITY")
        self.assertFalse(skin["source_geometry_resolved"])
        self.assertFalse(missing["controller_reference_resolved"])
        self.assertFalse(controls["controller_skinning_or_morphing_applied"])

    def test_surface_anchors_never_claim_native_registration(self):
        visual, terrain = scene()
        result = audit_surface_registration(terrain, visual, tee=(0., 1., 0.),
                                            pin=(10., 1., 10.))
        self.assertEqual(result["kcl_faces"], 2)
        self.assertEqual(result["visual_source_surface_triangle_counts"]["green"], 1)
        self.assertEqual(result["kcl_source_surface_triangle_counts"]["green"], 1)
        self.assertAlmostEqual(result["ram_tee_to_pin_distance_xz"], 14.1421, places=3)
        self.assertFalse(result["source_geometry_identity_proven"])
        self.assertFalse(result["native_game_world_transform_proven"])
        self.assertTrue(result["heading_is_not_a_source_matrix"])


    def test_four_display_fits_score_source_materials_without_applying_a_yaw(self):
        visual, terrain = scene()
        before_terrain = terrain.vertices
        before_visual = visual.vertices
        audit = audit_surface_registration(terrain, visual)
        contrast = audit["display_fit_surface_contrast"]
        self.assertEqual(contrast["status"], "DISPLAY_ONLY_COARSE_MATERIAL_CONTRAST")
        self.assertEqual(contrast["matched_material_classes"], ["green", "fairway"])
        self.assertEqual([t["display_yaw_degrees"] for t in contrast["trial_displays"]],
                         [0, 90, 180, 270])
        trials = {t["display_yaw_degrees"]: t for t in contrast["trial_displays"]}
        self.assertAlmostEqual(trials[0]["surface_centroid_rms_xz"], 0., places=4)
        self.assertGreater(trials[180]["surface_centroid_rms_xz"], 40.)
        self.assertFalse(contrast["auto_apply_rotation"])
        self.assertFalse(contrast["native_collision_visual_alignment_verified"])
        self.assertFalse(contrast["independent_point_correspondences_proven"])
        self.assertEqual(terrain.vertices, before_terrain)
        self.assertEqual(visual.vertices, before_visual)

    def test_180_degree_synthetic_scene_changes_contrast_only_not_source_geometry(self):
        visual, terrain = scene()
        rotated_visual = replace(visual, vertices=tuple(
            (100. - x, y, 100. - z) for x, y, z in visual.vertices))
        contrast = audit_surface_registration(terrain, rotated_visual)[
            "display_fit_surface_contrast"]
        scores = {t["display_yaw_degrees"]: t["surface_centroid_rms_xz"]
                  for t in contrast["trial_displays"]}
        self.assertAlmostEqual(scores[180], 0., places=4)
        self.assertGreater(scores[0], 40.)
        # The audit never uses this lowest residual to move or rewrite an OBJ.
        self.assertFalse(contrast["auto_apply_rotation"])
        self.assertEqual(terrain.vertices[0], (0., 1., 0.))
        self.assertEqual(visual.vertices[0], (0., 0., 0.))

    def test_missing_matching_materials_abstains_without_inventing_alignment(self):
        visual, terrain = scene()
        unsupported = replace(visual, faces=tuple(
            replace(face, material="M_Enkei") for face in visual.faces))
        contrast = audit_surface_registration(terrain, unsupported)[
            "display_fit_surface_contrast"]
        self.assertEqual(contrast["status"],
                         "ABSTAIN_FEWER_THAN_TWO_MATCHED_SURFACE_CLASSES")
        self.assertEqual(contrast["matched_material_classes"], [])
        self.assertNotIn("trial_displays", contrast)
        self.assertFalse(contrast["native_collision_visual_alignment_verified"])


    def test_cli_applies_sha_bound_private_kcl_labels_before_scoring(self):
        visual, labeled = scene()
        unlabeled = replace(labeled, face_materials=(None, None))
        output = StringIO()
        cli = ("--terrain-obj", "original-PRIVATE.obj", "--terrain-labels",
               "original-labels-PRIVATE.json", "--visual-dae", "original-PRIVATE.dae",
               "--offline")
        with patch("p0_inspect_course_alignment_private.load_asset_selections",
                   return_value=SimpleNamespace(terrain_obj=None, tree_json=None)), \
             patch("p0_inspect_course_alignment_private.load_private_obj",
                   return_value=unlabeled), \
             patch("p0_inspect_course_alignment_private.apply_private_surface_labels",
                   return_value=labeled) as strict_labels, \
             patch("p0_inspect_course_alignment_private.load_private_dae_visual_model",
                   return_value=visual), \
             patch("p0_inspect_course_alignment_private.audit_collada_scene",
                   return_value={"synthetic_only": True}), \
             redirect_stdout(output):
            code = alignment_audit_main(cli)
        self.assertEqual(code, 0)
        strict_labels.assert_called_once()
        report = json.loads(output.getvalue())
        contrast = report["geometry"]["display_fit_surface_contrast"]
        self.assertEqual(contrast["matched_material_classes"], ["green", "fairway"])
        self.assertEqual(len(contrast["trial_displays"]), 4)
        self.assertFalse(report["source_visual_world_alignment_verified"])
        self.assertFalse(report["training_approved"])
        self.assertEqual(unlabeled.face_materials, (None, None))

    def test_cli_reports_source_graph_rejection_instead_of_raw_abort(self):
        visual, terrain = scene()
        out = StringIO()
        scene_inventory = {
            "active_unsupported_construct_counts": {"instance_controller": 3},
            "active_scene_requires_unimplemented_processing": True,
        }
        with patch("p0_inspect_course_alignment_private.load_asset_selections",
                   return_value=SimpleNamespace(terrain_obj=None, tree_json=None)), \
             patch("p0_inspect_course_alignment_private.load_private_obj",
                   return_value=terrain), \
             patch("p0_inspect_course_alignment_private.load_private_dae_visual_model",
                   side_effect=VisualAssetError(
                       "Unsupported original scene graph transform/controller")), \
             patch("p0_inspect_course_alignment_private.audit_collada_scene",
                   return_value=scene_inventory), \
             redirect_stdout(out):
            code = alignment_audit_main((
                "--terrain-obj", "original-PRIVATE.obj",
                "--visual-dae", "original-PRIVATE.dae", "--offline"))
        self.assertEqual(code, 2)
        data = json.loads(out.getvalue())
        self.assertEqual(data["status"], "ABSTAIN_SOURCE_VISUAL_MODEL")
        self.assertEqual(data["reason"],
                         "UNSUPPORTED_OR_UNRESOLVED_SOURCE_SCENE_GRAPH")
        self.assertEqual(data["dae_visual_scene"], scene_inventory)
        self.assertFalse(data["course_material_alignment_scored"])
        self.assertFalse(data["native_world_transform_verified"])
        self.assertFalse(data["training_approved"])

    def test_cli_abstains_without_valid_kcl_source_materials(self):
        visual, labeled = scene()
        unlabeled = replace(labeled, face_materials=(None, None))
        output = StringIO()
        with patch("p0_inspect_course_alignment_private.load_asset_selections",
                   return_value=SimpleNamespace(terrain_obj=None, tree_json=None)), \
             patch("p0_inspect_course_alignment_private.load_private_obj",
                   return_value=unlabeled), \
             patch("p0_inspect_course_alignment_private.load_private_dae_visual_model",
                   return_value=visual), \
             patch("p0_inspect_course_alignment_private.audit_collada_scene",
                   return_value={}), \
             redirect_stdout(output):
            code = alignment_audit_main(("--terrain-obj", "source-PRIVATE.obj",
                                         "--visual-dae", "source-PRIVATE.dae",
                                         "--offline"))
        self.assertEqual(code, 2)
        self.assertIn("ABSTAIN_KCL_SOURCE_MATERIALS", output.getvalue())
        self.assertNotIn("display_fit_surface_contrast", output.getvalue())


class LiveReadOnlySourceTests(unittest.TestCase):
    def _packet(self, *args):
        return dict(identity=tuple(range(14)), words={
            "tee_start_candidate": tuple(_bits(v) for v in (0, 0, 0)),
            "pin_candidate": tuple(_bits(v) for v in (20, 0, 10)),
        }, frame_bracket=(22, 23))

    def test_live_gated_tee_pin_reader_never_calls_game_write(self):
        context = MagicMock()
        context.__enter__.return_value = MagicMock()
        with patch("wii_ai_golf.integration.rpc.FelkRPC", return_value=context), patch(
                "wii_ai_golf.inspector.fast.packet", side_effect=[
                    self._packet(), {**self._packet(), "frame_bracket": (23, 24)}
                ]) as called:
            result = source_gated_live_anchors()
        self.assertEqual(called.call_count, 2)
        self.assertEqual(result["hole"], 13)
        self.assertEqual(result["pin"], (20., 0., 10.))
        self.assertEqual(result["tee"], (0., 0., 0.))

    def test_epoch_or_geometry_mismatch_abstains(self):
        context = MagicMock()
        context.__enter__.return_value = MagicMock()
        invalid = self._packet()
        invalid["identity"] = tuple(range(13)) + (999,)
        with patch("wii_ai_golf.integration.rpc.FelkRPC", return_value=context), patch(
                "wii_ai_golf.inspector.fast.packet", side_effect=[
                    self._packet(), invalid]):
            with self.assertRaises(ValueError):
                source_gated_live_anchors()
        changed = self._packet()
        changed["words"] = {**changed["words"],
                            "pin_candidate": tuple(_bits(v) for v in (40, 0, 10))}
        with patch("wii_ai_golf.integration.rpc.FelkRPC", return_value=context), patch(
                "wii_ai_golf.inspector.fast.packet", side_effect=[
                    self._packet(), {**changed, "frame_bracket":(23,24)}]):
            with self.assertRaises(ValueError):
                source_gated_live_anchors()


if __name__ == "__main__":
    unittest.main()
