"""One shared original UV+KCL camera, explicitly UNVERIFIED alignment tests.

All meshes are synthetically created; no game assets, ROM, Dolphin, network,
memory writes or non-source texture guesses.
"""
from __future__ import annotations

from pathlib import Path
import time
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
    prepare_comparison_kcl, overlay_summary, draw_comparison,
    source_to_visual_display)
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

    def test_operator_180_yaw_rotates_kcl_about_visual_center(self):
        model, collision = scene()
        before_visual = model.vertices
        before_native_kcl = collision.vertices
        identity = prepare_comparison_kcl(collision, model, rotation_degrees=0)
        turned = prepare_comparison_kcl(collision, model, rotation_degrees=180)
        # The source replay/OBJ XYZ and genuine visual DAE stay immutable.
        self.assertEqual(model.vertices, before_visual)
        self.assertEqual(collision.vertices, before_native_kcl)
        self.assertEqual(identity.vertices[0], (0., 0., 0.))
        self.assertEqual(turned.vertices[0], (100., 0., 100.))
        self.assertEqual(turned.vertices[3], (0., 0., 0.))
        self.assertEqual(identity.source_sha256, turned.source_sha256)
        self.assertEqual(identity.faces, turned.faces)
        self.assertEqual(identity.colors, turned.colors)
        self.assertEqual(turned.display_center, (50., 0., 50.))
        self.assertEqual(turned.display_rotation_degrees, 180)
        self.assertIn("yaw 180°", overlay_summary(turned))
        self.assertIn("UNVERIFIED", overlay_summary(turned))

    def test_source_tree_bases_share_identical_kcl_display_transform(self):
        model, collision = scene()
        for angle in (0, 90, 180, 270):
            with self.subTest(display_yaw=angle):
                comp = prepare_comparison_kcl(
                    collision, model, rotation_degrees=angle)
                # Same unmodified source vertex represents either a tree base
                # or one KCL vertex. Both MUST project to the same XYZ.
                for original, drawn in zip(collision.vertices, comp.vertices):
                    self.assertEqual(
                        source_to_visual_display(original, comp), drawn)
                # KCL source center stays at visual source center under ALL
                # trial rotations, including quarter turns.
                mid = (5., 1., 5.)
                self.assertEqual(
                    source_to_visual_display(mid, comp),
                    (50., 0., 50.))
                xs = [v[0] for v in comp.vertices]
                zs = [v[2] for v in comp.vertices]
                self.assertAlmostEqual(max(xs)-min(xs), 100.)
                self.assertAlmostEqual(max(zs)-min(zs), 100.)

    def test_trial_display_yaw_rejects_invalid_values(self):
        model, collision = scene()
        for yaw in (45, -90, 360, "180", True, 90.0, float("nan")):
            with self.subTest(yaw=yaw), self.assertRaises(ValueError):
                prepare_comparison_kcl(collision, model,
                                       rotation_degrees=yaw)

    def test_visual_control_recomputes_existing_source_without_reloading(self):
        model, collision = scene()
        class Var:
            def __init__(self, v): self.v = v
            def get(self): return self.v
            def set(self, v): self.v = v
        view = object.__new__(TexturedPreviewWindow)
        view.model = model
        view.mode = Var("Textures")
        view.display_rotation = Var(180)
        view.comparison_status = Var("none")
        view.schedule = Mock()
        view.set_collision_terrain(collision)
        self.assertEqual(view.mode.get(), "Both")
        self.assertEqual(view.comparison_kcl.display_rotation_degrees, 180)
        self.assertIn("yaw 180°", view.comparison_status.get())
        before = collision.vertices
        view.set_display_rotation(0)
        self.assertEqual(view.display_rotation.get(), 0)
        self.assertEqual(view.comparison_kcl.display_rotation_degrees, 0)
        self.assertEqual(view._source_terrain.vertices, before)
        view.set_display_rotation(90)
        self.assertEqual(view.comparison_kcl.display_rotation_degrees, 90)
        with self.assertRaises(ValueError):
            view.set_display_rotation(22)
        self.assertEqual(view.comparison_kcl.display_rotation_degrees, 90)
        self.assertEqual(model.vertices, scene()[0].vertices)
        self.assertEqual(view.schedule.call_count, 3)

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

    def test_manual_review_bounds_transform_preserves_original_KCL_and_trees(self):
        model, collision = scene()
        orig_kcl = collision.vertices
        orig_visual = model.vertices
        baseline = prepare_comparison_kcl(collision, model)
        manual = prepare_comparison_kcl(
            collision, model, rotation_degrees=90,
            display_scale_multiplier=1.25,
            display_offset_fraction_xz=(.05, -.03))
        self.assertAlmostEqual(manual.source_scale,
                               prepare_comparison_kcl(
                                   collision, model, rotation_degrees=90
                               ).source_scale * 1.25)
        for source, rendered in zip(collision.vertices, manual.vertices):
            self.assertEqual(source_to_visual_display(source, manual), rendered)
        self.assertEqual(collision.vertices, orig_kcl)
        self.assertEqual(model.vertices, orig_visual)
        self.assertNotEqual(manual.vertices, baseline.vertices)
        self.assertEqual(manual.display_scale_multiplier, 1.25)
        self.assertIn("manual scale", overlay_summary(manual))

    def test_review_controls_are_reversible_topdown_and_do_not_modify_sources(self):
        class Var:
            def __init__(self, v): self.v = v
            def get(self): return self.v
            def set(self, v): self.v = v
        model, collision = scene()
        view = object.__new__(TexturedPreviewWindow)
        view.model = model
        view.home_camera = frame_playable_camera(model)
        view.camera = view.home_camera
        view.mode = Var("Textures")
        view.display_rotation = Var(180)
        view.comparison_status = Var("")
        view.review_status = Var("")
        view.review_manual = False
        view.review_scale = 1.
        view.review_offset_xz = (0., 0.)
        view.tree_illustrations = True
        view._source_terrain = collision
        view.schedule = Mock()
        view.start_visual_review()
        self.assertEqual(view.mode.get(), "Overlay")
        self.assertEqual(view.display_rotation.get(), 0)
        self.assertTrue(view.review_manual)
        self.assertFalse(view.tree_illustrations)
        self.assertGreater(view.camera.position[1], view.camera.focus[1])
        self.assertIn("UNVERIFIED", view.comparison_status.get())
        fit_before = view.comparison_kcl.vertices
        view.nudge_visual_review("scale", 1)
        view.nudge_visual_review("x", 1)
        view.nudge_visual_review("z", -1)
        self.assertEqual(view.review_offset_xz, (.01, -.01))
        self.assertAlmostEqual(view.review_scale, 1.05)
        self.assertNotEqual(fit_before, view.comparison_kcl.vertices)
        self.assertEqual(collision.vertices, scene()[1].vertices)
        self.assertEqual(model.vertices, scene()[0].vertices)
        view.reset_visual_review()
        self.assertFalse(view.review_manual)
        self.assertEqual(view.review_scale, 1.)
        self.assertEqual(view.review_offset_xz, (0., 0.))
        self.assertEqual(view.display_rotation.get(), 0)
        self.assertEqual(view.mode.get(), "Both")
        with self.assertRaises(ValueError):
            view.nudge_visual_review("rotate-native", 1)

    def test_manual_visual_adjustments_reject_unbounded_guesses(self):
        model, collision = scene()
        for scale in (.2, 4.01, float("nan"), True):
            with self.subTest(scale=scale), self.assertRaises(ValueError):
                prepare_comparison_kcl(
                    collision, model, display_scale_multiplier=scale)
        for offsets in ((2., 0.), (float("inf"), 0.), (0.,), [0., 0.]):
            with self.subTest(offsets=offsets), self.assertRaises(ValueError):
                prepare_comparison_kcl(
                    collision, model, display_offset_fraction_xz=offsets)

    def test_visual_overlay_and_split_share_camera_without_changes_to_pixels(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Optional Pillow needed")
        model, collision = scene()
        comp = prepare_comparison_kcl(collision, model)
        source = Image.new("RGB", (300, 220), (60, 75, 90))
        source_bytes = source.tobytes()
        camera = frame_playable_camera(model)
        alpha = draw_comparison(source.copy(), comp, camera, mode="Overlay")
        split = draw_comparison(source.copy(), comp, camera, mode="Split")
        self.assertEqual(alpha.size, source.size)
        self.assertEqual(split.size, source.size)
        self.assertEqual(source.tobytes(), source_bytes)
        self.assertNotEqual(alpha.tobytes(), source_bytes)
        self.assertNotEqual(split.tobytes(), source_bytes)
        self.assertEqual(split.getpixel((0, 0)), source.getpixel((0, 0)))
        self.assertEqual(split.getpixel((150, 0)), (247, 232, 138))

    def test_arrow_keys_hold_continuously_without_rmb_while_wasd_requires_it(self):
        model, _=scene()
        view=object.__new__(TexturedPreviewWindow)
        view.camera=frame_playable_camera(model)
        view.home_camera=view.camera
        view.full_camera=fit_camera(model.vertices)
        view.drag_button=None
        view._closed=False
        view.schedule=Mock()
        view.top=Mock()
        view.top.after.return_value="timer"
        view._nav_timer=None
        view._held_keys=set()
        view._pending_key_releases={}
        view._shift_held=False
        view._last_nav_tick=time.perf_counter()
        view._last_nav_render=0.
        start=view.camera.position
        self.assertEqual(view.key_move(SimpleNamespace(keysym="Up",state=0)),
                         "break")
        # Press is not a discrete unit jump.
        self.assertEqual(start,view.camera.position)
        for _ in range(5):
            view._last_nav_tick=time.perf_counter()-.02
            view._navigation_tick()
        self.assertNotEqual(start,view.camera.position)
        moved=view.camera.position
        # OS repeat keypress does NOT produce an immediate extra step.
        self.assertEqual(view.key_move(SimpleNamespace(keysym="Up",state=0)),
                         "break")
        self.assertEqual(moved,view.camera.position)
        view._held_keys.clear()
        self.assertIsNone(view.key_move(SimpleNamespace(keysym="w",state=0)))
        self.assertEqual(moved,view.camera.position)
        for key in ("Down","Left","Right"):
            before=view.camera.position
            self.assertEqual(view.key_move(SimpleNamespace(keysym=key,state=0)),
                             "break")
            self.assertEqual(before,view.camera.position)
            view._last_nav_tick=time.perf_counter()-.025
            view._navigation_tick()
            self.assertNotEqual(before,view.camera.position)
            view._held_keys.clear()
            view._nav_timer=None
        view.frame()
        self.assertEqual(view.camera,view.home_camera)
        view.frame_all()
        self.assertEqual(view.camera,view.full_camera)

    def test_autorepeat_release_is_cancelled_and_focus_loss_stops_flying(self):
        model, _=scene()
        view=object.__new__(TexturedPreviewWindow)
        view.camera=frame_playable_camera(model)
        view.drag_button=None
        view._closed=False
        view.schedule=Mock()
        view.top=Mock()
        view.top.after.return_value="timer"
        view._nav_timer=None
        view._held_keys=set()
        view._pending_key_releases={}
        view._shift_held=False
        view._last_nav_tick=time.perf_counter()
        view._last_nav_render=0.
        view.key_move(SimpleNamespace(keysym="Up",state=0))
        view.key_release(SimpleNamespace(keysym="Up",state=0))
        self.assertIn("up",view._pending_key_releases)
        view.key_move(SimpleNamespace(keysym="Up",state=0))
        self.assertNotIn("up",view._pending_key_releases)
        self.assertIn("up",view._held_keys)
        view.top.after_cancel.assert_called_with("timer")
        view._last_nav_tick=time.perf_counter()-.02
        view._navigation_tick()
        view.focus_lost()
        self.assertFalse(view._held_keys)
        self.assertIsNone(view._nav_timer)
        after=view.camera.position
        view._navigation_tick()
        self.assertEqual(view.camera.position,after)


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
