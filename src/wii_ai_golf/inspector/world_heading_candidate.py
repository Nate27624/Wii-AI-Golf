"""Instantaneous XZ aim-heading hypothesis from the live source-selected player scalar.

Operator Rev1 no-shot data: selected record +0x3C angle increases on visual
left and decreases on right. A direct candidate XZ forward bearing is pi/2-a,
NOT an accumulated input delta and NOT independently proved world avatar yaw.
No controller, RPC, guest writes, calibration state or inferred player XYZ.
"""
from __future__ import annotations

import math

from .replay import AIM, Sample, float_hypothesis

PIN = "pin_candidate"
TEE = "tee_start_candidate"


def _valid_angle(sample: Sample) -> float | None:
    if not sample.source_qualified or not sample.source_digest:
        return None
    word = sample.words.get(AIM)
    if word is None or len(word) != 1:
        return None
    angle = float_hypothesis(word[0])
    if angle is None or not -math.tau <= angle <= math.tau:
        return None
    return angle


def wrap_radians(angle: float) -> float:
    """Signed [-pi,pi] phase preserving all quadrants; no delta accumulation."""
    return math.atan2(math.sin(angle), math.cos(angle))


def candidate_heading_degrees(sample: Sample) -> float | None:
    """Candidate bearing in source XZ (+X=0,+Z=+90), NOT verified avatar yaw."""
    angle = _valid_angle(sample)
    return None if angle is None else math.degrees(wrap_radians(math.pi/2-angle))


def direct_aim_ray(
    sample: Sample, landmarks: dict[str, tuple[float, float, float]]
) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    """Source-qualified ray, anchored at TEE (never presumed player position).

    Length is 23% of same-packet tee-to-pin horizontal distance. The pin
    supplies SCALE only, never a starting direction or aiming baseline.
    """
    angle = _valid_angle(sample)
    tee, pin = landmarks.get(TEE), landmarks.get(PIN)
    if angle is None or tee is None or pin is None:
        return None
    if (len(tee) != 3 or len(pin) != 3 or
            not all(math.isfinite(v) for v in (*tee, *pin))):
        return None
    dx, dz = pin[0]-tee[0], pin[2]-tee[2]
    distance = math.hypot(dx, dz)
    if not 1e-5 < distance <= 1e6:
        return None
    length = 0.23*distance
    # cos(pi/2-a)=sin(a), sin(pi/2-a)=cos(a).
    return tee, (tee[0]+length*math.sin(angle), tee[1],
                 tee[2]+length*math.cos(angle))


def candidate_flag_error_degrees(
    sample: Sample, landmarks: dict[str, tuple[float, float, float]]
) -> float | None:
    """Heading minus tee-to-pin bearing. Meaningful only if aimed at flag."""
    if direct_aim_ray(sample, landmarks) is None:
        return None
    heading = candidate_heading_degrees(sample)
    tee, pin = landmarks[TEE], landmarks[PIN]
    bearing = math.atan2(pin[2]-tee[2], pin[0]-tee[0])
    if heading is None:
        return None
    return math.degrees(wrap_radians(math.radians(heading)-bearing))
