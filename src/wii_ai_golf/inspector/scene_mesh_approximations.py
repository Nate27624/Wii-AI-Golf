"""Bounded, source-anchored 3D presentation meshes in one inspector camera.

Tree trunks and two conical crown tiers, golfer limbs/torso/head/club,
flag pole/cloth and ball are WORLD-SPACE triangles/quads, NOT pixel sprites.
Their dimensions, colors and golfer offset are illustrative only. Source
positions, tee/pin/ball ownership and authored textures stay untouched.
Polygons are painter-sorted against one another but NOT depth-tested
against the source DAE's separate UV renderer. Never use for game physics.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math
from typing import TYPE_CHECKING

from .tree_positions import SOURCE_TREE_COUNT
from .tree_render import placeholder_size, _check as check_tree_bases
from .scene_camera import camera_axes
from .unified_source_view import source_to_visual_display

if TYPE_CHECKING:
    from .scene_camera import VisualCamera
    from .unified_source_view import ComparisonKCL
    from .source_actor_overlay import SourceActorSnapshot

Point = tuple[float, float, float]
MAX_SCENE_FACES = 5000


@dataclass(frozen=True)
class ApproxFace:
    kind: str
    vertices: tuple[Point, ...]
    fill: str


def _add(a: Point, b: Point) -> Point:
    return tuple(a[i] + b[i] for i in range(3))


def _sub(a: Point, b: Point) -> Point:
    return tuple(a[i] - b[i] for i in range(3))


def _mul(a: Point, f: float) -> Point:
    return tuple(v*f for v in a)


def _cross(a: Point, b: Point) -> Point:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def _unit(v: Point) -> Point:
    length = math.sqrt(sum(x*x for x in v))
    if not math.isfinite(length) or length < 1e-10:
        raise ValueError("Invalid 3D scene mesh axis")
    return _mul(v, 1./length)


def _up(p: Point, y: float) -> Point:
    return (p[0], p[1]+y, p[2])


def _cylinder(kind: str, base: Point, tip: Point, radius: float,
              colors: tuple[str, str], sides: int = 8) -> tuple[ApproxFace, ...]:
    axis = _unit(_sub(tip, base))
    u = _unit(_cross(axis, (1., 0., 0.) if abs(axis[0]) < .8
                     else (0., 0., 1.)))
    v = _cross(axis, u)
    ring = tuple(_add(_mul(u, math.cos(t*math.tau/sides)*radius),
                      _mul(v, math.sin(t*math.tau/sides)*radius))
                 for t in range(sides))
    return tuple(
        ApproxFace(kind, (
            _add(base, ring[i]), _add(base, ring[(i+1)%sides]),
            _add(tip, ring[(i+1)%sides]), _add(tip, ring[i])),
            colors[i%2])
        for i in range(sides))


def _sphere(kind: str, center: Point, radius: float,
            colors: tuple[str, str], sides: int = 8,
            bands: int = 5) -> tuple[ApproxFace, ...]:
    # Each face has actual world-space vertices; radial size changes
    # naturally under the same camera projection as trees and terrain.
    rings = []
    for j in range(bands+1):
        phi = -math.pi/2 + math.pi*j/bands
        rings.append(tuple((
            center[0] + radius*math.cos(phi)*math.cos(i*math.tau/sides),
            center[1] + radius*math.sin(phi),
            center[2] + radius*math.cos(phi)*math.sin(i*math.tau/sides))
            for i in range(sides)))
    faces = []
    for j in range(bands):
        for i in range(sides):
            nxt = (i+1)%sides
            if j == 0:
                points = (rings[j][i], rings[j+1][i], rings[j+1][nxt])
            elif j == bands-1:
                points = (rings[j][i], rings[j][nxt], rings[j+1][i])
            else:
                points = (rings[j][i], rings[j][nxt],
                          rings[j+1][nxt], rings[j+1][i])
            faces.append(ApproxFace(kind, points, colors[(i+j)%2]))
    return tuple(faces)


def _cone(kind: str, base: Point, tip: Point, radius: float,
          colors: tuple[str, str], sides: int = 8) -> tuple[ApproxFace, ...]:
    ring = tuple((base[0]+radius*math.cos(t*math.tau/sides), base[1],
                  base[2]+radius*math.sin(t*math.tau/sides))
                 for t in range(sides))
    return tuple(ApproxFace(kind, (ring[i],ring[(i+1)%sides],tip),
                            colors[i%2]) for i in range(sides))


@lru_cache(maxsize=2)
def tree_mesh_faces(points: tuple[Point, ...]) -> tuple[ApproxFace, ...]:
    """94 source-anchored, low-poly 3D trees; 24 faces/tree, cached."""
    check_tree_bases(points)
    s = placeholder_size(points)
    result = []
    for pos in points:
        result.extend(_cylinder("tree", pos, _up(pos, s*1.23),
                                s*.13, ("#835c3c", "#66452e")))
        result.extend(_cone("tree", _up(pos, s*.62),
                            _up(pos, s*1.78), s*.84,
                            ("#26674e", "#3b8664")))
        result.extend(_cone("tree", _up(pos, s*1.15),
                            _up(pos, s*2.42), s*.65,
                            ("#317b59", "#46946c")))
    if len(result) != SOURCE_TREE_COUNT*24:
        raise AssertionError("Unexpected scene tree geometry size")
    return tuple(result)


def actor_mesh_size(comp: "ComparisonKCL") -> float:
    """Human-sized illustrative model relative to original source course span."""
    if not comp.vertices or not math.isfinite(comp.source_scale):
        raise ValueError("Source collision display fit unavailable")
    span = max(
        max(v[0] for v in comp.vertices)-min(v[0] for v in comp.vertices),
        max(v[2] for v in comp.vertices)-min(v[2] for v in comp.vertices))
    source_span = span / max(abs(comp.source_scale), 1e-10)
    return min(1e4, max(.02, source_span*.035))


def actor_mesh_faces(comp: "ComparisonKCL", snapshot: "SourceActorSnapshot | None",
                     *, show_flag: bool = True, show_ball: bool = True,
                     show_player: bool = True) -> tuple[ApproxFace, ...]:
    """Generate native-source-anchored, fake 3D geometry per accepted packet."""
    if snapshot is None or not (snapshot.source_qualified or
                                snapshot.illustrative_only):
        return ()
    if not all(type(flag) is bool
               for flag in (show_flag,show_ball,show_player)):
        raise ValueError("Actor mesh toggles must be Boolean")
    h = actor_mesh_size(comp)
    faces: list[ApproxFace] = []
    flag = snapshot.flag
    tee = snapshot.tee_proxy
    # Direction only affects illustrative object orientation/tee-side offset.
    # NEVER count it as a measured player position or aim direction.
    toward = (0., 0., 1.)
    if flag is not None and tee is not None:
        dx, dz = flag[0]-tee[0], flag[2]-tee[2]
        span = math.hypot(dx,dz)
        if span > 1e-8:
            toward = (dx/span, 0., dz/span)
    side = (toward[2], 0., -toward[0])

    if show_flag and flag is not None:
        top = _up(flag, h*1.36)
        faces.extend(_cylinder(
            "flag", flag, top, h*.014, ("#f1f5fa", "#c9d6e2")))
        rim_center = _up(flag, h*.018)
        for i in range(8):
            a = i*math.tau/8.
            b = (i+1)*math.tau/8.
            faces.append(ApproxFace("flag", (
                rim_center,
                _add(rim_center, (math.cos(a)*h*.10, 0.,
                                  math.sin(a)*h*.10)),
                _add(rim_center, (math.cos(b)*h*.10, 0.,
                                  math.sin(b)*h*.10))),
                "#eee9d5" if i%2 else "#bfcbd5"))
        top_right = _add(top, _mul(side, h*.48))
        bottom_right = _up(top_right, -h*.24)
        faces.append(ApproxFace(
            "flag", (top, top_right, bottom_right,
                     _up(top, -h*.31)), "#e84943"))
        faces.append(ApproxFace(
            "flag", (top, _up(top,-h*.31), bottom_right, top_right),
            "#cf3b38"))

    if show_ball and snapshot.ball is not None:
        # Source ball+0x30 is the actual selected ball position candidate.
        # On geometry-derived illustrative-only positions the center is
        # raised by a visual radius to rest above the course polygon.
        pos = snapshot.ball
        if snapshot.illustrative_only:
            pos = _up(pos, h*.11)
        faces.extend(_sphere(
            "ball", pos, h*.11, ("#ffffff", "#d9e4ee"),
            sides=10, bands=5))

    if show_player and tee is not None:
        # A golfer is offset from the tee point solely to keep the rendered
        # player and ball distinct. This offset is NOT game-world player XYZ.
        foot = _add(tee, _mul(side, h*.30))
        if snapshot.illustrative_only:
            foot = _up(foot, h*.01)
        pelvis = _up(foot, h*.45)
        shoulder = _up(foot, h*.72)
        head = _up(foot, h*.91)
        faces.extend(_cylinder(
            "player", pelvis, shoulder, h*.17,
            ("#4b92d6", "#3178bf")))
        faces.extend(_sphere(
            "player", head, h*.115, ("#efd2b6", "#d9a17f"),
            sides=8, bands=5))
        for sign in (-1., 1.):
            leg_base = _add(foot, _mul(side, sign*h*.105))
            leg_top = _add(pelvis, _mul(side, sign*h*.07))
            faces.extend(_cylinder(
                "player", leg_base, leg_top, h*.073,
                ("#313b53", "#46516c"), sides=6))
            arm_top = _add(shoulder, _mul(side, sign*h*.16))
            hand = _add(_up(foot, h*.40), _mul(side, sign*h*.28))
            faces.extend(_cylinder(
                "player", hand, arm_top, h*.058,
                ("#d6a889", "#e6c1a6"), sides=6))
        hands = _add(_up(foot,h*.40), _mul(side,h*.28))
        club_head = _add(_up(foot,h*.04), _mul(toward,h*.28))
        faces.extend(_cylinder(
            "player", hands, club_head, h*.015,
            ("#e0e3e9", "#899db0"), sides=6))
    if len(faces) > MAX_SCENE_FACES:
        raise ValueError("Unbounded actor scene geometry")
    return tuple(faces)


def draw_3d_approximations(image, comp: "ComparisonKCL | None",
                           camera: "VisualCamera", *,
                           snapshot: "SourceActorSnapshot | None" = None,
                           source_tree_positions: tuple[Point, ...] = (),
                           show_trees: bool = True,
                           show_flag: bool = True,
                           show_ball: bool = True,
                           show_player: bool = True,
                           labels: bool = True):
    """Project 3D surfaces at varying world depths with one common camera.

    Uses painter order amongst scene meshes; intentionally never claims
    a true terrain/texture z-buffer, occlusion, or original character art.
    """
    if comp is None:
        return image
    if any(type(x) is not bool for x in
           (show_trees, show_flag, show_ball, show_player, labels)):
        raise ValueError("Scene toggles must be Boolean")
    from PIL import ImageDraw
    from .source_actor_overlay import SourceActorSnapshot
    if snapshot is not None and not isinstance(snapshot, SourceActorSnapshot):
        raise ValueError("Invalid actor snapshot")
    # Hidden trees are not examined/projected; source bases stay untouched.
    source_tree_positions = tuple(source_tree_positions)
    faces = []
    if show_trees and source_tree_positions:
        faces.extend(tree_mesh_faces(source_tree_positions))
    if snapshot is not None:
        faces.extend(actor_mesh_faces(
            comp, snapshot, show_flag=show_flag,
            show_ball=show_ball, show_player=show_player))
    if len(faces) > MAX_SCENE_FACES:
        raise ValueError("Unbounded approximated scene face count")
    if not faces:
        return image

    width, height = image.size
    right, up, toward = camera_axes(camera.yaw, camera.pitch)
    focal = height/(2.*math.tan(math.radians(55.)/2.))
    near = max(1e-6, camera.scale*.001)
    eye = camera.position
    projection_cache = {}

    def project(point: Point):
        item = projection_cache.get(point)
        if item is not None:
            return item
        mapped = source_to_visual_display(point, comp)
        delta = tuple(mapped[i]-eye[i] for i in range(3))
        depth = -sum(delta[i]*toward[i] for i in range(3))
        if not math.isfinite(depth) or depth <= near:
            return None
        px = width*.5+focal*sum(delta[i]*right[i] for i in range(3))/depth
        py = height*.5-focal*sum(delta[i]*up[i] for i in range(3))/depth
        if not math.isfinite(px) or not math.isfinite(py) or max(abs(px),abs(py))>1e6:
            return None
        item = (px,py,depth)
        projection_cache[point] = item
        return item

    projected = []
    for face in faces:
        pts = [project(vertex) for vertex in face.vertices]
        if any(point is None for point in pts):
            continue
        xy = tuple((v[0],v[1]) for v in pts)
        if (max(x for x,_ in xy)<0 or min(x for x,_ in xy)>width or
            max(y for _,y in xy)<0 or min(y for _,y in xy)>height):
            continue
        projected.append((sum(v[2] for v in pts)/len(pts),
                          xy, face.fill))
    projected.sort(key=lambda item:item[0], reverse=True)
    draw = ImageDraw.Draw(image)
    for _, polygon, fill in projected:
        draw.polygon(polygon, fill=fill)

    if labels:
        label_positions = []
        if snapshot is not None and (snapshot.source_qualified or
                                     snapshot.illustrative_only):
            inferred = snapshot.illustrative_only
            for show, pos, label, tint in (
                (show_flag, snapshot.flag,
                 "FLAG (approx green)" if inferred else "FLAG (source pin)",
                 "#f9eeee"),
                (show_ball, snapshot.ball,
                 "BALL (approx tee)" if inferred else "BALL (selected)",
                 "#ffffff"),
                (show_player, snapshot.tee_proxy,
                 "PLAYER (approx tee)" if inferred else "PLAYER (tee proxy)",
                 "#f1ce7b")):
                if show and pos is not None:
                    label_positions.append((pos,label,tint))
        if show_trees and source_tree_positions:
            # One short source-identity label for the whole tree set:
            # don't spam 94 labels on every navigation frame.
            label_positions.append((
                source_tree_positions[0], "TREES (94 illustrative 3D)", "#ccedb0"))
        for position, label, tint in label_positions:
            p = project(position)
            if p is not None and 0 <= p[0] < width and 0 <= p[1] < height:
                draw.text((p[0]+7,p[1]+7), label, fill=tint,
                          stroke_width=2, stroke_fill="#152e3b")
    return image
