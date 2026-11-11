"""Synthetic tests for unified 94-tree original-visual/KCL overlay and startup."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    from PIL import Image
except ImportError:
    Image = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wii_ai_golf.inspector.scene_camera import VisualCamera
from wii_ai_golf.inspector.tree_render import placeholder_faces
from wii_ai_golf.inspector.unified_source_view import (
    ComparisonKCL, draw_tree_comparison,
)


def points():
    return tuple((float(i % 12)*8., 0., float(i // 12)*12.)
                 for i in range(94))


def comparison():
    return ComparisonKCL("a"*64,
                         ((0., 0., 0.), (96., 0., 0.), (0., 0., 96.)),
                         ((0, 1, 2),), ("#669977",), 1.,
                         (0., 0., 0.), (1., 1.),
                         ((0, 1), (1, 2), (0, 2)))


def camera():
    return VisualCamera(position=(43., 75., 240.),
                        focus=(43., 0., 30.),
                        yaw=0., pitch=.1, scale=200.)


class PrivateTreeUnifiedTests(unittest.TestCase):
    @unittest.skipUnless(Image is not None, "optional Pillow not installed")
    def test_94_dots_are_visible_in_shared_source_camera(self):
        from PIL import Image
        image = Image.new("RGB", (700, 400), (22, 33, 44))
        before = image.tobytes()
        result = draw_tree_comparison(
            image, comparison(), camera(), points(), illustrations=False)
        self.assertIs(image, result)
        self.assertNotEqual(image.tobytes(), before)

    @unittest.skipUnless(Image is not None, "optional Pillow not installed")
    def test_unverified_transform_absent_does_not_guess_markers(self):
        from PIL import Image
        image = Image.new("RGB", (700, 400), (22, 33, 44))
        before = image.tobytes()
        result = draw_tree_comparison(image, None, camera(), points())
        self.assertIs(result, image)
        self.assertEqual(image.tobytes(), before)

    @unittest.skipUnless(Image is not None, "optional Pillow not installed")
    def test_bad_shape_rejected_before_visual_render(self):
        from PIL import Image
        image = Image.new("RGB", (700, 400))
        with self.assertRaises(ValueError):
            draw_tree_comparison(image, comparison(), camera(), points()[:93])
        with self.assertRaises(ValueError):
            draw_tree_comparison(image, comparison(), camera(),
                                 points()[:-1] + ((float("nan"), 0., 0.),))

    @unittest.skipUnless(Image is not None, "optional Pillow not installed")
    def test_exact_base_only_and_illustrative_modes_differ(self):
        from PIL import Image
        plain = Image.new("RGB", (700, 400), (22, 33, 44))
        shaded = plain.copy()
        draw_tree_comparison(plain, comparison(), camera(), points(),
                             illustrations=False)
        draw_tree_comparison(shaded, comparison(), camera(), points(),
                             illustrations=True)
        self.assertNotEqual(plain.tobytes(), shaded.tobytes())
        self.assertEqual(len(placeholder_faces(points())), 94*12)

    def test_preview_switches_tree_settings_without_dolphin(self):
        from wii_ai_golf.inspector.textured_preview import TexturedPreviewWindow
        preview = TexturedPreviewWindow.__new__(TexturedPreviewWindow)
        hits = []
        preview.schedule = lambda: hits.append(True)
        with self.assertRaises(ValueError):
            preview.set_tree_overlay(points()[:93], visible=True,
                                     illustrations=True, labels=False)
        preview.set_tree_overlay(points(), visible=True,
                                 illustrations=True, labels=False)
        self.assertEqual(preview.tree_overlay, points())
        self.assertTrue(preview.tree_overlay_visible)
        preview.set_tree_overlay(points(), visible=False,
                                 illustrations=False, labels=True)
        self.assertFalse(preview.tree_overlay_visible)
        self.assertFalse(preview.tree_illustrations)
        self.assertTrue(preview.tree_labels)
        self.assertEqual(len(hits), 2)

    def test_gui_has_both_persistent_trees_and_renderer_controls(self):
        from wii_ai_golf.inspector.gui import Inspector
        self.assertTrue(hasattr(Inspector, "restore_private_assets"))
        self.assertTrue(hasattr(Inspector, "_sync_visual_trees"))
        self.assertTrue(hasattr(Inspector, "load_tree_positions"))
        self.assertTrue(hasattr(Inspector, "load_visual_path"))
        self.assertTrue(hasattr(Inspector, "load_terrain_labels_path"))
        self.assertTrue(hasattr(Inspector, "load_terrain_path"))


if __name__ == "__main__":
    unittest.main()
