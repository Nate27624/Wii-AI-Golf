"""Source-only KCL mode works even when original DAE world registration fails.

Synthetic fixtures only: no copyrighted art, private tree positions, Dolphin,
calibration shortcuts, game writes or engine control.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from test_p0_inspector_material_alignment import fixture, Var
from wii_ai_golf.inspector.scene_camera import frame_playable_camera, fit_camera
from wii_ai_golf.inspector.textured_preview import TexturedPreviewWindow
from wii_ai_golf.inspector.unified_source_view import (
    prepare_source_only_kcl, source_to_visual_display,
    draw_comparison, draw_tree_comparison)
from wii_ai_golf.inspector.terrain import TerrainMesh


def window(*, missing_holdout=True):
    terrain, model=fixture(missing_holdout=missing_holdout)
    view=TexturedPreviewWindow.__new__(TexturedPreviewWindow)
    view.model=model
    view.camera=frame_playable_camera(model)
    view.home_camera=view.camera
    view.full_camera=fit_camera(model.vertices)
    view._visual_camera_before_collision=None
    view._collision_camera=None
    view._overlay_decline_reason=None
    view.source_collision_kcl=None
    view.comparison_kcl=None
    view._source_terrain=None
    view.mode=Var("Textures")
    view.display_rotation=Var(0)
    view.manual_overlay_trial=Var(False)
    view.comparison_status=Var("")
    view.schedule=Mock()
    view.fast_active=True
    return view,terrain


class KCLModeTests(unittest.TestCase):
    def test_exact_kcl_coordinates_are_never_scaled_by_missing_visual_scene(self):
        view,terrain=window()
        view.set_collision_terrain(terrain)
        self.assertEqual(view.mode.get(),"Textures")
        self.assertIsNone(view.comparison_kcl)
        raw=view.source_collision_kcl
        self.assertEqual(raw.vertices,terrain.vertices)
        self.assertEqual(raw.faces,terrain.faces)
        self.assertEqual(raw.source_scale,1.)
        self.assertEqual(raw.source_translation,(0.,0.,0.))
        self.assertEqual(raw.display_rotation_degrees,0)
        for p in terrain.vertices:
            self.assertEqual(source_to_visual_display(p,raw),p)
        self.assertEqual(len(raw.edge_faces),6)
        self.assertEqual(raw.colors[0].lower(),"#73e998")

    def test_both_selection_without_registration_visibly_declines_not_silent(self):
        view,terrain=window()
        view.set_collision_terrain(terrain)
        view.mode.set("Both")
        view._mode_changed()
        self.assertEqual(view.mode.get(),"Textures")
        self.assertIn("BOTH UNAVAILABLE",view.comparison_status.get())
        self.assertIn("independent",view.comparison_status.get())
        self.assertIn("Choose Collision",view.comparison_status.get())
        self.assertIsNotNone(view.source_collision_kcl)

    def test_collision_mode_uses_separate_source_camera_and_restores_visual(self):
        view,terrain=window()
        view.set_collision_terrain(terrain)
        source_eye=fit_camera(terrain.vertices)
        original_eye=view.camera
        view.mode.set("Collision")
        view._mode_changed()
        self.assertEqual(view.mode.get(),"Collision")
        self.assertEqual(view.camera,source_eye)
        self.assertIn("SOURCE-ONLY",view.comparison_status.get())
        self.assertIn("1:1",view.comparison_status.get())
        self.assertIsNotNone(view.source_collision_kcl)
        # Temporary camera navigation persists on next Collision visit
        moved=view.camera._replace(
            position=(view.camera.position[0]+2.,
                      view.camera.position[1],
                      view.camera.position[2]))
        view.camera=moved
        view.mode.set("Textures")
        view._mode_changed()
        self.assertEqual(view.camera,original_eye)
        view.mode.set("Collision")
        view._mode_changed()
        self.assertEqual(view.camera,moved)
        view.frame()
        self.assertEqual(view.camera,source_eye)
        view.mode.set("Textures")
        view._mode_changed()
        self.assertEqual(view.camera,original_eye)

    def test_rotation_of_failed_comparison_never_disables_collision_view(self):
        view,terrain=window()
        view.set_collision_terrain(terrain)
        view.mode.set("Collision")
        view._mode_changed()
        view.set_display_rotation(0)
        self.assertEqual(view.mode.get(),"Collision")
        self.assertIsNone(view.comparison_kcl)
        self.assertIn("SOURCE-ONLY",view.comparison_status.get())

    def test_unverified_trial_requires_explicit_opt_in(self):
        view,terrain=window()
        view.set_collision_terrain(terrain)
        self.assertIsNone(view.comparison_kcl)
        view.manual_overlay_trial.set(True)
        view._toggle_manual_overlay()
        self.assertEqual(view.mode.get(),"Both")
        self.assertIsNotNone(view.comparison_kcl)
        self.assertIn("MANUAL UNVERIFIED",view.comparison_status.get())
        self.assertNotEqual(view.comparison_kcl.source_scale,1.)
        view.manual_overlay_trial.set(False)
        view._toggle_manual_overlay()
        self.assertIsNone(view.comparison_kcl)
        self.assertEqual(view.mode.get(),"Textures")

    def test_render_queue_uses_source_only_kcl_not_missing_both_fit(self):
        view,terrain=window()
        view.set_collision_terrain(terrain)
        view._closed=False
        view._request_version=21
        view.drag_button=None
        view._held_keys=set()
        view.canvas=Mock()
        view.canvas.winfo_width.return_value=800
        view.canvas.winfo_height.return_value=600
        view.status=Var("idle")
        view._start_latest=Mock()
        view.mode.set("Collision")
        view._mode_changed()
        view._request_full_render()
        self.assertEqual(view._queued[4],"Collision")
        self.assertIs(view._queued[5],view.source_collision_kcl)
        view.mode.set("Both")
        view._request_full_render()
        self.assertEqual(view._queued[4],"Textures")
        self.assertIsNone(view._queued[5])

    def test_source_only_kcl_is_drawn_without_any_texture_model(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow optional test dependency unavailable")
        view,terrain=window()
        raw=prepare_source_only_kcl(terrain)
        cam=fit_camera(raw.vertices)
        image=Image.new("RGB",(320,240),(19,32,46))
        drawn=draw_comparison(image,raw,cam,mode="Collision")
        self.assertEqual(drawn.size,(320,240))
        self.assertNotEqual(drawn.getbbox(),None)
        self.assertNotEqual(drawn.tobytes(),image.tobytes())
        # Rendering contract permits only EXACTLY 94 numeric bases;
        # generate synthetic stand-ins, never relax strict source count.
        bases=tuple((
            terrain.vertices[i%len(terrain.vertices)][0]+i*.003,
            terrain.vertices[i%len(terrain.vertices)][1],
            terrain.vertices[i%len(terrain.vertices)][2]-i*.002)
            for i in range(94))
        trees=draw_tree_comparison(
            image.copy(),raw,cam,bases,
            illustrations=False, labels=True)
        self.assertEqual(trees.size,(320,240))


if __name__=="__main__":
    unittest.main()
