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
    # Tk's pointer x increases to the right. The prior positive yaw made
    # the view respond opposite to the operator's intended RMB turn.
    # Keep the CAMERA EYE (and its orbit focus) *bitwise unchanged*.
    return cam._replace(yaw=cam.yaw - dx * LOOK_SENSITIVITY,
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


def held_navigation_direction(keys: set[str] | frozenset[str],
                              *, right_mouse: bool = False) -> Vec3:
    """Keyboard *state* rather than discrete events, normalized diagonals.

    Arrow keys are always active when the source 3D canvas has focus.
    WASD and Q/E require right mouse, matching the inspector's fly mode.
    The returned values are unitless local-camera velocity directions.
    """
    arrows = {
        "up": (1, 0, 0), "down": (-1, 0, 0),
        "left": (0, -1, 0), "right": (0, 1, 0),
    }
    flying = {
        "w": (1, 0, 0), "s": (-1, 0, 0),
        "a": (0, -1, 0), "d": (0, 1, 0),
        "q": (0, 0, -1), "e": (0, 0, 1),
    }
    axes = [0., 0., 0.]
    for key in keys:
        direction = arrows.get(key)
        if direction is None and right_mouse:
            direction = flying.get(key)
        if direction is not None:
            for i in range(3):
                axes[i] += direction[i]
    mag = math.sqrt(sum(v*v for v in axes))
    if mag > 1.:
        return tuple(v/mag for v in axes)
    return tuple(axes)


def move_continuous(cam: VisualCamera, keys: set[str] | frozenset[str],
                    dt_seconds: float, *, right_mouse: bool = False,
                    fast: bool = False) -> VisualCamera:
    """Frame-time-proportional eye translation while a movement key is held.

    dt is bounded to avoid huge jumps when the OS/Tk stalls. A continuous
    motion tick never changes yaw, pitch or source model coordinates.
    """
    if not math.isfinite(dt_seconds) or dt_seconds < 0:
        raise ValueError("Invalid source camera frame duration")
    fwd, side, up = held_navigation_direction(keys, right_mouse=right_mouse)
    if fwd == side == up == 0 or dt_seconds == 0:
        return cam
    # move() advances .18*radius per argument unit. Target 1.2 radii/s.
    multiplier = min(dt_seconds, .05)*(1.2/.18)
    return move(cam, forward=fwd*multiplier,
                right=side*multiplier, vertical=up*multiplier, fast=fast)


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
