"""Read-only, per-sample flag/ball plus explicitly illustrative tee proxy.

All original positions remain in the PRIVATE qualified replay/live sample.
Only an accepted same-packet sample is shown. No inferred player RAM pointer,
native player model, physical marker height or verified world transform.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING

from .replay import BALL, AIM, float_hypothesis

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
    # Angle candidate from the current qualified packet, interpreted as
    # radians for display ONLY. Delta needs a same-source tee-to-pin baseline.
    aim_raw_degrees: float | None = None
    aim_delta_degrees: float | None = None
    aim_reference: str = ""  # "operator", "assumed", or "illustrative"


def from_sample(sample: "Sample | None", *, baseline: float | None = None,
                baseline_source: str | None = None,
                baseline_mode: str = "") -> SourceActorSnapshot:
    if (sample is None or not sample.source_qualified
            or not sample.source_digest):
        return SourceActorSnapshot()
    # sample.vec decodes only finite three-component f32. Never cache flag,
    # tee or ball across missing packets or changed source identities.
    raw = sample.words.get(AIM)
    raw_angle = (float_hypothesis(raw[0])
                 if raw is not None and len(raw) == 1 else None)
    if raw_angle is not None and abs(raw_angle) > math.tau:
        raw_angle = None
    valid_baseline = (
        raw_angle is not None and type(baseline) in (int, float)
        and math.isfinite(baseline) and abs(baseline) <= math.tau
        and isinstance(baseline_source, str)
        and baseline_source == sample.source_digest)
    delta = (math.degrees(math.remainder(raw_angle-baseline, math.tau))
             if valid_baseline else None)
    reference = ("operator" if baseline_mode.startswith("OPERATOR")
                 else "assumed") if valid_baseline else ""
    return SourceActorSnapshot(
        ball=sample.vec(BALL),
        flag=sample.vec(PIN),
        tee_proxy=sample.vec(TEE),
        source_qualified=True,
        aim_raw_degrees=(math.degrees(raw_angle)
                         if raw_angle is not None else None),
        aim_delta_degrees=delta,
        aim_reference=reference,
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
        ball=tee, flag=flag, tee_proxy=tee, illustrative_only=True,
        aim_delta_degrees=0., aim_reference="illustrative")


def draw_source_actors(image, comp, camera, snapshot: SourceActorSnapshot | None,
                       *, show_flag: bool = True, show_ball: bool = True,
                       show_player: bool = True, labels: bool = True):
    """Compatibility entry: genuine projected 3D meshes, not screen sprites.

    Source-selected positions are kept intact; model geometry and golfer
    placement remain explicitly illustrative and physically unverified.
    """
    from .scene_mesh_approximations import draw_3d_approximations
    return draw_3d_approximations(
        image, comp, camera, snapshot=snapshot,
        show_trees=False, show_flag=show_flag,
        show_ball=show_ball, show_player=show_player, labels=labels)
