"""Bounded two-sided solid terrain rendering helpers (display-only).

Source type/attribute comes exclusively from the source-labeled OBJ; face
orientation is used for generic visual lighting, never material attribution.
"""
from __future__ import annotations

import math

LIGHT = (0.38, 0.82, 0.42)


def shaded_hex(color: str, face: tuple[tuple[float, float, float], ...]) -> str:
    """Deterministic, winding-independent face lighting. No source semantics."""
    if len(color) != 7 or not color.startswith("#"):
        raise ValueError("Expected six-digit RGB color")
    a, b, c = face
    e1 = tuple(b[i] - a[i] for i in range(3))
    e2 = tuple(c[i] - a[i] for i in range(3))
    n = (
        e1[1]*e2[2]-e1[2]*e2[1],
        e1[2]*e2[0]-e1[0]*e2[2],
        e1[0]*e2[1]-e1[1]*e2[0],
    )
    norm = math.sqrt(sum(v*v for v in n))
    if not math.isfinite(norm) or norm <= 1e-12:
        raise ValueError("Cannot shade invalid triangle")
    light = abs(sum(n[i]*LIGHT[i] for i in range(3)) / norm)
    level = 0.72 + 0.27*min(1.0, light)
    try:
        channels = [int(color[i:i+2], 16) for i in (1, 3, 5)]
    except ValueError as exc:
        raise ValueError("Invalid RGB color") from exc
    return "#" + "".join(f"{max(0, min(255, round(v*level))):02x}" for v in channels)


def camera_depth(p: tuple[float, float, float], yaw: float, pitch: float) -> float:
    """Signed camera-facing component paired with inspector.gui.project."""
    x, y, z = p
    side = z*math.cos(yaw) - x*math.sin(yaw)
    return y*math.sin(pitch) - side*math.cos(pitch)


def back_to_front(
    faces: tuple[tuple[tuple[tuple[float, float, float], ...], int | None], ...],
    yaw: float,
    pitch: float,
) -> tuple[tuple[tuple[tuple[float, float, float], ...], int | None], ...]:
    """Sort bounded triangles for Tk's painter algorithm (not a depth buffer).

    Preserve face-material pairs; no back-face culling because source triangle
    winding and visible model ownership are not independently calibrated.
    """
    if not all(math.isfinite(v) for v in (yaw, pitch)):
        raise ValueError("Invalid camera")
    return tuple(sorted(
        faces,
        key=lambda entry: sum(camera_depth(p, yaw, pitch) for p in entry[0]) / 3,
    ))
