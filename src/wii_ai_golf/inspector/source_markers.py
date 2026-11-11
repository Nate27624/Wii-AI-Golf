"""Optional original-source markers on the unified PRIVATE visual inspector.

Original 94 tree base positions come ONLY from strict #411/#432 JSON loader.
Ball, cache, tee, pin originate ONLY from a qualified matching P0 sample.
No player body coordinates are presently source-verified: selected-player
metadata is shown in the HUD only, never plotted at a guessed position.

All source coordinates may be shown via the independent KCL-to-DAE
DISPLAY-ONLY bounding fit. That is NOT native world/physics alignment.
Never use this visualization for contact detection, game action or training.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING

from .replay import BALL, CACHE, Sample
from .scene_camera import VisualCamera, camera_axes

if TYPE_CHECKING:
    from .tree_positions import TreePositions
    from .unified_source_view import ComparisonKCL

PIN = "pin_candidate"
TEE = "tee_start_candidate"


@dataclass(frozen=True)
class SourceMarkerSnapshot:
    """One original sampler packet: no temporal joins between source epochs."""
    ball: tuple[float, float, float] | None = None
    cache: tuple[float, float, float] | None = None
    tee: tuple[float, float, float] | None = None
    pin: tuple[float, float, float] | None = None
    source_digest: str | None = None
    selected_player_index: int | None = None
    source_qualified: bool = False


def marker_snapshot(sample: Sample | None,
                    selected_player_index: int | None = None) -> SourceMarkerSnapshot:
    """Fail closed if packet cannot establish source-qualified same-frame XYZ."""
    if selected_player_index is not None and (
            type(selected_player_index) is not int or not 0 <= selected_player_index <= 7):
        selected_player_index = None
    if sample is None or not sample.source_qualified or not sample.source_digest:
        # Player index is a live scene-context field. It must NEVER survive
        # a failed/missing packet as if the actor belonged to that source epoch.
        return SourceMarkerSnapshot()
    return SourceMarkerSnapshot(
        ball=sample.vec(BALL), cache=sample.vec(CACHE),
        tee=sample.vec(TEE), pin=sample.vec(PIN),
        source_digest=sample.source_digest,
        selected_player_index=selected_player_index,
        source_qualified=True,
    )


def display_transform(comp: "ComparisonKCL",
                      point: tuple[float, float, float]):
    """Apply the SAME explicitly unverified visual-KCL comparison transform."""
    if len(point) != 3 or not all(math.isfinite(x) and abs(x) < 1e7 for x in point):
        raise ValueError("Nonfinite source marker")
    return tuple(comp.source_scale*point[i]+comp.source_translation[i]
                 for i in range(3))


def _project(point, camera: VisualCamera, viewport: tuple[int, int]):
    right, up, toward_viewer = camera_axes(camera.yaw, camera.pitch)
    delta = tuple(point[i]-camera.position[i] for i in range(3))
    depth = -sum(delta[i]*toward_viewer[i] for i in range(3))
    if depth <= max(1e-6, camera.scale*.001):
        return None
    w, h = viewport
    f = h/(2*math.tan(math.radians(55)*.5))
    px=w*.5 + f*sum(delta[i]*right[i] for i in range(3))/depth
    py=h*.5 - f*sum(delta[i]*up[i] for i in range(3))/depth
    if not math.isfinite(px) or not math.isfinite(py) or abs(px)>1e6 or abs(py)>1e6:
        return None
    return px, py, depth


def draw_source_markers(image, camera: VisualCamera,
                        comp: "ComparisonKCL | None",
                        trees: "TreePositions | None",
                        sample: SourceMarkerSnapshot | None,
                        *, show_trees: bool, show_tree_crowns: bool,
                        show_ball: bool, show_tee_pin: bool,
                        show_cache: bool):
    """Draw only source-backed scene markers; return source marker counts.

    Requires candidate KCL comparison fit; with no KCL (or invalid source
    packet), leave the texture frame unmodified rather than invent positions.
    The crowns are *illustrative 2D icons*, not native tree meshes/height.
    """
    if comp is None:
        return image, {"trees":0, "ball":0, "tee":0, "pin":0, "cache":0}
    from PIL import ImageDraw
    painter = ImageDraw.Draw(image)
    w,h=image.size
    count={"trees":0, "ball":0, "tee":0, "pin":0, "cache":0}

    if show_trees and trees is not None:
        # Tree bases come from exact 94 source coordinates; fake 2D crowns
        # are an EXPLICIT optional viewer illustration, not game art.
        for i, point in enumerate(trees.positions, start=1):
            p=_project(display_transform(comp,point),camera,(w,h))
            if p is None:
                continue
            x,y,_=p
            if x < -25 or y < -25 or x > w+25 or y > h+25:
                continue
            if show_tree_crowns:
                painter.ellipse((x-7,y-14,x+7,y+1),fill=(30,112,73),
                                outline=(165,197,103),width=1)
                painter.line((x,y-1,x,y+4),fill=(117,78,49),width=2)
            painter.ellipse((x-2,y-2,x+2,y+2),fill=(234,250,124))
            count["trees"]+=1

    if sample is not None and sample.source_qualified and sample.source_digest:
        for name, pt, enabled, color in (
            ("ball",sample.ball,show_ball,(250,250,250)),
            ("cache",sample.cache,show_cache,(241,170,80)),
            ("tee",sample.tee,show_tee_pin,(73,219,124)),
            ("pin",sample.pin,show_tee_pin,(62,218,247)),
        ):
            if not enabled or pt is None:
                continue
            p=_project(display_transform(comp,pt),camera,(w,h))
            if p is None:
                continue
            x,y,_=p
            if not -15<=x<=w+15 or not -15<=y<=h+15:
                continue
            if name=="pin":
                painter.line((x,y+9,x,y-11), fill=color,width=2)
                painter.polygon(((x,y-11),(x+12,y-6),(x,y-2)),fill=color)
            elif name=="tee":
                painter.polygon(((x,y-6),(x+6,y),(x,y+6),(x-6,y)),fill=color)
            else:
                radius=5 if name=="ball" else 4
                painter.ellipse((x-radius,y-radius,x+radius,y+radius),
                                fill=color,outline=(20,25,30),width=1)
            count[name]+=1
    return image,count


def source_marker_status(snapshot: SourceMarkerSnapshot | None,
                         trees, comp, *, show_player: bool) -> str:
    tree_info = (f"{len(trees.positions)} exact tree bases (NOT tree meshes)"
                 if trees is not None else "Tree source JSON unavailable")
    if snapshot is None or not snapshot.source_qualified:
        actor = "ball / tee / pin: unavailable (no source-qualified sample)"
    else:
        fields=(("ball",snapshot.ball),("tee",snapshot.tee),
                ("pin",snapshot.pin),("cache",snapshot.cache))
        actor = "sample: " + ", ".join(
            f"{name} {'XYZ candidate' if pt is not None else 'absent'}"
            for name,pt in fields)
    player="player hidden"
    if show_player:
        selected = (snapshot.selected_player_index if snapshot is not None
                    else None)
        player=(f"selected player {selected}" if selected is not None
                else "selected player unknown")
        player += "; 3D position/model NOT verified (no fake golfer)"
    alignment=("KCL/DAE display-only fit UNVERIFIED"
               if comp is not None else "No KCL fit; markers not positioned")
    return f"{tree_info} · {actor} · {player} · {alignment}"
