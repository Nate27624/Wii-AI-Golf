"""Synthetic Unity-like source camera tests; no Wii art, Dolphin or live data."""
from __future__ import annotations

from math import isclose
import time
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.inspector.scene_camera import (
    camera_axes, fit_camera, look_in_place, orbit, pan, dolly, move,
    held_navigation_direction, move_continuous,
)
from wii_ai_golf.inspector.texture_render import render_preview
from wii_ai_golf.inspector.textured_preview import TexturedPreviewWindow
from wii_ai_golf.inspector.visual_model import PrivateVisualModel, VisualFace


VERTICES = ((-2., -2., 0.), (2., -2., 0.), (0., 2., 0.),
            (-2., -2., 2.), (2., -2., 2.), (0., 2., 2.))


class SceneCameraTests(unittest.TestCase):
    def setUp(self):
        self.cam = fit_camera(VERTICES)

    def test_rmb_look_does_not_translate_camera_at_all(self):
        old = self.cam.position
        out = look_in_place(self.cam, 125, -54)
        self.assertEqual(out.position, old)
        self.assertEqual(out.focus, self.cam.focus)
        self.assertNotEqual(out.yaw, self.cam.yaw)
        self.assertNotEqual(out.pitch, self.cam.pitch)
        self.assertEqual(self.cam.position, old)

    def test_orbit_changes_camera_position_but_preserves_focus_distance(self):
        out = orbit(self.cam, 87, 42)
        self.assertEqual(out.focus, self.cam.focus)
        self.assertNotEqual(out.position, self.cam.position)
        def distance(a, b):
            return sum((a[i]-b[i])**2 for i in range(3)) ** .5
        self.assertAlmostEqual(distance(out.position, out.focus),
                               distance(self.cam.position, self.cam.focus))

    def test_middle_pan_moves_both_camera_and_target_not_rotation(self):
        out = pan(self.cam, 30, -15, 720)
        self.assertEqual((out.yaw, out.pitch), (self.cam.yaw, self.cam.pitch))
        self.assertNotEqual(out.position, self.cam.position)
        delta_position = tuple(out.position[i]-self.cam.position[i] for i in range(3))
        delta_focus = tuple(out.focus[i]-self.cam.focus[i] for i in range(3))
        for a, b in zip(delta_position, delta_focus):
            self.assertAlmostEqual(a, b, places=8)

    def test_wasd_moves_without_changing_facing(self):
        for direction in (
            {"forward": 1}, {"forward": -1}, {"right": 1},
            {"right": -1}, {"vertical": 1}, {"vertical": -1},
        ):
            with self.subTest(direction=direction):
                out = move(self.cam, **direction)
                self.assertNotEqual(out.position, self.cam.position)
                self.assertEqual((out.yaw, out.pitch), (self.cam.yaw, self.cam.pitch))
        self.assertNotEqual(dolly(self.cam, 2.).position, self.cam.position)

    def test_camera_axis_basis_is_orthogonal_normalized(self):
        axes = camera_axes(self.cam.yaw, self.cam.pitch)
        for axis in axes:
            self.assertAlmostEqual(sum(v*v for v in axis), 1., places=8)
        for i in range(3):
            for j in range(i):
                self.assertAlmostEqual(sum(a*b for a, b in zip(axes[i], axes[j])),
                                       0., places=8)

    def test_true_perspective_raster_rotates_about_fixed_camera_location(self):
        try:
            import numpy as np
            from PIL import Image
        except ImportError:
            self.skipTest("Optional visual renderer unavailable")
        model = PrivateVisualModel(
            vertices=VERTICES,
            uvs=((0., 0.), (1., 0.), (0., 1.)),
            faces=(
                VisualFace((0, 1, 2), (0, 1, 2), "M_Solid"),
                VisualFace((3, 4, 5), (0, 1, 2), "M_Solid"),
            ),
            textures={}, obj_sha256="synthetic", mtl_sha256="synthetic",
            source_name="synthetic-only", solid_colors={"M_Solid": (80, 180, 40)})
        original, drawn = render_preview(
            model, 240, 180, camera=self.cam, textures={})
        self.assertGreater(drawn, 0)
        turned = look_in_place(self.cam, 45., 0.)
        self.assertEqual(turned.position, self.cam.position)
        rotated, other = render_preview(
            model, 240, 180, camera=turned, textures={})
        self.assertNotEqual(np.asarray(original).tobytes(),
                            np.asarray(rotated).tobytes())

    def test_rmb_horizontal_direction_reversed_and_eye_never_moves(self):
        for dx in (-125, 125):
            out = look_in_place(self.cam, dx, 0)
            self.assertEqual(out.position, self.cam.position)
            self.assertEqual(out.focus, self.cam.focus)
            self.assertEqual(out.pitch, self.cam.pitch)
            self.assertEqual((out.yaw < self.cam.yaw), (dx > 0))

    def test_continuous_time_normalized_arrow_and_rmb_fly(self):
        self.assertEqual(held_navigation_direction({"up"}), (1., 0., 0.))
        self.assertEqual(held_navigation_direction({"down"}), (-1., 0., 0.))
        self.assertEqual(held_navigation_direction({"left"}), (0., -1., 0.))
        self.assertEqual(held_navigation_direction({"right"}), (0., 1., 0.))
        self.assertEqual(held_navigation_direction({"w"}), (0., 0., 0.))
        self.assertEqual(held_navigation_direction({"w"}, right_mouse=True),
                         (1., 0., 0.))
        self.assertEqual(held_navigation_direction({"up", "down"}), (0., 0., 0.))
        diagonal = held_navigation_direction({"up", "right"})
        self.assertAlmostEqual(sum(v*v for v in diagonal), 1., places=10)
        # Moving at the same elapsed time is independent of OS repeat rate.
        first = move_continuous(self.cam, {"up"}, .016)
        second = move_continuous(first, {"up"}, .016)
        combined = move_continuous(self.cam, {"up"}, .032)
        for one, two in zip(second.position, combined.position):
            self.assertAlmostEqual(one, two, places=9)
        self.assertEqual(first.yaw, self.cam.yaw)
        self.assertEqual(first.pitch, self.cam.pitch)
        self.assertEqual(first.scale, self.cam.scale)
        for duration in (-1., float("nan")):
            with self.assertRaises(ValueError):
                move_continuous(self.cam, {"up"}, duration)

    def test_right_drag_event_preserves_eye_while_keyboard_is_continuous(self):
        view = object.__new__(TexturedPreviewWindow)
        view.camera = self.cam
        view.drag_origin = (100, 100)
        view.drag_button = 3
        view.canvas = Mock()
        view.top = Mock()
        view.top.after.return_value = "synthetic-nav-timer"
        view.schedule = Mock()
        view._closed = False
        view._held_keys = set()
        view._pending_key_releases = {}
        view._nav_timer = None
        view._shift_held = False
        view._last_nav_tick = time.perf_counter()
        view._last_nav_render = 0.
        original = view.camera.position
        view.drag_move(SimpleNamespace(x=120, y=92))
        self.assertEqual(view.camera.position, original)
        self.assertEqual(view.drag_origin, (120, 92))
        self.assertLess(view.camera.yaw, self.cam.yaw)
        self.assertEqual(view.key_move(SimpleNamespace(keysym="w", state=0)),
                         "break")
        # Keydown only sets held state; no discrete step.
        self.assertEqual(view.camera.position, original)
        view._last_nav_tick = time.perf_counter() - .03
        view._navigation_tick()
        self.assertNotEqual(view.camera.position, original)
        after = view.camera.position
        view.drag_button = 1
        view._last_nav_tick = time.perf_counter() - .03
        view._navigation_tick()
        self.assertEqual(view.camera.position, after)
        view._held_keys.clear()
        self.assertIsNone(
            view.key_move(SimpleNamespace(keysym="w", state=0)))
        self.assertEqual(view.camera.position, after)



if __name__ == "__main__":
    unittest.main()
