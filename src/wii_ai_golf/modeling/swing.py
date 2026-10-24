"""Pure, uncalibrated Felk Preview4 swing trace generator.

Rows are [hold_A, dx,dy,dz,distance_m,speed_m_s,return_speed_m_s,angle_rad].
No Dolphin calls or claims about real-ball contact.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, replace
import hashlib
import json
import math

AXES = {
    "x+": (1.0,0.0,0.0), "x-": (-1.0,0.0,0.0),
    "y+": (0.0,1.0,0.0), "y-": (0.0,-1.0,0.0),
    "z+": (0.0,0.0,1.0), "z-": (0.0,0.0,-1.0),
}

@dataclass(frozen=True)
class SwingProfile:
    axis: str = "y+"
    speed_m_s: float = 3.5
    travel_m: float = 0.6
    backswing_m: float = 0.25
    return_speed_m_s: float = 2.0
    angle_rad: float = 0.0
    ready_frames: int = 12
    backswing_frames: int = 15
    downswing_frames: int = 20
    release_frames: int = 12

    def __post_init__(self):
        if self.axis not in AXES:
            raise ValueError("axis must be one of x+/x-/y+/y-/z+/z-")
        for key, high in (("speed_m_s",8.0),("travel_m",1.5),
                          ("backswing_m",1.5),("return_speed_m_s",8.0)):
            v = getattr(self,key)
            if type(v) not in (float,int) or not math.isfinite(v) or not 0 <= v <= high:
                raise ValueError(key+" outside valid range")
        if type(self.angle_rad) not in (float,int) or not math.isfinite(self.angle_rad) or abs(self.angle_rad)>math.pi:
            raise ValueError("angle_rad outside +/-pi")
        for key in ("ready_frames","backswing_frames","downswing_frames","release_frames"):
            v=getattr(self,key)
            if type(v) is not int or not 1<=v<=300:
                raise ValueError(key+" must be integer in 1..300")
        if self.total_frames>600:
            raise ValueError("exceeds 600 trace frames")

    @property
    def total_frames(self):
        return self.ready_frames+self.backswing_frames+self.downswing_frames+self.release_frames

    def with_changes(self, **changes):
        return replace(self,**changes)


def swing_trace(profile: SwingProfile) -> list[list[bool | float]]:
    """Construct a hypothesis, NOT a validated game-recognized waveform."""
    axis=AXES[profile.axis]
    backward=tuple(-v for v in axis)
    idle=[True,0.0,0.0,0.0,0.0,0.0,0.0,0.0]
    back=[True,*backward,profile.backswing_m,
          min(8.0,profile.speed_m_s*0.35),profile.return_speed_m_s,profile.angle_rad]
    down=[True,*axis,profile.travel_m,
          profile.speed_m_s,profile.return_speed_m_s,profile.angle_rad]
    release=[False,0.0,0.0,0.0,0.0,0.0,0.0,0.0]
    return ([list(idle) for _ in range(profile.ready_frames)]
          + [list(back) for _ in range(profile.backswing_frames)]
          + [list(down) for _ in range(profile.downswing_frames)]
          + [list(release) for _ in range(profile.release_frames)])


def trace_hash(trace):
    return hashlib.sha256(json.dumps(trace,separators=(",",":"),allow_nan=False).encode("utf-8")).hexdigest()
