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
from .material_alignment import MaterialAlignment

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
    # Explicit viewing correction only; never original KCL/world orientation.
    display_rotation_degrees: int = 0
    display_center: tuple[float, float, float] = (0.0, 0.0, 0.0)
    source_material_fit: MaterialAlignment | None = None


# Exact quarter-turns avoid floating-point trig drift for repeatable overlay.
_DISPLAY_TURNS = {
    0: (1., 0.), 90: (0., 1.),
    180: (-1., 0.), 270: (0., -1.),
}


def source_to_visual_display(point: tuple[float, float, float],
                             comp: ComparisonKCL) -> tuple[float, float, float]:
    """Apply ONE display-only KCL->visual transform to source faces AND trees.

    Equivalent to scaling/centering the original collision frame, then
    rotating about the visual bounds center around +Y. Original source
    points, tree JSON, KCL OBJ, and textured DAE bytes are never edited.
    """
    if (len(point) != 3 or not all(math.isfinite(x) and abs(x) < 1e7 for x in point)
            or not all(math.isfinite(x) for x in comp.display_center)):
        raise ValueError("Nonfinite/out-of-bounds source comparison position")
    try:
        c, sn = _DISPLAY_TURNS[comp.display_rotation_degrees]
    except (KeyError, TypeError):
        raise ValueError("Unsupported comparison orientation") from None
    if comp.source_material_fit is not None:
        # Independently measured material-landmark similarity: use the
        # exact SAME fit for all KCL faces and all 94 source tree bases.
        # Manual yaw trials must not overwrite a measured transform.
        return comp.source_material_fit.apply(point)
    p = tuple(comp.source_scale * point[i] + comp.source_translation[i]
              for i in range(3))
    ox, _, oz = comp.display_center
    dx, dz = p[0] - ox, p[2] - oz
    return (ox + c*dx - sn*dz, p[1], oz + sn*dx + c*dz)


def bounds(points):
    if not points:
        raise ValueError("Cannot align empty original source geometry")
    mins = tuple(min(p[i] for p in points) for i in range(3))
    maxs = tuple(max(p[i] for p in points) for i in range(3))
    if not all(math.isfinite(x) for x in (*mins, *maxs)):
        raise ValueError("Source bounds not finite")
    return mins, maxs


def prepare_comparison_kcl(terrain: "TerrainMesh",
                           visual: "PrivateVisualModel",
                           *, rotation_degrees: int = 0,
                           material_alignment: MaterialAlignment | None = None
                           ) -> ComparisonKCL:
    """Fit two unaligned source bounding boxes for *display ONLY*.

    Not source/native scale, not aligned collision or verified active hole.
    Preserve aspect with one uniform X/Z ratio; no guessed tilt or mirroring.
    User may visually compare material classes, not infer collision coordinates.
    """
    if type(rotation_degrees) is not int or rotation_degrees not in _DISPLAY_TURNS:
        raise ValueError("KCL viewing rotation must be 0, 90, 180 or 270 degrees")
    if material_alignment is not None:
        if not isinstance(material_alignment, MaterialAlignment):
            raise ValueError("Invalid original source material registration")
        if rotation_degrees:
            raise ValueError("Do not combine measured material registration with arbitrary yaw")
    if not 1 <= len(terrain.faces) <= 30_000:
        raise ValueError("Source KCL face count outside overlay bounds")
    k_min, k_max = bounds(terrain.vertices)
    v_min, v_max = bounds(playable_source_vertices(visual))
    k_span = tuple(k_max[i] - k_min[i] for i in range(3))
    v_span = tuple(v_max[i] - v_min[i] for i in range(3))
    if not all(1e-7 < k_span[i] < 1e7 and 1e-7 < v_span[i] < 1e7
               for i in (0, 2)):
        raise ValueError("Horizontal geometry extent invalid; cannot fit collision overlay")
    # Quarter-turns swap displayed horizontal bounds. Fit by the ACTUAL
    # rotated extents, rather than retaining 0-degree spans for 90/270.
    rotated_x = k_span[2] if rotation_degrees in (90, 270) else k_span[0]
    rotated_z = k_span[0] if rotation_degrees in (90, 270) else k_span[2]
    sx, sz = v_span[0]/rotated_x, v_span[2]/rotated_z
    scale = min(sx, sz) if material_alignment is None else material_alignment.scale
    if not 1e-7 <= scale <= 1e7:
        raise ValueError("Unbounded comparison transform")
    k_mid = tuple((k_min[i]+k_max[i])*.5 for i in range(3))
    v_mid = tuple((v_min[i]+v_max[i])*.5 for i in range(3))
    translation = (tuple(v_mid[i]-scale*k_mid[i] for i in range(3))
                   if material_alignment is None else material_alignment.translation)
    transform_info = ComparisonKCL(
        terrain.sha256, (), (), (), scale, translation, (sx, sz), (),
        rotation_degrees, v_mid, material_alignment)
    transformed = tuple(source_to_visual_display(p, transform_info)
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
        scale, translation, (sx, sz), tuple(sorted(unique_edges)),
        rotation_degrees, v_mid, material_alignment)


def prepare_source_only_kcl(terrain: "TerrainMesh") -> ComparisonKCL:
    """Draw ORIGINAL source OBJ XYZ, WITHOUT fitting to any visual DAE.

    Unlike the x-ray overlay, this Collision view is always available once
    the strict private source KCL has loaded. Source tree bases use the same
    identity map. No inferred scale, rotation, or Wii collision semantics.
    """
    if not 1 <= len(terrain.faces) <= 30_000:
        raise ValueError("Source KCL faces outside safe viewing bound")
    points = tuple(terrain.vertices)
    if not points or any(
            len(p) != 3 or not all(math.isfinite(v) and abs(v) < 1e7 for v in p)
            for p in points):
        raise ValueError("Original KCL positions invalid for source-only mode")
    source_colors = tuple(
        surface_style(terrain.face_materials[i]
                      if terrain.face_materials else None)[1]
        for i in range(len(terrain.faces)))
    edges = set()
    for tri in terrain.faces:
        if len(tri) != 3 or any(type(v) is not int or not 0 <= v < len(points)
                                for v in tri):
            raise ValueError("Invalid original KCL face indices")
        for a, b in ((tri[0],tri[1]),(tri[1],tri[2]),(tri[2],tri[0])):
            edges.add((min(a,b),max(a,b)))
    return ComparisonKCL(
        terrain.sha256, points, terrain.faces, source_colors,
        1.0, (0.,0.,0.), (1.,1.), tuple(sorted(edges)),
        0, (0.,0.,0.))


def overlay_summary(comp: ComparisonKCL) -> str:
    if comp.source_material_fit is not None:
        fit = comp.source_material_fit
        return (
            f"KCL {len(comp.faces):,} source faces · MATERIAL-LANDMARK "
            f"display-only uniform scale {fit.scale:.5g}× · "
            f"source +Y yaw {fit.yaw_degrees:.1f}° · "
            f"independent {fit.holdout_name} residual "
            f"{fit.holdout_error_fraction:.1%} of green/fairway span · "
            f"green footprint ratio {fit.green_area_ratio:.2f} · "
            "native/world alignment UNVERIFIED")
    sx, sz = comp.span_ratio_xz
    ratio = max(sx, sz)/min(sx, sz)
    return (
        f"KCL {len(comp.faces):,} source faces · x-ray display-only "
        f"uniform bounds fit {comp.source_scale:.5g}× "
        f"+Y display yaw {comp.display_rotation_degrees}° (operator hypothesis) "
        f"(X/Z fit-ratio disagreement {ratio:.2f}×) · "
        "UNVERIFIED native/world alignment")


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


def draw_tree_comparison(image, comp: ComparisonKCL | None,
                         camera: "VisualCamera",
                         source_positions: tuple[tuple[float, float, float], ...],
                         *, illustrations: bool = True, labels: bool = False):
    """Render exact tree bases in unified KCL/UV display-only camera.

    No source tree-to-DAE/world transform has been proven. Reuse the same
    *unverified bounding-box comparison* as KCL; this is an X-ray display,
    NOT native tree art, source physical scale, or collision depth.
    """
    if comp is None or not source_positions:
        return image
    from .tree_render import _check, placeholder_faces
    from PIL import ImageDraw

    points = tuple(source_positions)
    _check(points)
    w, h = image.size
    right, up, toward = camera_axes(camera.yaw, camera.pitch)
    focal = h / (2. * math.tan(math.radians(55.) * .5))
    near = max(1e-6, camera.scale * 0.001)
    cam = camera.position

    def project_source(point):
        transformed = source_to_visual_display(point, comp)
        delta = tuple(transformed[i] - cam[i] for i in range(3))
        depth = -sum(delta[i] * toward[i] for i in range(3))
        if depth <= near:
            return None
        x = w*.5 + focal * sum(delta[i] * right[i] for i in range(3)) / depth
        y = h*.5 - focal * sum(delta[i] * up[i] for i in range(3)) / depth
        if any(not math.isfinite(v) or abs(v) >= 1e6 for v in (x, y, depth)):
            return None
        return (x, y, depth)

    draw = ImageDraw.Draw(image)
    if illustrations:
        painter = []
        for face in placeholder_faces(points):
            projected = tuple(project_source(v) for v in face.vertices)
            if any(v is None for v in projected):
                continue
            painter.append((
                sum(v[2] for v in projected) / len(projected),
                tuple((v[0], v[1]) for v in projected), face.fill,
            ))
        # Deliberate painter order: never claim original UV/KCL z-buffer.
        painter.sort(key=lambda item: item[0], reverse=True)
        for _, vertices, color in painter:
            draw.polygon(vertices, fill=color)

    for index, point in enumerate(points, 1):
        p = project_source(point)
        if p is None:
            continue
        x, y, _ = p
        if -6 <= x <= w + 6 and -6 <= y <= h + 6:
            draw.ellipse((x - 3, y - 3, x + 3, y + 3),
                         fill="#e9fb9c", outline="#183b23")
            if labels:
                draw.text((x + 5, y + 3), f"T{index:02d}", fill="#e9fb9c")
    return image
