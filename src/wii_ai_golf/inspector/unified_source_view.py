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
    # Manual UI-only correction, applied equally to KCL and tree base markers.
    # Units are visual model coordinates; NEVER native Wii/KCL positions.
    display_offset: tuple[float, float, float] = (0., 0., 0.)
    display_scale_multiplier: float = 1.


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
    shift = comp.display_offset
    return (ox + c*dx - sn*dz + shift[0],
            p[1] + shift[1],
            oz + sn*dx + c*dz + shift[2])


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
                           material_alignment: MaterialAlignment | None = None,
                           display_scale_multiplier: float = 1.,
                           display_offset_fraction_xz: tuple[float, float] = (0., 0.)
                           ) -> ComparisonKCL:
    """Fit two unaligned source bounding boxes for *display ONLY*.

    Not source/native scale, not aligned collision or verified active hole.
    Preserve aspect with one uniform X/Z ratio; no guessed tilt or mirroring.
    User may visually compare material classes, not infer collision coordinates.
    """
    if type(rotation_degrees) is not int or rotation_degrees not in _DISPLAY_TURNS:
        raise ValueError("KCL viewing rotation must be 0, 90, 180 or 270 degrees")
    if (not isinstance(display_offset_fraction_xz, tuple)
            or len(display_offset_fraction_xz) != 2
            or any(type(v) not in (float, int) or
                   not math.isfinite(v) or abs(v) > 1.
                   for v in display_offset_fraction_xz)
            or type(display_scale_multiplier) not in (float, int)
            or not math.isfinite(display_scale_multiplier)
            or not 0.25 <= display_scale_multiplier <= 4.):
        raise ValueError("Unbounded manual KCL comparison adjustment")
    if material_alignment is not None:
        if not isinstance(material_alignment, MaterialAlignment):
            raise ValueError("Invalid original source material registration")
        if (rotation_degrees or display_scale_multiplier != 1.
                or display_offset_fraction_xz != (0., 0.)):
            raise ValueError("Do not combine measured material registration with manual trials")
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
    scale = (min(sx, sz) * display_scale_multiplier
             if material_alignment is None else material_alignment.scale)
    if not 1e-7 <= scale <= 1e7:
        raise ValueError("Unbounded comparison transform")
    k_mid = tuple((k_min[i]+k_max[i])*.5 for i in range(3))
    v_mid = tuple((v_min[i]+v_max[i])*.5 for i in range(3))
    translation = (tuple(v_mid[i]-scale*k_mid[i] for i in range(3))
                   if material_alignment is None else material_alignment.translation)
    v_diagonal_xz = math.hypot(v_span[0], v_span[2])
    shift = (display_offset_fraction_xz[0]*v_diagonal_xz, 0.,
             display_offset_fraction_xz[1]*v_diagonal_xz)
    transform_info = ComparisonKCL(
        terrain.sha256, (), (), (), scale, translation, (sx, sz), (),
        rotation_degrees, v_mid, material_alignment, shift,
        display_scale_multiplier)
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
        rotation_degrees, v_mid, material_alignment, shift,
        display_scale_multiplier)


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
        f"· manual scale {comp.display_scale_multiplier:.3f}× "
        f"shift X/Z {comp.display_offset[0]:+.3g}/{comp.display_offset[2]:+.3g} visual units "
        f"(X/Z fit-ratio disagreement {ratio:.2f}×) · "
        "UNVERIFIED native/world alignment")


def draw_comparison(image, comp: ComparisonKCL | None, camera: "VisualCamera",
                    *, mode: str = "Both"):
    """Draw KCL polygon / wire on SAME PhotoImage after original UV raster.

    Mode: Textures (no KCL), Collision (surface colors), Both (visual
    PNG image plus cyan x-ray KCL wire edges), Overlay (transparent source
    material KCL over original PNG), Split (same camera textures left,
    KCL-colored faces right). These are all display-only hypotheses.
    """
    if mode not in {"Textures", "Collision", "Both", "Overlay", "Split"}:
        raise ValueError("Unknown unified source view mode")
    if comp is None or mode == "Textures":
        return image
    import numpy as np
    from PIL import Image, ImageDraw, ImageColor

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
    if mode in {"Collision", "Overlay", "Split"}:
        # Per-vertex RGB is original OGWS-class *display color*, never a
        # texture/collision semantic match. No DAE/KCL shared depth claim.
        if mode == "Overlay":
            tinted = Image.new("RGBA", image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(tinted, "RGBA")
        elif mode == "Split":
            panel = Image.new("RGB", image.size, (19, 32, 46))
            draw = ImageDraw.Draw(panel)
        else:
            draw = ImageDraw.Draw(image)
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
            color = comp.colors[index]
            if mode == "Overlay":
                draw.polygon(points, fill=(*ImageColor.getrgb(color), 90))
            else:
                draw.polygon(points, fill=color)
        if mode == "Overlay":
            return Image.alpha_composite(image.convert("RGBA"), tinted).convert("RGB")
        if mode == "Split":
            halfway = width // 2
            image.paste(panel.crop((halfway, 0, width, height)),
                        (halfway, 0))
            ImageDraw.Draw(image).line(
                (halfway, 0, halfway, height), fill="#f7e88a", width=2)
            return image
        return image

    draw = ImageDraw.Draw(image)
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
