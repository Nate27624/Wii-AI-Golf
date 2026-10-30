"""Pure, bounded 2D camera controls for the inspector's orthographic 3D view.

These calculations manipulate only screen-space viewing state, never Wii RAM,
source-component measurements, or player/ball coordinates. Mouse-wheel zoom
preserves the scene point under the cursor, as in scene editor navigation.
"""
from __future__ import annotations
import math

MIN_ZOOM = 0.04
MAX_ZOOM = 64.0
ZOOM_PER_NOTCH = 1.2


def wheel_steps(delta: object = None, button: object = None) -> float:
    """Normalize Windows/macOS Tk MouseWheel and X11 buttons 4/5."""
    if button == 4:
        return 1.0
    if button == 5:
        return -1.0
    if type(delta) not in (int, float) or not math.isfinite(delta):
        return 0.0
    return max(-8.0, min(8.0, float(delta) / 120.0))


def zoom_at_cursor(zoom: float, pan: tuple[float, float],
                   cursor: tuple[float, float], viewport: tuple[float, float],
                   steps: float) -> tuple[float, tuple[float, float]]:
    """Return new zoom and pixel pan while preserving the cursor's scene point.

    Screen = viewport_center + pan + zoom * fitted_projected_offset.
    The fitted offset at the cursor must remain unchanged as zoom varies.
    """
    values = (zoom, *pan, *cursor, *viewport, steps)
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        raise ValueError('Non-finite camera input')
    if zoom <= 0 or viewport[0] <= 0 or viewport[1] <= 0:
        raise ValueError('Invalid camera dimensions')
    new_zoom = min(MAX_ZOOM, max(MIN_ZOOM, zoom * ZOOM_PER_NOTCH ** max(-8.0, min(8.0, steps))))
    ratio = new_zoom / zoom
    center = (viewport[0] / 2.0, viewport[1] / 2.0)
    new_pan = tuple((cursor[i] - center[i]) - ratio * (cursor[i] - center[i] - pan[i])
                    for i in (0, 1))
    return new_zoom, new_pan


def pan_by(pan: tuple[float, float], dx: float, dy: float) -> tuple[float, float]:
    """Pan the editor in screen pixels (middle mouse drag)."""
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in (*pan, dx, dy)):
        raise ValueError('Invalid camera pan')
    return pan[0] + dx, pan[1] + dy
