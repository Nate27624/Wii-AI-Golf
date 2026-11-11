"""Fast source-authentic CPU UV rasterizer backed by optional Numba.

This is NOT Wii native GPU TEV. It draws original DAE-derived triangles,
the original user-local TEX0/PNG texels, the same reciprocal-depth
perspective projection, depth buffer and alpha semantics as texture_render.py.

No Blender, OpenGL/Tk embedding, separate window, upload or source asset writes.
A single nopython compiled loop eliminates Python-per-triangle/texel overhead.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

# This module is imported by the core GUI, where NumPy is OPTIONAL.
# Keep ordinary KCL/replay startup working on a minimal Python install.
try:
    import numpy as np
except ImportError:
    np = None

from .scene_camera import VisualCamera, camera_axes
from .visual_model import PrivateVisualModel, VisualAssetError

try:
    from numba import njit
except (ImportError, RuntimeError, OSError) as exc:
    njit = None
    NUMBA_IMPORT_ERROR = str(exc)
else:
    NUMBA_IMPORT_ERROR = ""

MAX_PACKED_RGBA_BYTES = 96 * 1024 * 1024
MAX_FAST_FACES = 100_000


@dataclass(frozen=True)
class FastVisualScene:
    """One-time immutable source UV/material packing for repeated camera frames."""
    xyz: Any
    uv: Any
    faces: Any
    face_uvs: Any
    material_ids: Any
    rgba_pixels: Any
    tex_offsets: Any
    tex_widths: Any
    tex_heights: Any
    solid_colors: Any


def accelerated_available() -> bool:
    return njit is not None and np is not None


def prepare_fast_scene(model: PrivateVisualModel,
                       textures: dict[str, Any]) -> FastVisualScene:
    """Use ONLY verified source PNG arrays and source diffuse colors."""
    if not accelerated_available():
        raise VisualAssetError(
            "Accelerated UV viewer requires Numba: "
            "py -3 -m pip install 'numba>=0.68.1,<0.69' "
            "(Pillow and NumPy remain required)")
    if not 1 <= len(model.faces) <= MAX_FAST_FACES:
        raise VisualAssetError("Source UV triangle count outside compiled renderer bound")
    if not textures and not model.solid_colors:
        raise VisualAssetError("No original TEX0 diffuse appearance to render")

    xyz = np.ascontiguousarray(model.vertices, dtype=np.float64)
    uv = np.ascontiguousarray(model.uvs, dtype=np.float64)
    faces = np.ascontiguousarray(
        [f.vertices for f in model.faces], dtype=np.int32)
    uv_faces = np.ascontiguousarray(
        [f.uvs for f in model.faces], dtype=np.int32)
    if (xyz.ndim != 2 or xyz.shape[1] != 3
            or uv.ndim != 2 or uv.shape[1] != 2
            or faces.shape != (len(model.faces), 3)
            or uv_faces.shape != (len(model.faces), 3)
            or not np.isfinite(xyz).all() or not np.isfinite(uv).all()
            or faces.min() < 0 or faces.max() >= len(xyz)
            or uv_faces.min() < 0 or uv_faces.max() >= len(uv)):
        raise VisualAssetError("Source model geometry/UV failed compiled admission")

    names = sorted({f.material for f in model.faces})
    mat_lookup = {name: i for i, name in enumerate(names)}
    mat_ids = np.asarray(
        [mat_lookup[f.material] for f in model.faces], dtype=np.int32)

    offsets = np.full(len(names), -1, dtype=np.int32)
    widths = np.zeros(len(names), dtype=np.int32)
    heights = np.zeros(len(names), dtype=np.int32)
    colors = np.zeros((len(names), 3), dtype=np.uint8)
    pixels = []
    byte_count = 0

    for name in names:
        index = mat_lookup[name]
        if name in textures:
            tex = np.asarray(textures[name], dtype=np.uint8)
            if tex.ndim != 3 or tex.shape[2] != 4 or (
                    len(tex) == 0 or len(tex[0]) == 0):
                raise VisualAssetError("Original RGBA PNG array invalid")
            tex = np.ascontiguousarray(tex)
            byte_count += tex.nbytes
            if byte_count > MAX_PACKED_RGBA_BYTES:
                raise VisualAssetError("Original texture pixels exceed fast-memory bound")
            offsets[index] = (byte_count - tex.nbytes) // 4
            heights[index], widths[index] = tex.shape[:2]
            pixels.append(tex.reshape(-1, 4))
        elif name in model.solid_colors:
            color = model.solid_colors[name]
            if len(color) != 3 or any(
                    type(c) is not int or not 0 <= c <= 255 for c in color):
                raise VisualAssetError("Source-only diffuse color invalid")
            colors[index] = color
        else:
            raise VisualAssetError("Original source face lacks verified texture or color")

    texels = (np.ascontiguousarray(np.concatenate(pixels, axis=0))
              if pixels else np.empty((0, 4), dtype=np.uint8))
    return FastVisualScene(xyz, uv, faces, uv_faces, mat_ids, texels,
                           offsets, widths, heights, colors)


def _project(scene: FastVisualScene, width: int, height: int,
             camera: VisualCamera):
    if (type(width) is not int or type(height) is not int or
            not 16 <= width <= 1280 or not 16 <= height <= 800):
        raise VisualAssetError("Fast preview size outside source renderer bounds")
    if not all(math.isfinite(v) for v in (
            *camera.position, *camera.focus, camera.yaw, camera.pitch,
            camera.scale)):
        raise VisualAssetError("Fast camera has nonfinite source-local coordinates")
    right, up, toward = camera_axes(camera.yaw, camera.pitch)
    src = scene.xyz
    delta = src - np.asarray(camera.position, dtype=np.float64)
    depth = -(delta[:, 0]*toward[0]+delta[:, 1]*toward[1]+delta[:, 2]*toward[2])
    near = max(1e-6, camera.scale*0.001)
    front = depth > near
    denom = np.maximum(depth, near)
    focal = height/(2.0*math.tan(math.radians(55.)*.5))
    screen = np.empty_like(src)
    screen[:, 0] = width*.5 + focal*(
        delta[:, 0]*right[0]+delta[:, 1]*right[1]+delta[:, 2]*right[2])/denom
    screen[:, 1] = height*.5 - focal*(
        delta[:, 0]*up[0]+delta[:, 1]*up[1]+delta[:, 2]*up[2])/denom
    screen[:, 2] = 1.0/denom
    if not np.isfinite(screen).all():
        raise VisualAssetError("Fast renderer perspective projection not finite")
    return screen, np.asarray(front, dtype=np.bool_)


def _raster_loop(screen, front, faces, face_uvs, uv, materials, texels,
                 tex_offsets, tex_widths, tex_heights, solid_colors,
                 width, height):
    """Bounded Z-buffer triangle loop; Numba compiles to native machine code."""
    image = np.empty((height, width, 3), dtype=np.uint8)
    image[:, :, 0] = 19
    image[:, :, 1] = 32
    image[:, :, 2] = 46
    zbuf = np.full((height, width), -np.inf, dtype=np.float32)
    drawn = 0

    for f in range(faces.shape[0]):
        v0, v1, v2 = faces[f, 0], faces[f, 1], faces[f, 2]
        # Like the original bounded CPU viewer, do not invent near-plane
        # clipped triangles. Skip triangles with a behind-camera vertex.
        if not (front[v0] and front[v1] and front[v2]):
            continue
        x0, y0, z0 = screen[v0, 0], screen[v0, 1], screen[v0, 2]
        x1, y1, z1 = screen[v1, 0], screen[v1, 1], screen[v1, 2]
        x2, y2, z2 = screen[v2, 0], screen[v2, 1], screen[v2, 2]
        det = (y1-y2)*(x0-x2) + (x2-x1)*(y0-y2)
        if abs(det) < 1e-8:
            continue
        left = max(0, int(math.floor(min(x0, x1, x2))))
        top = max(0, int(math.floor(min(y0, y1, y2))))
        right = min(width, int(math.ceil(max(x0, x1, x2)))+1)
        bottom = min(height, int(math.ceil(max(y0, y1, y2)))+1)
        if left >= right or top >= bottom:
            continue
        material = materials[f]
        tex_offset = tex_offsets[material]
        if tex_offset >= 0:
            t0, t1, t2 = face_uvs[f, 0], face_uvs[f, 1], face_uvs[f, 2]
            u0, v0u = uv[t0, 0], uv[t0, 1]
            u1, v1u = uv[t1, 0], uv[t1, 1]
            u2, v2u = uv[t2, 0], uv[t2, 1]
            tw, th = tex_widths[material], tex_heights[material]
        showed = False
        for y in range(top, bottom):
            py = y + .5
            for x in range(left, right):
                px = x + .5
                b0 = ((y1-y2)*(px-x2)+(x2-x1)*(py-y2))/det
                b1 = ((y2-y0)*(px-x2)+(x0-x2)*(py-y2))/det
                b2 = 1.0-b0-b1
                if b0 < -1e-6 or b1 < -1e-6 or b2 < -1e-6:
                    continue
                z = b0*z0+b1*z1+b2*z2
                if z <= zbuf[y, x]:
                    continue
                if tex_offset >= 0:
                    # The original viewer uses reciprocal-depth-correct UVs.
                    w0, w1, w2 = b0*z0, b1*z1, b2*z2
                    denominator = w0+w1+w2
                    if denominator <= 1e-30:
                        continue
                    u = (w0*u0+w1*u1+w2*u2)/denominator
                    v = (w0*v0u+w1*v1u+w2*v2u)/denominator
                    tx = int(math.floor((u-math.floor(u))*tw)) % tw
                    flipped = 1.0-v
                    ty = int(math.floor((flipped-math.floor(flipped))*th)) % th
                    texel = tex_offset+ty*tw+tx
                    alpha = int(texels[texel, 3])
                    if alpha <= 16:
                        continue
                    if alpha == 255:
                        image[y, x, 0] = texels[texel, 0]
                        image[y, x, 1] = texels[texel, 1]
                        image[y, x, 2] = texels[texel, 2]
                    else:
                        for c in range(3):
                            image[y, x, c] = np.uint8(
                                (int(texels[texel, c])*alpha +
                                 int(image[y, x, c])*(255-alpha))/255.)
                else:
                    image[y, x, 0] = solid_colors[material, 0]
                    image[y, x, 1] = solid_colors[material, 1]
                    image[y, x, 2] = solid_colors[material, 2]
                zbuf[y, x] = z
                showed = True
        if showed:
            drawn += 1
    return image, drawn


if njit is not None:
    _native_raster = njit(cache=True, nogil=True)(_raster_loop)
else:
    _native_raster = None


def render_fast(scene: FastVisualScene, width: int, height: int,
                camera: VisualCamera):
    """Return (PIL source-textured image, visible native triangle count).

    First invocation JIT-compiles once; later launches reuse Numba disk cache.
    The native kernel usually finishes fast enough not to need mid-frame
    cancellation; callers check the cancellation flag before and after.
    """
    if _native_raster is None:
        raise VisualAssetError("Numba is not installed for fast UV rendering")
    screen, front = _project(scene, width, height, camera)
    image, drawn = _native_raster(
        screen, front, scene.faces, scene.face_uvs, scene.uv,
        scene.material_ids, scene.rgba_pixels, scene.tex_offsets,
        scene.tex_widths, scene.tex_heights, scene.solid_colors,
        width, height)
    from PIL import Image
    return Image.fromarray(image, mode="RGB"), int(drawn)
