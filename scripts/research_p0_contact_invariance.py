#!/usr/bin/env python3
"""Deterministic synthetic earliest-contact metamorphic probe.

Compares geometry transformations against the provisional CCD solver.
Never reads game data, interacts with Dolphin, or writes files.
"""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import sys


def load_model():
    path = Path(__file__).resolve().parents[1] / "src/wii_ai_golf/physics/first_contact.py"
    spec = importlib.util.spec_from_file_location("p0_contact_differential_model", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODEL_MODULE_MISSING")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def difference(a, b):
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))


def shifted(v, shift):
    return tuple(x+y for x,y in zip(v, shift))


def scaled(v, factor):
    return tuple(factor*x for x in v)


def report():
    model = load_model()
    triangle = model.Triangle((-10., 0., -10.), (0., 0., 10.),
                              (10., 0., -10.), face_id=1)
    a, b, c = triangle.a, triangle.b, triangle.c
    centroid = tuple((a[i]+b[i]+c[i])/3 for i in range(3))
    subdivisions = (
        model.Triangle(a, b, centroid, face_id=2),
        model.Triangle(b, c, centroid, face_id=3),
        model.Triangle(c, a, centroid, face_id=4),
    )
    shift = (10000., -9000., 3000.)
    p, q = (0., 5., 0.), (0., -1., 0.)
    results = []
    for radius in (0., .5):
        base = model.segment_hit(p, q, triangle, radius)
        if base is None:
            raise ValueError("BASELINE_CONTACT_MISSING")
        variants = {
            "winding_reversed": (
                [model.Triangle(c, b, a)], p, q, radius, (0., 0., 0.), 1.),
        }
        # Explicit translations avoid constructor assumptions about iterables.
        variants["large_translation"] = (
            [model.Triangle(shifted(a, shift), shifted(b, shift),
                            shifted(c, shift))],
            shifted(p, shift), shifted(q, shift), radius, shift, 1.)
        variants["double_scale"] = (
            [model.Triangle(scaled(a, 2.), scaled(b, 2.), scaled(c, 2.))],
            scaled(p, 2.), scaled(q, 2.), radius*2., (0.,0.,0.), 2.)
        variants["subdivided"] = (list(subdivisions), p, q, radius,
                                   (0.,0.,0.), 1.)
        for label, (triangles, start, stop, query_radius, origin, scale) in variants.items():
            candidates = []
            for t in triangles:
                hit = model.segment_hit(start, stop, t, query_radius)
                if hit is not None:
                    candidates.append(hit)
            if not candidates:
                results.append({"variant": label, "radius": radius,
                                "status": "NO_HIT_WHERE_BASELINE_HITS"})
                continue
            got = min(candidates, key=lambda item: item[0])
            center = tuple((got[1][i]-origin[i])/scale for i in range(3))
            surface = tuple((got[2][i]-origin[i])/scale for i in range(3))
            results.append({
                "variant": label,
                "radius": radius,
                "status": "COMPARABLE_HIT",
                "time_difference": round(abs(got[0]-base[0]), 12),
                "center_xyz_difference": round(difference(center, base[1]), 12),
                "surface_xyz_difference": round(difference(surface, base[2]), 12),
                "base_feature": base[3],
                "variant_feature": got[3],
            })
    return {
        "study": "P0_SYNTHETIC_CONTACT_INVARIANCE_V1",
        "status": "SYNTHETIC_COMPARISON",
        "cases": results,
        "query_radius_not_ball_radius": True,
        "native_collision_parity_verified": False,
        "training_approved": False,
    }


def main():
    print(json.dumps(report(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
