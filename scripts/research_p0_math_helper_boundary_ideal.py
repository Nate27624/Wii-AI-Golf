#!/usr/bin/env python3
"""Source-derived analytic boundary study for the Rev1 GolfMathTrig helper.

Uses only publicly documented original-source constants, IEEE float32
rounding, and HOST math. This is NOT a native PPC/NW4R LUT implementation,
a guest execution, an observed shot, or a training-eligible measurement.
No ROM, private capture, disk access, network, or Dolphin is used.
"""
from __future__ import annotations

import json
import math
import struct

def f32(value: float) -> float:
    return struct.unpack(">f", struct.pack(">f", value))[0]

TAU = f32(0.001)
PARAM_EASE = f32(0.85)
PARAM_SINE = f32(0.55)
WEIGHT_SCALE = f32(0.95)
WEIGHT_BASE = f32(0.05)
LIMIT = f32(10.995574951171875)
F30_ILLUSTRATIVE = f32(0.1)

def previous_positive_f32(value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Requires a positive finite float32")
    bits = struct.unpack(">I", struct.pack(">f", value))[0]
    return struct.unpack(">f", struct.pack(">I", bits - 1))[0]

def signed_power_ideal(parameter: float, argument: float) -> float:
    """Conditional ideal REAL function; source early guards retained.

    NW4R detail::FLog and FExp use native lookup/bit arithmetic, so this
    is not a bit-exact PPC implementation even if inputs are float32.
    """
    if not math.isfinite(parameter) or not math.isfinite(argument):
        raise ValueError("Only finite parameter and input allowed")
    if abs(argument) < TAU or parameter <= 0:
        return 0.0
    return math.copysign(abs(argument) ** math.log2(1.0 / parameter), argument)

def report() -> dict:
    below = previous_positive_f32(TAU)
    at = TAU
    for p in (PARAM_EASE, PARAM_SINE):
        if signed_power_ideal(p, below) != 0:
            raise AssertionError("Source cutoff not enforced")
        if not signed_power_ideal(p, at) > 0:
            raise AssertionError("Source cutoff lacks finite jump")
    f_ease = signed_power_ideal(PARAM_EASE, at)
    f_sine = signed_power_ideal(PARAM_SINE, at)
    weight_below = WEIGHT_BASE
    weight_at = f32(f32(WEIGHT_SCALE * f32(f_ease)) + WEIGHT_BASE)
    return {
        "kind": "S002_REV1_GOLFMATHTRIG_SOURCE_DERIVED_ANALYTIC_EDGE",
        "evidence": "SOURCE_DERIVED_HOST_MATH_NOT_NATIVE_EXECUTION",
        "original_native_source_basis": "LOCALOPS_67_SHA_PASS",
        "source_f32_threshold": TAU,
        "previous_positive_f32_input": below,
        "f32_input_at_threshold": at,
        "guard_below_threshold": "ZERO",
        "normal_finite_parameter_0p85": {
            "parameter_f32": PARAM_EASE,
            "ideal_exponent": math.log2(1.0 / PARAM_EASE),
            "ideal_f_at_threshold": f_ease,
            "ideal_weight_below": weight_below,
            "ideal_weight_at": weight_at,
            "ideal_weight_gain_ratio": weight_at / weight_below,
            "illustrative_step_change_at_f30_0p1": f32(F30_ILLUSTRATIVE * weight_at)
            - f32(F30_ILLUSTRATIVE * weight_below),
            "approx_outer_angle_magnitude_at_cutoff": LIMIT * (1.0 - TAU),
        },
        "normal_finite_parameter_0p55": {
            "parameter_f32": PARAM_SINE,
            "ideal_exponent": math.log2(1.0 / PARAM_SINE),
            "ideal_f_at_threshold": f_sine,
            "ideal_calc_0x1B0_jump_over_q": 5.0 * f_sine,
            "condition": "Q_nonzero_and_source_conditional_write_path",
        },
        "native_nw4r_table_parity_verified": False,
        "guest_executed_shot_verified": False,
        "accepted_ball_launch_verified": False,
        "training_approved": False,
    }

if __name__ == "__main__":
    print(json.dumps(report(), separators=(",", ":"), allow_nan=False))
