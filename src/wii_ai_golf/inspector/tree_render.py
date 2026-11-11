"""Bounded, nonphysical display-only tree silhouettes for source-qualified placements.

No native tree mesh, scale, species, alpha texture, collision volume or tree
physics is represented here. The 94 bases come from the strict private loader;
the geometric crowns/trunks are illustrative and scaled to the source span.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from collections.abc import Callable
import math

from .tree_positions import SOURCE_TREE_COUNT

Point3 = tuple[float, float, float]


@dataclass(frozen=True)
class TreeFace:
    source_index: int
    vertices: tuple[Point3, ...]
    fill: str


def _check(positions: tuple[Point3, ...]) -> None:
    if len(positions) != SOURCE_TREE_COUNT:
        raise ValueError("Tree display requires exactly 94 qualified source bases")
    if any(len(point) != 3 or any(not math.isfinite(v) or abs(v) >= 1e7 for v in point)
           for point in positions):
        raise ValueError("Invalid source tree position")


def placeholder_size(positions: tuple[Point3, ...]) -> float:
    """Illustrative scale ONLY; never return a game-derived tree dimension."""
    _check(positions)
    xs = [p[0] for p in positions]
    zs = [p[2] for p in positions]
    span = max(max(xs) - min(xs), max(zs) - min(zs), 1.0)
    return min(100_000.0, max(0.02, span * 0.018))


def fit_points(positions: tuple[Point3, ...], *, illustrations: bool) -> tuple[Point3, ...]:
    """Include ALL 94 exact bases in framing; extend bounds for fake crowns."""
    _check(positions)
    if not illustrations:
        return positions
    s = placeholder_size(positions)
    extra = []
    for x, y, z in positions:
        extra.append((x, y + 2.4*s, z))
        # All four corners matter for bounds at arbitrary camera yaw.
        extra.extend((x+dx*s, y+0.75*s, z+dz*s)
                     for dx, dz in ((-1,-1),(-1,1),(1,-1),(1,1)))
    return positions + tuple(extra)


def camera_depth(point: Point3, yaw: float, pitch: float) -> float:
    """Orthographic camera-depth heuristic paired with inspector.gui.project."""
    if not (math.isfinite(yaw) and math.isfinite(pitch)):
        raise ValueError("Nonfinite camera")
    x, y, z = point
    side = z * math.cos(yaw) - x * math.sin(yaw)
    return y * math.sin(pitch) - side * math.cos(pitch)


@lru_cache(maxsize=3)
def placeholder_faces(positions: tuple[Point3, ...]) -> tuple[TreeFace, ...]:
    """12 bounded 3D polygons/tree: four trunk sides and two 4-face crowns.

    Neither volume nor appearance is intended to approximate a hitbox.
    In particular this does NOT implement the unknown 72/22 resource groups.
    """
    s = placeholder_size(positions)
    shapes: list[TreeFace] = []
    for idx, (x, y, z) in enumerate(positions, start=1):
        trunk_r = 0.16*s
        corners = ((-trunk_r, -trunk_r), (trunk_r, -trunk_r),
                   (trunk_r, trunk_r), (-trunk_r, trunk_r))
        for side in range(4):
            a, b = corners[side], corners[(side+1) % 4]
            shapes.append(TreeFace(idx, (
                (x+a[0], y, z+a[1]), (x+b[0], y, z+b[1]),
                (x+b[0], y+1.05*s, z+b[1]), (x+a[0], y+1.05*s, z+a[1]),
            ), ("#876041", "#754f36")[side % 2]))
        for ring_height, apex_height, radius, colors in (
            (0.65, 1.75, 1.0, ("#2f7158", "#3b8266")),
            (1.25, 2.4, 0.76, ("#358367", "#459072")),
        ):
            ring = tuple((x+dx*radius*s, y+ring_height*s, z+dz*radius*s)
                         for dx, dz in ((-1,-1),(1,-1),(1,1),(-1,1)))
            tip = (x, y+apex_height*s, z)
            for side in range(4):
                shapes.append(TreeFace(idx, (
                    ring[side], ring[(side+1) % 4], tip,
                ), colors[side % 2]))
    if len(shapes) != SOURCE_TREE_COUNT * 12:
        raise AssertionError("Unbounded tree placeholder geometry")
    return tuple(shapes)


def draw_tree_layer(
    canvas: object,
    positions: tuple[Point3, ...],
    project_to_canvas: Callable[[Point3], tuple[float, float]],
    yaw: float,
    pitch: float,
    *,
    illustrations: bool,
    labels: bool,
) -> int:
    """Draw all verified bases, optionally with explicitly fake 3D trees.

    The Tk canvas uses a back-to-front approximation; there is no Z-buffer.
    This renderer never loads assets, sends network requests or accesses Dolphin.
    """
    _check(positions)
    if illustrations:
        faces = placeholder_faces(positions)
        # Deterministic painter order makes camera rotation legible, not a
        # claim of physically correct occlusion against separate terrain.
        ordered = sorted(
            faces,
            key=lambda face: sum(camera_depth(v, yaw, pitch) for v in face.vertices)
                             / len(face.vertices),
        )
        for face in ordered:
            xy = tuple(project_to_canvas(v) for v in face.vertices)
            canvas.create_polygon(
                *(n for point in xy for n in point), fill=face.fill,
                outline="#24483a" if len(face.vertices) == 3 else "#4c362b",
                width=0.5,
                tags=("tree_illustrative_nonphysical", f"tree_source_{face.source_index:03d}"),
            )
    for idx, point in enumerate(positions, start=1):
        px, py = project_to_canvas(point)
        # Exact source base is a dot even when an invented crown is displayed.
        canvas.create_oval(
            px-2.5, py-2.5, px+2.5, py+2.5,
            fill="#e9fb9c", outline="#183b23",
            tags=("tree_exact_source_base", f"tree_source_{idx:03d}"),
        )
        if labels:
            canvas.create_text(
                px+4, py+3, anchor="nw", text=f"T{idx:02d}",
                fill="#e9fb9c", tags=("tree_source_label", f"tree_source_{idx:03d}"),
            )
    return len(positions)
