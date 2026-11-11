"""Synthetic 94-tree viewer tests; no private RAM, OBJ, ROM or texture assets."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.inspector.tree_render import (
    camera_depth, draw_tree_layer, fit_points, placeholder_faces, placeholder_size,
)
from wii_ai_golf.inspector.tree_positions import SOURCE_TREE_COUNT


POSITIONS = tuple(
    (float(i % 10) * 10.0, float(i // 10), float(i // 10) * 14.0)
    for i in range(SOURCE_TREE_COUNT)
)


class FakeCanvas:
    def __init__(self):
        self.polygons = []
        self.ovals = []
        self.texts = []

    def create_polygon(self, *args, **kwargs):
        self.polygons.append((args, kwargs))

    def create_oval(self, *args, **kwargs):
        self.ovals.append((args, kwargs))

    def create_text(self, *args, **kwargs):
        self.texts.append((args, kwargs))


def xy(p):
    return (p[0] + p[2] * 0.1, 100.0 - p[1] - p[2] * 0.2)


class TreeVisualTests(unittest.TestCase):
    def test_all_94_exact_bases_in_point_only_mode(self):
        canvas = FakeCanvas()
        n = draw_tree_layer(canvas, POSITIONS, xy, .6, .5,
                            illustrations=False, labels=False)
        self.assertEqual(n, 94)
        self.assertEqual(len(canvas.polygons), 0)
        self.assertEqual(len(canvas.ovals), 94)
        self.assertEqual(len(canvas.texts), 0)
        for i, (_, kwargs) in enumerate(canvas.ovals, 1):
            self.assertIn("tree_exact_source_base", kwargs["tags"])
            self.assertIn(f"tree_source_{i:03d}", kwargs["tags"])

    def test_all_94_have_12_bounded_illustrative_3d_faces(self):
        faces = placeholder_faces(POSITIONS)
        self.assertEqual(len(faces), 94 * 12)
        self.assertEqual({face.source_index for face in faces}, set(range(1, 95)))
        self.assertEqual(len([f for f in faces if len(f.vertices) == 4]), 94 * 4)
        self.assertEqual(len([f for f in faces if len(f.vertices) == 3]), 94 * 8)
        self.assertTrue(all(math.isfinite(v) for f in faces for p in f.vertices for v in p))
        self.assertGreater(placeholder_size(POSITIONS), 0.0)
        self.assertIs(placeholder_faces(POSITIONS), faces)  # geometry cached

    def test_illustration_changes_only_extra_geometry_not_base_points(self):
        canvas = FakeCanvas()
        n = draw_tree_layer(canvas, POSITIONS, xy, .5, .6,
                            illustrations=True, labels=True)
        self.assertEqual(n, 94)
        self.assertEqual(len(canvas.polygons), 94 * 12)
        self.assertEqual(len(canvas.ovals), 94)
        self.assertEqual(len(canvas.texts), 94)
        self.assertEqual(canvas.texts[0][1]["text"], "T01")
        self.assertTrue(all("tree_illustrative_nonphysical" in opts["tags"]
                            for _, opts in canvas.polygons))
        for base, (coords, _) in zip(POSITIONS, canvas.ovals):
            self.assertAlmostEqual((coords[0]+coords[2])/2, xy(base)[0])
            self.assertAlmostEqual((coords[1]+coords[3])/2, xy(base)[1])

    def test_framing_keeps_exact_bases_and_adds_crowns_only_when_enabled(self):
        self.assertEqual(fit_points(POSITIONS, illustrations=False), POSITIONS)
        extended = fit_points(POSITIONS, illustrations=True)
        self.assertEqual(extended[:94], POSITIONS)
        self.assertGreater(len(extended), 94)

    def test_camera_depth_is_finite_and_source_frame_only(self):
        self.assertTrue(math.isfinite(camera_depth((4., 5., 6.), 0.8, 0.4)))
        with self.assertRaises(ValueError):
            camera_depth((1., 2., 3.), float("nan"), .5)

    def test_reject_partial_or_nonfinite_point_sets_without_drawing(self):
        for invalid in (POSITIONS[:-1],
                        POSITIONS[:-1] + ((float("inf"), 0., 0.),)):
            with self.subTest(invalid=invalid[-1]):
                canvas = FakeCanvas()
                with self.assertRaises(ValueError):
                    draw_tree_layer(canvas, invalid, xy, .5, .4,
                                    illustrations=True, labels=False)
                self.assertEqual(len(canvas.polygons), 0)
                self.assertEqual(len(canvas.ovals), 0)

    def test_no_model_assets_collision_or_physics_exposed(self):
        face = placeholder_faces(POSITIONS)[0]
        self.assertFalse(hasattr(face, "collision_radius"))
        self.assertFalse(hasattr(face, "physical_material"))
        self.assertFalse(hasattr(face, "texture"))
        self.assertFalse(hasattr(face, "source_species"))


if __name__ == "__main__":
    unittest.main()
