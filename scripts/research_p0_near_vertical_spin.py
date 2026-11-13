#!/usr/bin/env python3
"""Synthetic near-vertical f32 spin-direction and illustrative-axis audit.

Source-derived directions are NORMALIZED when nondegenerate in source.
This host calculation does not establish native PPC normalizer, guard,
object receiver, acceleration or numerical timestep behavior.
No Dolphin, private archive, I/O mutation or networking.
"""
from __future__ import annotations

import importlib.util
import json
from math import sqrt, isfinite
from pathlib import Path
import struct
import sys


def model():
    path = Path(__file__).resolve().parents[1] / "src/wii_ai_golf/physics/first_contact.py"
    spec = importlib.util.spec_from_file_location("p0_near_vertical_model", path)
    if spec is None or spec.loader is None:
        raise ValueError("MODEL_NOT_AVAILABLE")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def f32(v):
    return struct.unpack(">f", struct.pack(">f", float(v)))[0]


def magnitude(a):
    return sqrt(sum(t * t for t in a))


def delta(a, b):
    return magnitude(tuple(x - y for x, y in zip(a, b)))


def run():
    m = model()
    rows = []
    for x0 in (0., 1e-12, 1e-9, 1e-7, 1e-5, 1e-3, 0.1, 1.):
        x = f32(x0)
        v = (x, 1., 0.)
        # Source-PC-qualified direction expressions, quantized inputs/products;
        # normalizer semantics and near-zero branch remain UNKNOWN.
        side_raw = (0., 0., f32(-x))
        lift_raw = (f32(-x), f32(x * x), 0.)
        plain = m.step_airborne(m.State((0., 2., 0.), v, acceleration=(0., 0., 0.),
                                        speed_like=2.))
        record = {"vx": x0,
                  "raw_s": round(magnitude(side_raw), 12),
                  "raw_l": round(magnitude(lift_raw), 12)}
        for axis, label in (((0., 1., 0.), "up"), ((0., 0., 1.), "other")):
            try:
                s = m.State((0., 2., 0.), v, acceleration=(0., 0., 0.),
                            speed_like=2., lift=2., lateral=3., spin_axis=axis)
                nxt = m.step_airborne(s)
                record[label] = round(delta(nxt.velocity, plain.velocity), 9)
            except ValueError as exc:
                if "nonparallel explicit spin_axis" not in str(exc):
                    raise
                record[label] = "REJECTED"
        rows.append(record)
    for row in rows:
        for key in ("vx", "raw_s", "raw_l", "up", "other"):
            if isinstance(row[key], (int, float)) and not isfinite(row[key]):
                raise ValueError("NONFINITE_STUDY_OUTPUT")
    result = {"study": "P0_NEAR_VERTICAL_NORMALIZED_SOURCE_DIRECTIONS_V1",
              "classification": "HOST_F32_INPUT_SOURCE_DIR_NOT_NATIVE_RUNTIME",
              "cases": rows, "native_normalization_guard_known": False,
              "source_vectors_normalized_when_eligible": True,
              "training_approved": False}
    if len(json.dumps(result, separators=(",", ":"))) > 2300:
        raise ValueError("OUTPUT_TOO_LARGE")
    return result


def main():
    print(json.dumps(run(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
