"""Read-only, per-sample flag/ball plus explicitly illustrative tee proxy.

All original positions remain in the PRIVATE qualified replay/live sample.
Only an accepted same-packet sample is shown. No inferred player RAM pointer,
native player model, physical marker height or verified world transform.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING

from .replay import BALL

if TYPE_CHECKING:
    from .replay import Sample

PIN = "pin_candidate"
TEE = "tee_start_candidate"


@dataclass(frozen=True)
class SourceActorSnapshot:
    """Positions from one source-qualified sample; no carry-forward."""
    ball: tuple[float, float, float] | None = None
    flag: tuple[float, float, float] | None = None
    tee_proxy: tuple[float, float, float] | None = None
    source_qualified: bool = False
    illustrative_only: bool = False


def from_sample(sample: "Sample | None") -> SourceActorSnapshot:
    if (sample is None or not sample.source_qualified
            or not sample.source_digest):
        return SourceActorSnapshot()
    # sample.vec decodes only finite three-component f32. Never cache flag,
    # tee or ball across missing packets or changed source identities.
    return SourceActorSnapshot(
        ball=sample.vec(BALL),
        flag=sample.vec(PIN),
        tee_proxy=sample.vec(TEE),
        source_qualified=True,
    )


def illustrative_from_terrain(terrain) -> SourceActorSnapshot:
    """Clearly unverified placements for a source-only visual preview.

    Green area centroid indicates an approximate flag. A far-end fairway
    face indicates only a plausible tee-side silhouette and initial ball.
    Not source RAM positions, not a reconstruction of game actor placements.
    """
    if (terrain is None or not terrain.face_materials
            or len(terrain.face_materials) != len(terrain.faces)):
        return SourceActorSnapshot()
    green = []
    fairway = []
    for face, attr in zip(terrain.faces, terrain.face_materials):
        if attr not in (0x0006, 0x0001):
            continue
        a, b, c = (terrain.vertices[i] for i in face)
        twice = abs((b[0]-a[0])*(c[2]-a[2])
                    -(b[2]-a[2])*(c[0]-a[0]))
        if not math.isfinite(twice) or twice <= 1e-8:
            continue
        point = tuple((a[i]+b[i]+c[i])/3. for i in range(3))
        if attr == 0x0006:
            green.append((twice, point))
        else:
            fairway.append((twice, point))
    if not green or not fairway:
        return SourceActorSnapshot()
    total = sum(w for w, _ in green)
    if total <= 0.:
        return SourceActorSnapshot()
    flag = tuple(sum(w*p[i] for w,p in green)/total for i in range(3))
    # Choose a bounded far-end fairway area centroid, not a random vertex.
    # No physical tee is proven by this purely visual method.
    _, tee = max(
        fairway,
        key=lambda item: (
            (item[1][0]-flag[0])**2+(item[1][2]-flag[2])**2,
            item[0]))
    return SourceActorSnapshot(
        ball=tee, flag=flag, tee_proxy=tee, illustrative_only=True)


def draw_source_actors(image, comp, camera, snapshot: SourceActorSnapshot | None,
                       *, show_flag: bool = True, show_ball: bool = True,
                       show_player: bool = True, labels: bool = True):
    """Draw illustrated markers in the common collision/visual camera.

    Flag pole and golfer are 2D presentation symbols. The golfer is placed
    on a TEE candidate, not the original player's verified XYZ. Drawn on top
    of textures like an X-ray; not depth-tested game geometry.
    """
    if (comp is None or snapshot is None
            or not (snapshot.source_qualified or snapshot.illustrative_only)):
        return image
    if (not isinstance(snapshot, SourceActorSnapshot)
            or any(type(v) is not bool for v in
                   (show_flag, show_ball, show_player, labels))):
        raise ValueError("Invalid source actor presentation")
    from PIL import ImageDraw
    from .scene_camera import camera_axes
    from .unified_source_view import source_to_visual_display

    width, height = image.size
    right, up, toward = camera_axes(camera.yaw, camera.pitch)
    focal = height / (2. * math.tan(math.radians(55.) / 2.))
    near = max(1e-6, camera.scale * 0.001)

    def project(point):
        if point is None:
            return None
        if (len(point) != 3
                or any(not math.isfinite(v) or abs(v) >= 1e7 for v in point)):
            return None
        mapped = source_to_visual_display(point, comp)
        delta = tuple(mapped[i] - camera.position[i] for i in range(3))
        depth = -sum(delta[i] * toward[i] for i in range(3))
        if depth <= near:
            return None
        x = width * .5 + focal * sum(delta[i] * right[i] for i in range(3)) / depth
        y = height * .5 - focal * sum(delta[i] * up[i] for i in range(3)) / depth
        if (not all(math.isfinite(v) for v in (x, y))
                or max(abs(x), abs(y)) >= 1e6
                or x < -40 or x > width + 40 or y < -40 or y > height + 40):
            return None
        return (float(x), float(y))

    draw = ImageDraw.Draw(image)
    provisional = snapshot.illustrative_only
    flag_label = ("FLAG (green approximation)" if provisional
                  else "FLAG (pin candidate)")
    player_label = ("PLAYER (illustrative fairway proxy)" if provisional
                    else "PLAYER (tee proxy only)")
    ball_label = ("BALL (illustrative tee proxy)" if provisional
                  else "BALL (selected source)")
    if show_flag and (p := project(snapshot.flag)) is not None:
        x, y = p
        draw.ellipse((x-5, y-2, x+5, y+3),
                     fill="#f9f6da", outline="#1b3045", width=2)
        draw.line((x, y, x, y-30), fill="#ffffff", width=3)
        draw.polygon(((x+1, y-30), (x+22, y-24), (x+1, y-18)),
                     fill="#ff5c52")
        if labels:
            draw.text((x+24, y-31), flag_label,
                      fill="#ffffff", stroke_width=2,
                      stroke_fill="#203146")
    if show_player and (p := project(snapshot.tee_proxy)) is not None:
        x, y = p
        # Source anchor remains exactly at the tee. The figure's head/body
        # offsets are screen pixels ONLY, not an invented world position.
        draw.ellipse((x-4, y-26, x+4, y-18),
                     fill="#ffd2b0", outline="#203146", width=1)
        draw.line((x, y-18, x, y-8), fill="#e9ecf2", width=5)
        draw.line((x, y-8, x-7, y), fill="#e9ecf2", width=2)
        draw.line((x, y-8, x+8, y), fill="#e9ecf2", width=2)
        draw.line((x-1, y-15, x+10, y-12), fill="#e9ecf2", width=2)
        draw.line((x+10, y-12, x+15, y-1), fill="#56687c", width=2)
        draw.ellipse((x-3, y-3, x+3, y+3),
                     outline="#f6dc6d", width=2)
        if labels:
            draw.text((x+18, y-20), player_label,
                      fill="#f6dc6d", stroke_width=2,
                      stroke_fill="#203146")
    if show_ball and (p := project(snapshot.ball)) is not None:
        x, y = p
        draw.ellipse((x-7, y-7, x+7, y+7),
                     fill="#ffffff", outline="#0e1b2c", width=2)
        draw.ellipse((x-2, y-4, x, y-2), fill="#9db0c2")
        if labels:
            draw.text((x+10, y+8), ball_label,
                      fill="#ffffff", stroke_width=2,
                      stroke_fill="#203146")
    return image
