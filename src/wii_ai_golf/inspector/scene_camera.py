"""Deterministic Unity-like private visual camera. Never moves game actors.

Right mouse: look around from a FIXED camera world position.
Left mouse: orbit a focus point by moving camera, middle: translate camera
and focus together, wheel: dolly along gaze. These are source-model local
coordinates and DO NOT establish native Wii/KCL coordinate alignment.
"""
from __future__ import annotations
import math
from typing import NamedTuple


Vec3 = tuple[float, float, float]
LOOK_SENSITIVITY = 0.006
MAX_PITCH = 1.48
MIN_DISTANCE = 1e-5


class VisualCamera(NamedTuple):
    position: Vec3
    focus: Vec3
    yaw: float = 0.65
    pitch: float = 0.48
    scale: float = 1.0


def _dot(a: Vec3, b: Vec3) -> float:
    return sum(a[i] * b[i] for i in range(3))


def _add(a: Vec3, b: Vec3) -> Vec3:
    return tuple(a[i] + b[i] for i in range(3))


def _subtract(a: Vec3, b: Vec3) -> Vec3:
    return tuple(a[i] - b[i] for i in range(3))


def _mul(v: Vec3, k: float) -> Vec3:
    return tuple(k * c for c in v)


def _length(v: Vec3) -> float:
    return math.sqrt(_dot(v, v))


def camera_axes(yaw: float, pitch: float) -> tuple[Vec3, Vec3, Vec3]:
    """Return right, up, TOWARD-VIEWER for the original inspector yaw/pitch."""
    if not math.isfinite(yaw) or not math.isfinite(pitch) or abs(pitch) > MAX_PITCH:
        raise ValueError("Invalid visual camera orientation")
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    right = (cy, 0., sy)
    up = (-sy*sp, cp, cy*sp)
    toward_viewer = (-sy*cp, -sp, cy*cp)
    return right, up, toward_viewer


def playable_source_vertices(model) -> tuple[Vec3, ...]:
    """Frame source-mapped play area, not the oversized scenery plane.

    Material names are verified source DAE identifiers, not inferred grass.
    This changes *view framing only*, not vertex scale or world collision.
    """
    playable = {"M_Fairway", "M_Green", "M_Rough", "M_Bunker",
                "M_Kiwa_F", "M_Kiwa_R", "M_Kiwa_Bunker"}
    used = {i for face in model.faces if face.material in playable
            for i in face.vertices}
    if len(used) < 3:
        return model.vertices
    return tuple(model.vertices[i] for i in sorted(used))


def frame_playable_camera(model) -> VisualCamera:
    return fit_camera(playable_source_vertices(model))


def fit_camera(vertices: tuple[Vec3, ...]) -> VisualCamera:
    if not vertices:
        raise ValueError("Cannot frame empty original model")
    if not all(len(v) == 3 and all(math.isfinite(n) for n in v) for v in vertices):
        raise ValueError("Invalid source-model bounds")
    low = tuple(min(p[i] for p in vertices) for i in range(3))
    high = tuple(max(p[i] for p in vertices) for i in range(3))
    focus = tuple((low[i]+high[i])*.5 for i in range(3))
    radius = max(_length(_subtract(high, low))*.5, MIN_DISTANCE)
    # Original source camera views the complete bounding sphere at 55° FOV.
    _, _, to_viewer = camera_axes(.65, .48)
    distance = radius * 3.2
    return VisualCamera(_add(focus, _mul(to_viewer, distance)),
                        focus, .65, .48, radius)


def look_in_place(cam: VisualCamera, dx: float, dy: float) -> VisualCamera:
    """Unity-style RMB look: world-space camera position NEVER changes."""
    if not all(math.isfinite(x) for x in (dx, dy)):
        raise ValueError("Invalid camera drag delta")
    return cam._replace(yaw=cam.yaw + dx * LOOK_SENSITIVITY,
                        pitch=max(-MAX_PITCH, min(MAX_PITCH,
                                      cam.pitch + dy * LOOK_SENSITIVITY)))


def orbit(cam: VisualCamera, dx: float, dy: float) -> VisualCamera:
    """LMB scene orbit: keep pivot and radial distance, not camera position."""
    turned = look_in_place(cam, dx, dy)
    radius = max(MIN_DISTANCE, _length(_subtract(cam.position, cam.focus)))
    _, _, to_viewer = camera_axes(turned.yaw, turned.pitch)
    return turned._replace(position=_add(cam.focus, _mul(to_viewer, radius)))


def pan(cam: VisualCamera, dx: float, dy: float, viewport_height: int) -> VisualCamera:
    if not 16 <= viewport_height <= 10000:
        raise ValueError("Invalid viewport height")
    right, up, _ = camera_axes(cam.yaw, cam.pitch)
    distance = max(MIN_DISTANCE, _length(_subtract(cam.position, cam.focus)))
    factor = 2. * math.tan(math.radians(55.)*.5) * distance / viewport_height
    shift = _add(_mul(right, -dx*factor), _mul(up, dy*factor))
    return cam._replace(position=_add(cam.position, shift),
                        focus=_add(cam.focus, shift))


def move(cam: VisualCamera, *, forward: float = 0., right: float = 0.,
         vertical: float = 0., fast: bool = False) -> VisualCamera:
    """Unity-like RMB+WASD/QE translates a fixed-orientation camera."""
    if not all(math.isfinite(x) and abs(x) <= 100. for x in (forward, right, vertical)):
        raise ValueError("Unbounded camera navigation")
    right_axis, _, toward_viewer = camera_axes(cam.yaw, cam.pitch)
    step = max(MIN_DISTANCE, cam.scale*.18) * (4. if fast else 1.)
    delta = _add(_add(_mul(toward_viewer, -forward*step),
                       _mul(right_axis, right*step)),
                 (0., vertical*step, 0.))
    return cam._replace(position=_add(cam.position, delta),
                        focus=_add(cam.focus, delta))


def dolly(cam: VisualCamera, steps: float) -> VisualCamera:
    if not math.isfinite(steps) or abs(steps) > 8:
        raise ValueError("Invalid wheel movement")
    return move(cam, forward=steps*.75)
