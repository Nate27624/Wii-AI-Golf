#!/usr/bin/env python3
"""Source-derived SinFIdx near-zero cutoff geometry, synthetic/public only.

Four samples from the published NW4R sin/cos lookup table suffice for
the seven n*pi zero neighborhoods inside the earlier source-derived
conditional |calc+0x1B8| < 10.995574951f domain. This is an approximation
of public decompiled code, not verified Gekko psq_st, FMA or gameplay.
"""
from __future__ import annotations

import json
import math
import struct

def f32(value: float) -> float:
    return struct.unpack(">f", struct.pack(">f", value))[0]

def bits(value: float) -> int:
    return struct.unpack(">I", struct.pack(">f", value))[0]

def float_from_bits(value: int) -> float:
    return struct.unpack(">f", struct.pack(">I", value))[0]

SOURCE_TAU = f32(0.001)
SOURCE_INDEX_GAIN = f32(40.7436637878418)
SOURCE_ANGLE_LIMIT = f32(10.995574951171875)
# Public decomp: nw4r/math/math_triangular.cpp sSinCosTbl.
# Only rows needed near multiple-of-128 zero crossings; four fields
# per row in original, retaining sin_val/sin_delta only here.
SINE_ZERO_NEIGHBORS = {
    0: (f32(0.0), f32(0.024541)),
    127: (f32(0.024541), f32(-0.024541)),
    128: (f32(0.0), f32(-0.024541)),
    255: (f32(-0.024541), f32(0.024541)),
}

def public_lut_sine_near_zero(angle_rad: float) -> float:
    """Near-zero-index public LUT emulator with assumed truncating cast.

    Deliberately refuses non-neighbor table indices; no generic
    mathematically smooth or source-exact SinFIdx substitute is implied.
    """
    if not math.isfinite(angle_rad) or abs(angle_rad) >= SOURCE_ANGLE_LIMIT:
        raise ValueError("Outside finite source conditional angle domain")
    idx = f32(f32(abs(angle_rad)) * SOURCE_INDEX_GAIN)
    whole = math.trunc(idx)
    frac = f32(idx - float(whole))
    tab = whole & 255
    if tab not in SINE_ZERO_NEIGHBORS:
        raise ValueError("Not a public sine zero-neighbor interval")
    sin_val, sin_delta = SINE_ZERO_NEIGHBORS[tab]
    val = f32(sin_val + f32(frac * sin_delta))
    return f32(-val) if angle_rad < 0 else val

def angle_boundary(positive_n: int, side: str) -> dict:
    """Find adjacent float32 values at |public_sine| < tau boundary."""
    if positive_n not in (0, 1, 2, 3) or side not in ("left", "right"):
        raise ValueError("Invalid positive source zero neighborhood")
    center = f32(positive_n * math.pi)
    offset = f32(0.003)
    lo = f32(center - offset) if side == "left" else center
    hi = center if side == "left" else f32(center + offset)
    if lo < 0:
        # n=0 left-side mirrors the right-hand interval.
        neg = angle_boundary(0, "right")
        return {"outside": -neg["outside"], "inside": -neg["inside"]}
    inside = lambda x: abs(public_lut_sine_near_zero(x)) < SOURCE_TAU
    if not inside(center) or inside(lo) == inside(hi):
        raise AssertionError("No isolated threshold between scan bounds")
    left = bits(lo)
    right = bits(hi)
    while right - left > 1:
        mid = (left + right) // 2
        if inside(float_from_bits(mid)):
            if side == "left":
                right = mid
            else:
                left = mid
        else:
            if side == "left":
                left = mid
            else:
                right = mid
    if side == "left":
        return {"outside": float_from_bits(left), "inside": float_from_bits(right)}
    return {"inside": float_from_bits(left), "outside": float_from_bits(right)}

def report() -> dict:
    nrows = []
    for n in range(-3, 4):
        a = abs(n)
        left, right = angle_boundary(a, "left"), angle_boundary(a, "right")
        # Mirror the geometry for negative crossings.
        if n < 0:
            left, right = (
                {"outside": -right["outside"], "inside": -right["inside"]},
                {"inside": -left["inside"], "outside": -left["outside"]},
            )
        center = f32(n * math.pi)
        if not abs(public_lut_sine_near_zero(center)) < SOURCE_TAU:
            raise AssertionError("Expected source table zero at index 128*n")
        nrows.append({
            "multiple_of_pi": n,
            "center_rad_f32": center,
            "inside_left_rad_f32": left["inside"],
            "inside_right_rad_f32": right["inside"],
            "deadzone_width_rad_approx": right["inside"] - left["inside"],
        })
    return {
        "kind": "S002_REV1_PUBLIC_SINFIDX_ZERO_NEIGHBOR_DEADZONE_STUDY",
        "evidence": "SOURCE_DERIVED_PUBLIC_DECOMP_SYNTHETIC",
        "normal_finite_input_only": True,
        "native_helper_cutoff_f32": SOURCE_TAU,
        "conditional_angle_limit_f32": SOURCE_ANGLE_LIMIT,
        "source_index_gain_f32": SOURCE_INDEX_GAIN,
        "public_sine_lut_neighbor_rows": 4,
        "zeros_within_conditional_domain": nrows,
        "fastcast_truncation_assumed": True,
        "native_f32_lut_parity_verified": False,
        "selected_ball_consumer_verified": False,
        "guest_shot_executed": False,
        "training_approved": False,
    }

if __name__ == "__main__":
    print(json.dumps(report(), separators=(",", ":"), allow_nan=False))
