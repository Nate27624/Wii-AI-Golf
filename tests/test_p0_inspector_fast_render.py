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
        with self.assertRaisesRegex(VisualAssetError, "No original TEX0 diffuse appearance|source face lacks"):
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

    def test_mipmapped_bilinear_fast_and_numpy_agree(self):
        model, textures = synthetic_scene()
        textures["grass"] = np.empty((16, 16, 4), dtype=np.uint8)
        textures["grass"][:,:,:] = (12, 44, 66, 255)
        textures["grass"][:8,:8,:3] = (210, 188, 90)
        textures["grass"][8:,8:,:3] = (240, 34, 76)
        # UV range creates deliberately minified stripes/texels in motion.
        from dataclasses import replace
        tiled = replace(model, uvs=tuple((u*24.,v*24.) for u,v in model.uvs))
        fast_scene = prepare_fast_scene(tiled, textures)
        cam = fit_camera(tiled.vertices)
        native, nf = render_fast(fast_scene, 198, 166, cam, filtered=True)
        cpu, sf = render_preview(
            tiled, 198, 166, camera=cam, textures=textures, filtered=True)
        self.assertEqual(nf, sf)
        dif=np.abs(np.asarray(native).astype(np.int16) -
                   np.asarray(cpu).astype(np.int16))
        if int(dif.max()) > 2:
            ay,ax,ac=np.unravel_index(int(dif.argmax()),dif.shape)
            from wii_ai_golf.inspector.texture_sampling import screen_texture_lod
            from wii_ai_golf.inspector.fast_texture_render import _project
            xy,_=_project(fast_scene,198,166,cam)
            lods=[screen_texture_lod(xy[list(face.vertices),:2],
                      np.array([tiled.uvs[i] for i in face.uvs]),
                      16,16,int(fast_scene.mip_counts[0]))
                  for face in tiled.faces]
            print("FILTER_DIAG",{"first":(int(ax),int(ay),int(ac)),
                  "fast":tuple(np.asarray(native)[ay,ax]),
                  "slow":tuple(np.asarray(cpu)[ay,ax]),
                  "count_mismatch":int(np.count_nonzero(dif>2)),
                  "levels":lods,
                  "mip_offsets":fast_scene.mip_offsets[0].tolist(),
                  "mip_counts":fast_scene.mip_counts.tolist()})
        self.assertLessEqual(int(dif.max()), 2)

    def test_mipmap_chain_reduces_checker_speckle_without_modifying_png(self):
        from wii_ai_golf.inspector.texture_sampling import (
            build_rgba_mips, screen_texture_lod, bilinear_wrapped_rgba)
        checker = np.full((32, 32, 4), 255, dtype=np.uint8)
        yy,xx=np.indices((32,32))
        checker[:,:,:3] = (((xx+yy)%2)*255)[:,:,None]
        snapshot=checker.copy()
        chain=build_rgba_mips(checker)
        self.assertTrue(np.array_equal(checker,snapshot))
        self.assertGreaterEqual(len(chain),5)
        self.assertEqual(chain[-1].shape,(1,1,4))
        self.assertLess(abs(int(chain[-1][0,0,0])-128),3)
        level=screen_texture_lod(((0.,0.),(5.,0.),(0.,5.)),
                                 ((0.,0.),(16.,0.),(0.,16.)),
                                 32,32,len(chain))
        self.assertGreaterEqual(level,4)
        u=np.array([0.25],dtype=np.float64)
        v=np.array([0.25],dtype=np.float64)
        sampled=bilinear_wrapped_rgba(chain[level],u,v)
        self.assertLess(abs(int(sampled[0,0])-128),4)

    def test_source_texture_arrays_are_byte_identical(self):
        model, textures = synthetic_scene()
        textures["grass"][:, :4, :3] = (200, 32, 75)
        scene = prepare_fast_scene(model, textures)
        copy = scene.rgba_pixels.copy()
        self.assertEqual(copy.shape[1], 4)
        self.assertGreater(copy.shape[0], 64)  # source level 0 + preview mip chain
        self.assertEqual(tuple(copy[0, :3]), (200, 32, 75))
        self.assertTrue(np.array_equal(copy[:64], textures["grass"].reshape(-1,4)))
        self.assertEqual(int(scene.tex_offsets[0]), 0)
        self.assertEqual(int(scene.tex_widths[0]), 8)
        self.assertGreater(int(scene.mip_counts[0]), 1)
        self.assertEqual(int(scene.mip_widths[0,1]), 4)


if __name__ == "__main__":
    unittest.main()
