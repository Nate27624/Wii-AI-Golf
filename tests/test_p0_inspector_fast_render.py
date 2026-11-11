"""Synthetic-only CPU raster acceleration tests; NO game art or ROM assets."""
from __future__ import annotations

from dataclasses import replace
import time
import unittest

try:
    import numpy as np
except ImportError:
    np = None

from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.inspector.fast_texture_render import (
    accelerated_available, prepare_fast_scene, render_fast)
from wii_ai_golf.inspector.scene_camera import fit_camera
from wii_ai_golf.inspector.texture_render import render_preview
from wii_ai_golf.inspector.visual_model import (
    PrivateVisualModel, VisualFace, VisualAssetError)


def synthetic_scene(*, textured: bool = True):
    vertices = ((-3., -3., 0.), (3., -3., 0.), (-3., 3., 0.),
                (3., 3., 0.), (-3., -3., 1.))
    uv = ((0., 0.), (1., 0.), (0., 1.), (1., 1.))
    model = PrivateVisualModel(
        vertices=vertices, uvs=uv,
        faces=(VisualFace((0, 1, 2), (0, 1, 2), "grass"),
               VisualFace((1, 3, 2), (1, 3, 2), "grass")),
        textures={},
        obj_sha256="synthetic", mtl_sha256="synthetic",
        source_name="synthetic-local-test",
        solid_colors={} if textured else {"grass": (20, 180, 70)})
    texels = np.empty((8, 8, 4), dtype=np.uint8)
    texels[:, :, :] = (20, 180, 70, 255)
    return model, ({"grass": texels} if textured else {})


@unittest.skipUnless(np is not None and accelerated_available(),
                     "Optional NumPy/Numba not installed")
class NativeSourceRasterTests(unittest.TestCase):
    def test_native_cpu_uses_all_original_faces_and_pixels(self):
        model, textures = synthetic_scene()
        scene = prepare_fast_scene(model, textures)
        camera = fit_camera(model.vertices)
        native, native_faces = render_fast(scene, 260, 200, camera)
        reference, reference_faces = render_preview(
            model, 260, 200, camera=camera, textures=textures)
        self.assertEqual(native_faces, reference_faces)
        self.assertEqual(np.asarray(native).shape, (200, 260, 3))
        a = np.asarray(native).astype(np.int16)
        b = np.asarray(reference).astype(np.int16)
        self.assertLessEqual(int(np.max(np.abs(a-b))), 1)
        self.assertGreater(int(np.sum(a[:, :, 1] == 180)), 300)

    def test_native_matches_source_only_nontextured_color(self):
        model, textures = synthetic_scene(textured=False)
        scene = prepare_fast_scene(model, textures)
        cam = fit_camera(model.vertices)
        fast, count = render_fast(scene, 220, 180, cam)
        slow, original_count = render_preview(
            model, 220, 180, camera=cam, textures={})
        self.assertEqual(count, original_count)
        self.assertTrue(np.array_equal(np.asarray(fast), np.asarray(slow)))

    def test_compiled_rejects_missing_source_material(self):
        model, textures = synthetic_scene()
        with self.assertRaisesRegex(VisualAssetError, "source face lacks"):
            prepare_fast_scene(model, {})

    def test_compiled_rejects_oversized_rgba_arrays(self):
        model, textures = synthetic_scene()
        textures["grass"] = np.zeros((1, 1), dtype=np.uint8)
        with self.assertRaises(VisualAssetError):
            prepare_fast_scene(model, textures)

    def test_compiled_does_not_stride_drop_more_than_4000_faces(self):
        model, textures = synthetic_scene(textured=False)
        many = replace(model, faces=model.faces * 2251)
        packed = prepare_fast_scene(many, textures)
        self.assertEqual(packed.faces.shape[0], 4502)
        native, drawn = render_fast(packed, 64, 48,
                                   fit_camera(many.vertices))
        self.assertEqual(native.size, (64, 48))
        self.assertGreater(drawn, 0)

    def test_source_texture_arrays_are_byte_identical(self):
        model, textures = synthetic_scene()
        textures["grass"][:, :4, :3] = (200, 32, 75)
        scene = prepare_fast_scene(model, textures)
        copy = scene.rgba_pixels.copy()
        self.assertEqual(copy.shape, (64, 4))
        self.assertEqual(tuple(copy[0, :3]), (200, 32, 75))
        self.assertEqual(int(scene.tex_offsets[0]), 0)
        self.assertEqual(int(scene.tex_widths[0]), 8)


if __name__ == "__main__":
    unittest.main()
