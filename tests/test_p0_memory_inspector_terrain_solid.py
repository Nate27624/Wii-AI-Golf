"""Pure synthetic source-material solid rendering and startup checks."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.inspector.terrain import TerrainMesh, load_private_obj, surface_style, NEUTRAL
from wii_ai_golf.inspector.terrain_solid import back_to_front, camera_depth, shaded_hex
from wii_ai_golf.inspector.gui import Inspector

spec = importlib.util.spec_from_file_location(
    "_terrain_solid_launcher", ROOT / "scripts" / "p0_memory_inspector.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)

A = ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 0.0, 2.0))
B = ((0.0, 0.0, 5.0), (2.0, 0.0, 5.0), (0.0, 0.0, 7.0))


class SolidTerrainTests(unittest.TestCase):
    def test_shaded_color_is_valid_and_deterministic(self):
        value = shaded_hex(surface_style(6)[1], A)
        self.assertRegex(value, r"^#[0-9a-f]{6}$")
        self.assertEqual(value, shaded_hex(surface_style(6)[1], A))
        self.assertNotEqual(value, shaded_hex(surface_style(3)[1], A))

    def test_shading_never_interprets_untyped_triangle_as_fairway(self):
        self.assertEqual(surface_style(None), NEUTRAL)
        self.assertNotEqual(shaded_hex(NEUTRAL[1], A), shaded_hex(surface_style(1)[1], A))

    def test_winding_independent_visual_lighting(self):
        self.assertEqual(shaded_hex("#abcdef", A),
                         shaded_hex("#abcdef", (A[0], A[2], A[1])))

    def test_invalid_triangle_fails(self):
        with self.assertRaises(ValueError):
            shaded_hex("#abcdef", ((0.0,)*3,)*3)
        with self.assertRaises(ValueError):
            shaded_hex("bogus", A)

    def test_painter_order_keeps_source_attributes(self):
        entries = ((B, 7), (A, 6))
        sorted_faces = back_to_front(entries, 0.0, 0.0)
        self.assertEqual(sorted_faces, ((B, 7), (A, 6)))
        self.assertLess(camera_depth(B[0], 0.0, 0.0),
                        camera_depth(A[0], 0.0, 0.0))
        self.assertEqual({attr for _, attr in sorted_faces}, {6, 7})

    def test_camera_rotation_changes_depth(self):
        self.assertNotEqual(camera_depth(B[0], 0, 0),
                            camera_depth(B[0], 1.0, 0))
        with self.assertRaises(ValueError):
            back_to_front(((A, None),), float("nan"), 0.0)

    def test_matched_source_labels_survive_decimation_and_sort(self):
        mesh = TerrainMesh(A + B, ((0,1,2), (3,4,5)),
                           "a"*64, "PRIVATE.obj", (6, 7))
        items = mesh.drawing_colored_faces(focused=False, limit=2)
        self.assertEqual({attr for _, attr in back_to_front(items, 0, 0)}, {6, 7})

    def test_gui_draws_source_colored_polygons_not_only_edges(self):
        from wii_ai_golf.inspector.replay import AIM, BALL, CACHE
        class FakeCanvas:
            def __init__(self):
                self.ops = []
            def delete(self, *a, **k):
                pass
            def winfo_width(self):
                return 640
            def winfo_height(self):
                return 480
            def create_polygon(self, *a, **kw):
                self.ops.append(("polygon", kw))
            def create_line(self, *a, **kw):
                self.ops.append(("line", kw))
            def create_text(self, *a, **kw):
                self.ops.append(("text", kw))
            def create_oval(self, *a, **kw):
                self.ops.append(("oval", kw))
        class Sample:
            source_qualified = True
            source_digest = "synthetic"
            words = {}
            def vec(self, channel):
                return {BALL: (0.0, 0.0, 0.0),
                        CACHE: (0.0, 0.0, 0.0),
                        "pin_candidate": (1.0, 0.0, 1.0),
                        "tee_start_candidate": (0.0, 0.0, 0.0)}.get(channel)
        class Value:
            def __init__(self, value):
                self.value = value
            def get(self):
                return self.value
        canvas = FakeCanvas()
        sample = Sample()
        view = SimpleNamespace(
            canvas=canvas, replay=SimpleNamespace(samples=(sample,)),
            index=Value(0), yaw=0.65, pitch=0.48,
            terrain_mesh=TerrainMesh(
                A, ((0, 1, 2),), "a"*64, "synthetic", (6,)),
            terrain_visible=Value(True), terrain_focus=Value(False),
            terrain_colors=Value(True), terrain_solid=Value(True),
            terrain_edges=Value(False),
            terrain_status=Mock(), landmark_status=Mock(), aim_status=Mock(),
            baseline=None, aim_baseline_source=None, aim_baseline_mode="",
            live_worker=None, live_last=None,
            a_status=Value("A RELEASED"), a_reason=Value("synthetic"),
        )
        view.draw_a_overlay = lambda: Inspector.draw_a_overlay(view)
        Inspector.draw_path(view)
        solid = [kw for kind, kw in canvas.ops
                 if kind == "polygon" and "terrain_solid_face" in kw.get("tags", ())]
        self.assertEqual(len(solid), 1)
        self.assertEqual(solid[0]["fill"], shaded_hex(surface_style(6)[1], A))
        self.assertFalse(any(kind == "line" and "terrain_wire_edge" in kw.get("tags", ())
                             for kind, kw in canvas.ops))
        view.terrain_solid = Value(False)
        view.terrain_edges = Value(True)
        canvas.ops.clear()
        Inspector.draw_path(view)
        wire = [kw for kind, kw in canvas.ops
                if kind == "line" and "terrain_wire_edge" in kw.get("tags", ())]
        self.assertEqual(len(wire), 1)

    def test_launcher_passes_explicit_obj_without_connecting(self):
        from wii_ai_golf.inspector import gui
        with patch.object(gui, "launch", return_value=0) as launch:
            self.assertEqual(launcher.main(["--terrain-obj", "private.obj"]), 0)
        launch.assert_called_once_with("", "", "private.obj")

    def test_startup_reuses_strict_loader(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"synth.obj"
            path.write_text(
                "v 0 0 0\nv 2 0 0\nv 0 0 2\n"
                "g KCL_OGWS_0006\nf 1 2 3\n", encoding="ascii")
            view = SimpleNamespace(terrain_mesh=None, terrain_visible=Mock(),
                                   terrain_status=Mock(), draw_path=Mock())
            self.assertTrue(Inspector.load_terrain_path(view, str(path)))
            self.assertEqual(view.terrain_mesh.face_materials, (6,))
            view.terrain_visible.set.assert_called_once_with(True)
            view.draw_path.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
