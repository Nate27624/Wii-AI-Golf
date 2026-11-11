"""Source-only DAE scene transform audit and no-write RAM alignment gates."""
from __future__ import annotations

import json
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

from wii_ai_golf.inspector.scene_alignment_audit import (
    RegistrationAuditError, audit_collada_scene, audit_surface_registration)
from test_p0_inspector_unified_source_view import scene
from p0_inspect_course_alignment_private import source_gated_live_anchors


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
