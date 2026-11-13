#!/usr/bin/env python3
"""Offline analytical edge/vertex and trajectory-timing differential.

Uses only synthetic geometry and the current provisional first-contact solver.
No private asset, Dolphin, guest operation, writes, or network access.
"""
from __future__ import annotations

import importlib.util
import json
from math import isfinite, sqrt
from pathlib import Path
import sys


def model():
    path = Path(__file__).resolve().parents[1] / "src/wii_ai_golf/physics/first_contact.py"
    spec = importlib.util.spec_from_file_location("p0_ccd_boundary_model", path)
    if spec is None or spec.loader is None:
        raise ValueError("MODEL_NOT_AVAILABLE")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def evaluate():
    fc = model()
    tri = fc.Triangle((0., 0., 0.), (2., 0., 0.), (0., 0., 2.), face_id=17)
    radius = 0.5
    tests = [
        # label, x, z, vertical half-distance, nearest 2D distance, feature
        ("edge", 1., -0.25, 2., 0.25, "edge"),
        ("vertex", -0.25, -0.25, 2., sqrt(0.125), "vertex"),
        ("fast_edge", 1., -0.25, 1e6, 0.25, "edge"),
        ("grazing_inside", 1., -(radius - 1e-4), 2., radius - 1e-4, "edge"),
        ("grazing_outside", 1., -(radius + 1e-4), 2., radius + 1e-4, "miss"),
    ]
    rows = []
    for label, x, z, half, transverse, expected_feature in tests:
        hit = fc.segment_hit((x, half, z), (x, -half, z), tri, radius)
        if expected_feature == "miss":
            rows.append({"case": label, "analytic_hit": False, "hit": hit is not None,
                         "verdict": "AGREES" if hit is None else "FALSE_POSITIVE"})
            continue
        expected_t = (half - sqrt(radius * radius - transverse * transverse)) / (2 * half)
        if hit is None:
            rows.append({"case": label, "analytic_hit": True, "hit": False,
                         "verdict": "FALSE_NEGATIVE"})
            continue
        t, center, surface, feature = hit
        rows.append({"case": label, "analytic_hit": True, "hit": True,
                     "verdict": "AGREES", "feature": feature,
                     "expected_feature": expected_feature,
                     "t_err": round(abs(t - expected_t), 10),
                     "surface_y_err": round(abs(surface[1]), 10),
                     "center_y_err": round(abs(center[1] - sqrt(
                         radius * radius - transverse * transverse)), 10)})
    # A point-face high-speed crossing is independent of the swept-radius model.
    point = fc.segment_hit((0.3, 1e6, 0.3), (0.3, -1e6, 0.3), tri, 0.)
    if point is None:
        rows.append({"case": "fast_point", "analytic_hit": True,
                     "hit": False, "verdict": "FALSE_NEGATIVE"})
    else:
        rows.append({"case": "fast_point", "analytic_hit": True,
                     "hit": True, "verdict": "AGREES", "feature": point[3],
                     "t_err": round(abs(point[0] - 0.5), 10)})
    # Compare time parameterization for a single straight segment vs two
    # collinear pieces, with identical numerical sample coordinate span.
    p, q = (1., 2., -0.25), (1., -2., -0.25)
    single = fc.predict_contact_from_trajectory(
        [(4., p, (0., -4., 0.)), (20., q, (0., -4., 0.))],
        [tri], contact_mode="swept_kcol_query_0p5", assume_tree_free=True)
    split = fc.predict_contact_from_trajectory(
        [(4., p, (0., -4., 0.)), (12., (1., 0., -0.25), (0., -4., 0.)),
         (20., q, (0., -4., 0.))], [tri],
        contact_mode="swept_kcol_query_0p5", assume_tree_free=True)
    rows.append({"case": "time_split", "hit":
                 single.get("status") == split.get("status")
                 == "PROVISIONAL_FIRST_CONTACT",
                 "t_err": round(abs(single.get("contact_t", -1)
                                    - split.get("contact_t", -2)), 10)})
    # Speed ladder exposes loss-of-precision thresholds without creating
    # large output or presuming any guest-game scaling.
    speed_ladder = []
    for half in (2., 100., 10000., 100000., 1000000.):
        hit = fc.segment_hit((1., half, -0.25),
                             (1., -half, -0.25), tri, radius)
        speed_ladder.append({"span": int(2 * half), "hit": hit is not None})
    if not all(isfinite(v) for row in rows for v in row.values()
               if type(v) is float):
        raise ValueError("NONFINITE_STUDY_OUTPUT")
    result = {"study": "P0_CCD_EDGE_VERTEX_ANALYTIC_V1",
              "classification": "SYNTHETIC_NOT_NATIVE",
              "cases": rows, "speed_ladder": speed_ladder,
              "detected_false_negative": any(
                  x.get("verdict") == "FALSE_NEGATIVE" for x in rows),
              "native_kcol_parity": False,
              "training_approved": False}
    if len(json.dumps(result, separators=(",", ":"))) > 2300:
        raise ValueError("OUTPUT_TOO_LARGE")
    return result


def main():
    print(json.dumps(evaluate(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
