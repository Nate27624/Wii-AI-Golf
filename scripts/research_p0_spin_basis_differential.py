#!/usr/bin/env python3
"""Synthetic source-vector versus provisional spin integration differential.

Offline, no game actions, original bank access, paths, network, or writes.
The formula is a previously published static native-source hypothesis,
NOT verified executed selected-ball force semantics.
"""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import sys


def load_model():
    path = Path(__file__).resolve().parents[1] / "src/wii_ai_golf/physics/first_contact.py"
    spec = importlib.util.spec_from_file_location("p0_spin_differential_model", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODEL_MODULE_MISSING")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def norm(v):
    return math.sqrt(sum(c * c for c in v))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def source_basis(v):
    x, y, z = v
    lift = (-x * y, x * x + z * z, -z * y)
    lateral = (z, 0.0, -x)
    return lift, lateral


def report():
    model = load_model()
    cases = ((1.0, 1.0, 0.0), (0.0, 1.0, 0.0),
             (0.000001, 1.0, 0.0), (-1.0, 0.5, 2.0),
             (0.5, -1.0, -2.0))
    rows = []
    for velocity in cases:
        lift_basis, side_basis = source_basis(velocity)
        base = model.State((0.0, 1.0, 0.0), velocity,
                           acceleration=(0.0, 0.0, 0.0),
                           speed_like=2.0)
        plain = model.step_airborne(base)
        try:
            active = model.State(base.position, velocity,
                                 acceleration=base.acceleration,
                                 speed_like=2.0, lift=2.0, lateral=3.0)
            default_spin = model.step_airborne(active)
            default_outcome = "ALLOWED"
            residual_default = norm(tuple(x - y for x, y in zip(
                default_spin.velocity, plain.velocity)))
        except ValueError as exc:
            if "nonparallel explicit spin_axis" not in str(exc):
                raise
            default_outcome = "REJECTED_MISSING_SPIN_AXIS"
            residual_default = None
        explicit = model.step_airborne(model.State(
            base.position, velocity, acceleration=base.acceleration,
            speed_like=2.0, lift=2.0, lateral=3.0,
            spin_axis=(0.0, 0.0, 1.0)))
        residual_explicit = norm(tuple(x - y for x, y in zip(
            explicit.velocity, plain.velocity)))
        row = {
            "velocity": list(velocity),
            "source_lift_norm": round(norm(lift_basis), 12),
            "source_lateral_norm": round(norm(side_basis), 12),
            "source_lift_dot_v": round(dot(lift_basis, velocity), 12),
            "source_lateral_dot_v": round(dot(side_basis, velocity), 12),
            "source_lift_dot_lateral": round(dot(lift_basis, side_basis), 12),
            "default_spin_status": default_outcome,
            "provisional_default_spin_delta_v": (round(residual_default, 12)
                                                  if residual_default is not None else None),
            "provisional_explicit_spin_delta_v": round(residual_explicit, 12),
        }
        if not all(math.isfinite(n) for n in (
                row["source_lift_norm"], row["source_lateral_norm"],
                residual_explicit)):
            raise ValueError("NONFINITE_STUDY_OUTPUT")
        rows.append(row)
    return {
        "study": "P0_SYNTHETIC_SPIN_BASIS_DIFF_V1",
        "status": "SYNTHETIC_COMPARISON",
        "cases": rows,
        "native_selected_ball_parity_verified": False,
        "guest_timestep_verified": False,
        "training_approved": False,
    }


def main():
    print(json.dumps(report(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
