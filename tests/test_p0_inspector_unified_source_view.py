"""One shared original UV+KCL camera, explicitly UNVERIFIED alignment tests.

All meshes are synthetically created; no game assets, ROM, Dolphin, network,
memory writes or non-source texture guesses.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from wii_ai_golf.inspector.scene_camera import (
    fit_camera, frame_playable_camera, playable_source_vertices)
from wii_ai_golf.inspector.textured_preview import TexturedPreviewWindow
from wii_ai_golf.inspector.unified_source_view import (
    prepare_comparison_kcl, overlay_summary, draw_comparison)
from wii_ai_golf.inspector.visual_model import PrivateVisualModel, VisualFace
from wii_ai_golf.inspector.terrain import TerrainMesh


def scene():
    vertices = (
        (0., 0., 0.), (100., 0., 0.), (0., 0., 100.),
        (100., 0., 100.), (-2500., 0., -2500.),
        (2500., 0., -2500.), (-2500., 0., 2500.))
    model = PrivateVisualModel(
        vertices=vertices,
        uvs=((0., 0.), (1., 0.), (0., 1.)),
        faces=(
            VisualFace((0, 1, 2), (0, 1, 2), "M_Fairway"),
            VisualFace((1, 3, 2), (0, 1, 2), "M_Green"),
            VisualFace((4, 5, 6), (0, 1, 2), "M_Enkei"),
        ),
        textures={}, obj_sha256="synthetic", mtl_sha256="synthetic",
        source_name="synthetic-no-original-game-art",
        solid_colors={"M_Fairway": (10, 150, 25),
                      "M_Green": (30, 200, 40),
                      "M_Enkei": (60, 100, 40)},
    )
    collision=TerrainMesh(
        vertices=((0., 1., 0.), (10., 1., 0.),
                  (0., 1., 10.), (10., 1., 10.)),
        faces=((0, 1, 2), (1, 3, 2)),
        sha256="synthetic-original-kcl-hash",
        source_name="synthetic-private-kcl.obj",
        face_materials=(1, 6),
    )
    return model, collision


class UnifiedSourceTests(unittest.TestCase):
    def test_frame_uses_playable_source_not_background_scenery(self):
        model, _ = scene()
        self.assertEqual(len(playable_source_vertices(model)), 4)
        original = fit_camera(model.vertices)
        course = frame_playable_camera(model)
        self.assertLess(course.scale, original.scale / 20.)
        self.assertEqual(course.focus, (50., 0., 50.))
        # No changes to original geometry coordinates.
        self.assertEqual(model.vertices[4], (-2500., 0., -2500.))

    def test_bounds_fit_disclosed_not_native_world_transform(self):
        model, collision=scene()
        comp=prepare_comparison_kcl(collision, model)
        self.assertEqual(comp.source_scale, 10.)
        self.assertEqual(comp.source_sha256, collision.sha256)
        self.assertEqual(len(comp.faces), 2)
        self.assertEqual(len(comp.edge_faces), 5)
        self.assertEqual(comp.vertices[0][:3], (0., 0., 0.))
        self.assertEqual(comp.colors[0].lower(), "#42b979")
        self.assertEqual(comp.colors[1].lower(), "#73e998")
        self.assertIn("UNVERIFIED", overlay_summary(comp).upper())
        self.assertIn("display-only", overlay_summary(comp))
        self.assertEqual(collision.vertices[0], (0., 1., 0.))

    def test_same_canvas_modes_preserve_texture_image_bytes(self):
        try:
            from PIL import Image
            import numpy as np
        except ImportError:
            self.skipTest("Optional original-image renderer missing")
        model, collision=scene()
        comp=prepare_comparison_kcl(collision, model)
        camera=frame_playable_camera(model)
        frame=Image.new("RGB", (300, 220), (24, 32, 49))
        original=np.asarray(frame).copy()
        only=draw_comparison(frame.copy(), comp, camera, mode="Textures")
        self.assertTrue(np.array_equal(np.asarray(only), original))
        kcl=draw_comparison(frame.copy(), comp, camera, mode="Collision")
        both=draw_comparison(frame.copy(), comp, camera, mode="Both")
        self.assertEqual(kcl.size, frame.size)
        self.assertEqual(both.size, frame.size)
        self.assertFalse(np.array_equal(np.asarray(kcl), original))
        self.assertFalse(np.array_equal(np.asarray(both), original))
        with self.assertRaises(ValueError):
            draw_comparison(frame, comp, camera, mode="INVALID")

    def test_arrow_keys_move_without_rmb_while_wasd_requires_it(self):
        model, _=scene()
        view=object.__new__(TexturedPreviewWindow)
        view.camera=frame_playable_camera(model)
        view.home_camera=view.camera
        view.full_camera=fit_camera(model.vertices)
        view.drag_button=None
        view.schedule=Mock()
        start=view.camera.position
        self.assertEqual(view.key_move(SimpleNamespace(keysym="Up",state=0)), "break")
        self.assertNotEqual(start, view.camera.position)
        after=view.camera.position
        view.key_move(SimpleNamespace(keysym="w",state=0))
        self.assertEqual(after, view.camera.position)
        for key in ("Down", "Left", "Right"):
            previous=view.camera.position
            self.assertEqual(view.key_move(SimpleNamespace(keysym=key,state=0)), "break")
            self.assertNotEqual(previous, view.camera.position)
        view.frame()
        self.assertEqual(view.camera,view.home_camera)
        view.frame_all()
        self.assertEqual(view.camera,view.full_camera)

    def test_drag_adaptively_lowers_pixel_resolution_not_source_faces(self):
        view=object.__new__(TexturedPreviewWindow)
        view._pending=None
        view._closed=False
        view._request_version=7
        view.fast_active=True
        view.drag_button=3
        view.camera=fit_camera(scene()[0].vertices)
        view.mode=Mock()
        view.mode.get.return_value="Both"
        view.comparison_kcl=object()
        view.model=Mock()
        view.model.faces=[None]*11995
        view.canvas=Mock()
        view.canvas.winfo_width.return_value=1000
        view.canvas.winfo_height.return_value=600
        view.status=Mock()
        view._start_latest=Mock()
        view._request_full_render()
        self.assertEqual(view._queued[:3],(7,680,408))
        self.assertEqual(view._queued[4:],
                         ("Both", view.comparison_kcl))
        view.drag_button=None
        view._request_full_render()
        self.assertEqual(view._queued[:3],(7,1000,600))

    def test_gui_syncs_new_or_labeled_collision_data_to_shared_view(self):
        from wii_ai_golf.inspector.gui import Inspector
        inst=object.__new__(Inspector)
        inst.visual_preview=Mock()
        inst.terrain_mesh=scene()[1]
        Inspector._sync_visual_terrain(inst)
        inst.visual_preview.set_collision_terrain.assert_called_once_with(
            inst.terrain_mesh)
        inst.visual_preview.reset_mock()
        inst.terrain_mesh=None
        Inspector._sync_visual_terrain(inst)
        inst.visual_preview.set_collision_terrain.assert_called_once_with(None)


if __name__=="__main__":
    unittest.main()
