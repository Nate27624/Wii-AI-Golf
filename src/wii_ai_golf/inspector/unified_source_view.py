"""One shared source visual/KCL viewer, with explicitly UNVERIFIED fit.

The exact SHA-bound KCL source OBJ and Wii source UV/PNG art are independent.
No common native world transform has been proved. A display-only uniform
bounding-box comparison can make the two visible in ONE camera viewport;
NEVER treat a display fit as a physics, ball/tee/pin or tree calibration.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING

from .scene_camera import camera_axes, playable_source_vertices
from .terrain import surface_style

if TYPE_CHECKING:
    from .scene_camera import VisualCamera
    from .terrain import TerrainMesh
    from .visual_model import PrivateVisualModel


@dataclass(frozen=True)
class ComparisonKCL:
    """Original collision indices and display-only, bounded source transform."""
    source_sha256: str
    vertices: tuple[tuple[float, float, float], ...]
    faces: tuple[tuple[int, int, int], ...]
    colors: tuple[str, ...]
    source_scale: float
    source_translation: tuple[float, float, float]
    span_ratio_xz: tuple[float, float]
    edge_faces: tuple[tuple[int, int], ...]


def bounds(points):
    if not points:
        raise ValueError("Cannot align empty original source geometry")
    mins = tuple(min(p[i] for p in points) for i in range(3))
    maxs = tuple(max(p[i] for p in points) for i in range(3))
    if not all(math.isfinite(x) for x in (*mins, *maxs)):
        raise ValueError("Source bounds not finite")
    return mins, maxs


def prepare_comparison_kcl(terrain: "TerrainMesh",
                           visual: "PrivateVisualModel") -> ComparisonKCL:
    """Fit two unaligned source bounding boxes for *display ONLY*.

    Not source/native scale, not aligned collision or verified active hole.
    Preserve aspect with one uniform X/Z ratio; no guessed tilt or mirroring.
    User may visually compare material classes, not infer collision coordinates.
    """
    if not 1 <= len(terrain.faces) <= 30_000:
        raise ValueError("Source KCL face count outside overlay bounds")
    k_min, k_max = bounds(terrain.vertices)
    v_min, v_max = bounds(playable_source_vertices(visual))
    k_span = tuple(k_max[i] - k_min[i] for i in range(3))
    v_span = tuple(v_max[i] - v_min[i] for i in range(3))
    if not all(1e-7 < k_span[i] < 1e7 and 1e-7 < v_span[i] < 1e7
               for i in (0, 2)):
        raise ValueError("Horizontal geometry extent invalid; cannot fit collision overlay")
    sx, sz = v_span[0]/k_span[0], v_span[2]/k_span[2]
    scale = min(sx, sz)
    if not 1e-7 <= scale <= 1e7:
        raise ValueError("Unbounded comparison transform")
    k_mid = tuple((k_min[i]+k_max[i])*.5 for i in range(3))
    v_mid = tuple((v_min[i]+v_max[i])*.5 for i in range(3))
    translation = tuple(v_mid[i]-scale*k_mid[i] for i in range(3))
    transformed = tuple(tuple(scale*p[i]+translation[i] for i in range(3))
                        for p in terrain.vertices)

    source_colors = tuple(
        surface_style(terrain.face_materials[i]
                      if terrain.face_materials else None)[1]
        for i in range(len(terrain.faces)))
    unique_edges = set()
    for a, b, c in terrain.faces:
        for v0, v1 in ((a, b), (b, c), (c, a)):
            unique_edges.add((min(v0, v1), max(v0, v1)))
    return ComparisonKCL(
        terrain.sha256, transformed, terrain.faces, source_colors,
        scale, translation, (sx, sz), tuple(sorted(unique_edges)))


def overlay_summary(comp: ComparisonKCL) -> str:
    sx, sz = comp.span_ratio_xz
    ratio = max(sx, sz)/min(sx, sz)
    return (
        f"KCL {len(comp.faces):,} source faces · x-ray display-only "
        f"uniform bounds fit {comp.source_scale:.5g}× "
        f"(X/Z fit-ratio disagreement {ratio:.2f}×) · "
        "NOT verified native/world alignment")


def draw_comparison(image, comp: ComparisonKCL | None, camera: "VisualCamera",
                    *, mode: str = "Both"):
    """Draw KCL polygon / wire on SAME PhotoImage after original UV raster.

    Mode: Textures (no KCL), Collision (surface colors), Both (visual
    PNG image plus cyan x-ray KCL wire edges). All are explicitly unverified
    relative registration; no changes to source assets.
    """
    if mode not in {"Textures", "Collision", "Both"}:
        raise ValueError("Unknown unified source view mode")
    if comp is None or mode == "Textures":
        return image
    import numpy as np
    from PIL import Image, ImageDraw

    if mode == "Collision":
        image = Image.new("RGB", image.size, (19, 32, 46))
    width, height = image.size
    coords = np.asarray(comp.vertices, dtype=np.float64)
    right, up, toward_viewer = camera_axes(camera.yaw, camera.pitch)
    delta = coords - np.asarray(camera.position, dtype=np.float64)
    facing = -(delta @ np.asarray(toward_viewer, dtype=np.float64))
    near = max(1e-6, camera.scale*0.001)
    front = facing > near
    denom = np.maximum(facing, near)
    focal = height / (2.*math.tan(math.radians(55.)*.5))
    xy = np.empty((len(coords), 2), dtype=np.float64)
    xy[:, 0] = width*.5+focal*(delta @ np.asarray(right))/denom
    xy[:, 1] = height*.5-focal*(delta @ np.asarray(up))/denom
    draw = ImageDraw.Draw(image)
    if mode == "Collision":
        # Unverified source-category-colored candidate KCL polygons:
        # painter sorting is for inspectability, NOT game native physics.
        ordered = sorted(range(len(comp.faces)),
                         key=lambda i: float(sum(facing[v] for v in comp.faces[i])),
                         reverse=True)
        for index in ordered:
            tri = comp.faces[index]
            if not all(front[v] for v in tri):
                continue
            points = [tuple(xy[v]) for v in tri]
            if any(abs(x) > 1e6 for p in points for x in p):
                continue
            draw.polygon(points, fill=comp.colors[index])
        return image

    # Both: source-textured DAE plus a thin cyan X-RAY KCL line overlay.
    # X-ray avoids a false claim that KCL and original TEV share a zbuffer.
    for v0, v1 in comp.edge_faces:
        if not (front[v0] and front[v1]):
            continue
        x0, y0 = xy[v0]
        x1, y1 = xy[v1]
        if (min(x0, x1) > width or max(x0, x1) < 0 or
                min(y0, y1) > height or max(y0, y1) < 0):
            continue
        if max(abs(x0), abs(y0), abs(x1), abs(y1)) > 1e6:
            continue
        draw.line((float(x0), float(y0), float(x1), float(y1)),
                  fill=(0, 215, 255), width=1)
    return image
