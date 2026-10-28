"""Offline S002 rotation-hypothesis test for the selected source player record.

Hypothesis only: player-record +0x40..+0x4C are a 2x2 rotation-like
matrix [c,-s;s,c], and +0x3C is ~atan2(s,c)+pi/2 radians.
Report uses a *previously captured* user-owned private B0..B3 object JSON.
No Dolphin, controller, live memory, savestate, publication or file output.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

# Python -I excludes the script directory; resolve the audited sibling explicitly.
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR in sys.path:
    sys.path.remove(_SCRIPT_DIR)
sys.path.insert(0, _SCRIPT_DIR)
import inspect_golf_aim_offsets_private as base

THETA_OFFSET = 0x3C
MATRIX_OFFSETS = (0x40, 0x44, 0x48, 0x4C)
QUATERNION_A = (0xA0, 0xA4, 0xA8, 0xAC)
QUATERNION_B = (0xB0, 0xB4, 0xB8, 0xBC)
QUATERNION_YAW_DEG_TOLERANCE = 0.25
UNIT_TOLERANCE = 2e-3
PHASE_TOLERANCE_RAD = 2e-3


def _as_f32(word: int) -> float:
    import struct
    return struct.unpack(">f", word.to_bytes(4, "big"))[0]


def signed_wrap(angle: float) -> float:
    return (angle + math.pi) % (2 * math.pi) - math.pi


def _quaternion_guess(words, offsets, matrix_angle: float) -> dict:
    "Interpret fixed floats as XYZW; this is still a source-unverified hypothesis."
    x, y, z, w = (_as_f32(words[offset // 4]) for offset in offsets)
    if not all(math.isfinite(t) for t in (x, y, z, w)):
        raise ValueError("Non-finite quaternion-like candidate")
    norm_squared = x*x + y*y + z*z + w*w
    yaw = math.atan2(2 * (w*y + x*z), 1 - 2*(y*y + z*z))
    discrepancy = math.degrees(signed_wrap(yaw - matrix_angle))
    return {
        "component_offsets_hex": [f"+0x{off:03X}" for off in offsets],
        "hypothetical_component_order": "x,y,z,w",
        "norm_squared": norm_squared,
        "norm_residual": norm_squared - 1,
        "hypothetical_Y_rotation_degrees": math.degrees(yaw),
        "yaw_matrix_angle_discrepancy_degrees": discrepancy,
        "norm_consistent_with_unit_quaternion":
            abs(norm_squared - 1) < UNIT_TOLERANCE,
    }


def inspect(report: dict) -> dict:
    # Reuse the existing strict report identity/phase/record validation.
    base.analyze(report)
    rows = base._words(report, "player_record_0", base.SELECTED_BYTES)
    rec = []
    for i, words in enumerate(rows):
        theta = _as_f32(words[THETA_OFFSET // 4])
        c, negative_s, s, repeated_c = (
            _as_f32(words[offset // 4]) for offset in MATRIX_OFFSETS
        )
        all_finite = all(map(math.isfinite, (theta, c, negative_s, s, repeated_c)))
        if not all_finite:
            raise ValueError("Non-finite float in candidate angular field")
        bitwise_c = words[0x40 // 4] == words[0x4C // 4]
        # IEEE754 sign flip produces -s; no numeric tolerance is required.
        bitwise_s = words[0x44 // 4] == (words[0x48 // 4] ^ 0x80000000)
        unit_residual = c * c + s * s - 1.0
        angle_from_matrix = math.atan2(s, c)
        quarter_turn_residual = signed_wrap(
            theta - angle_from_matrix - math.pi / 2
        )
        is_consistent = bool(
            bitwise_c and bitwise_s
            and abs(unit_residual) < UNIT_TOLERANCE
            and abs(quarter_turn_residual) < PHASE_TOLERANCE_RAD
        )
        qa = _quaternion_guess(words, QUATERNION_A, angle_from_matrix)
        qb = _quaternion_guess(words, QUATERNION_B, angle_from_matrix)
        rec.append({
            "phase": base.PHASES[i],
            "quaternion_A_candidate": qa,
            "quaternion_B_candidate": qb,
            "quaternion_A_Y_rotation_agrees_with_matrix":
                qa["norm_consistent_with_unit_quaternion"]
                and abs(qa["yaw_matrix_angle_discrepancy_degrees"])
                    < QUATERNION_YAW_DEG_TOLERANCE,
            "theta_radians": theta,
            "theta_degrees": math.degrees(theta),
            "matrix_derived_angle_radians": angle_from_matrix,
            "matrix_derived_angle_degrees": math.degrees(angle_from_matrix),
            "matrix_diagonal_exact": bitwise_c,
            "matrix_offdiagonal_opposites_exact": bitwise_s,
            "unit_vector_residual": unit_residual,
            "quarter_turn_relation_residual_radians": quarter_turn_residual,
            "consistent_with_2d_rotation_hypothesis": is_consistent,
        })
    theta_delta = math.degrees(signed_wrap(
        rec[2]["theta_radians"] - rec[1]["theta_radians"]
    ))
    matrix_delta = math.degrees(signed_wrap(
        rec[2]["matrix_derived_angle_radians"] -
        rec[1]["matrix_derived_angle_radians"]
    ))
    before_idle_stable = all(
        rows[0][o // 4] == rows[1][o // 4]
        for o in (THETA_OFFSET, *MATRIX_OFFSETS)
    )
    after_idle_stable = all(
        rows[2][o // 4] == rows[3][o // 4]
        for o in (THETA_OFFSET, *MATRIX_OFFSETS)
    )
    return {
        "kind": "PRIVATE-golf-aim-rotation-matrix-hypothesis",
        "game_id": "RSPE01",
        "disc_revision": 1,
        "phase_observations": rec,
        "before_aim_idle_stable": before_idle_stable,
        "after_aim_idle_stable": after_idle_stable,
        "theta_delta_degrees_during_WASD_aim": theta_delta,
        "matrix_delta_degrees_during_WASD_aim": matrix_delta,
        "theta_matrix_delta_discrepancy_degrees": theta_delta - matrix_delta,
        "all_phases_rotation_like": all(r[
            "consistent_with_2d_rotation_hypothesis"] for r in rec),
        "all_phases_quaternion_A_Y_rotation_agrees":
            all(r["quaternion_A_Y_rotation_agrees_with_matrix"] for r in rec),
        "all_phases_quaternion_B_norm_consistent":
            all(r["quaternion_B_candidate"]["norm_consistent_with_unit_quaternion"]
                for r in rec),
        "quaternion_A_B_idle_controls_stable": all(
            rows[0][off // 4] == rows[1][off // 4]
            and rows[2][off // 4] == rows[3][off // 4]
            for off in (*QUATERNION_A, *QUATERNION_B)),
        "quaternion_semantics_verified": False,
        "source_field_semantics_verified": False,
        "screen_aim_angle_verified": False,
        "world_axes_verified": False,
        "ball_motion_verified": False,
        "swing_power_verified": False,
        "approved_for_training": False,
        "allowed_to_publish": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        # Same local-only source location guard as the original inspector.
        root = (Path(__file__).resolve().parents[2] /
                "Wii-AI-Golf-Data").resolve(strict=True)
        target = args.report
        if target.is_symlink() or not target.is_file():
            raise ValueError("Missing or linked private report")
        actual = target.resolve(strict=True)
        if not actual.is_relative_to(root) or actual.stat().st_size > 512000:
            raise ValueError("Report outside canonical private Data root")
        data = json.loads(actual.read_text(encoding="utf-8"))
        result = inspect(data)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (ValueError, OSError, OverflowError, TypeError, KeyError) as exc:
        print("Private source-rotation inspection stopped:", str(exc),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
