"""Explicit, bounded Wii Remote swing trace client for Felk Preview 4.

Inputs use documented meters, m/s and radians; their response inside Wii
Sports is UNCALIBRATED and must be verified by on-screen observation.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Sequence

from .atomic_client import AtomicTraceClient


@dataclass(frozen=True)
class SwingSample:
    hold_a: bool
    direction: tuple[float, float, float]
    distance_m: float
    speed_m_s: float
    return_speed_m_s: float
    angle_rad: float

    def __post_init__(self):
        if type(self.hold_a) is not bool or len(self.direction) != 3:
            raise ValueError("hold_a bool and 3-component direction required")
        nums = self.direction + (self.distance_m, self.speed_m_s, self.return_speed_m_s, self.angle_rad)
        if any(type(x) not in (float, int) or not math.isfinite(x) for x in nums):
            raise ValueError("swing values must be finite numerics")
        if any(abs(v) > 1 for v in self.direction):
            raise ValueError("direction components must be -1..1")
        if not 0 <= self.distance_m <= 1.5 or not 0 <= self.speed_m_s <= 8 or not 0 <= self.return_speed_m_s <= 8:
            raise ValueError("distance or speed exceeds conservative bounds")
        if abs(self.angle_rad) > math.pi:
            raise ValueError("angle exceeds pi")


class SwingTraceClient(AtomicTraceClient):
    """Uses the existing atomic scheduler's trace.status and trace.abort."""

    def submit(self, samples: Sequence[SwingSample]) -> dict[str, Any]:
        if not 1 <= len(samples) <= 600:
            raise ValueError("1..600 frame samples required")
        if any(not isinstance(s, SwingSample) for s in samples):
            raise ValueError("all samples must be SwingSample instances")
        payload = [
            [s.hold_a, *s.direction, s.distance_m, s.speed_m_s, s.return_speed_m_s, s.angle_rad]
            for s in samples
        ]
        response = self.rpc.call("trace.submit_swing", [self.port, payload])
        if not isinstance(response, dict) or response.get("state") != "scheduled" or response.get("kind") != "swing":
            raise RuntimeError("Patched swing trace handler not available or returned invalid ACK")
        return response
