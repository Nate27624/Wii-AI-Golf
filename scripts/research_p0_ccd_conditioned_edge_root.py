#!/usr/bin/env python3
"""Synthetic conditioned edge-cylinder root differential (research only).

Compare an analytic nearest-approach/offset quadratic with the existing
generic CCD root. This is a candidate numerical remedy, not a production
solver, native Wii KCol behavior, or evidence of the physical ball radius.
No private files, game actions, network, or writes.
"""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import sys


def load_contact():
    source = Path(__file__).resolve().parents[1] / "src/wii_ai_golf/physics/first_contact.py"
    spec = importlib.util.spec_from_file_location("p0_conditioned_edge_contact", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("CONTACT_SOLVER_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def mul(a, scale):
    return tuple(x * scale for x in a)


def conditioned_edge_hit(start, end, a, b, radius):
    """Nearest approach before solving for offset, not b*b-4*a*c.

    Returns earliest (t, center, edge point, residual distance), or None.
    This is only an edge-interior candidate, not a replacement for the
    complete face/edge/vertex solver.
    """
    edge = sub(b, a)
    length_sq = dot(edge, edge)
    if length_sq <= 0 or not math.isfinite(radius) or radius <= 0:
        raise ValueError("invalid geometry or radius")
    velocity = sub(end, start)
    relative = sub(start, a)
    along0 = dot(relative, edge) / length_sq
    alongv = dot(velocity, edge) / length_sq
    w0 = sub(relative, mul(edge, along0))
    wv = sub(velocity, mul(edge, alongv))
    denominator = dot(wv, wv)
    if denominator == 0 or not math.isfinite(denominator):
        return None
    middle = -dot(w0, wv) / denominator
    closest = add(w0, mul(wv, middle))
    squared_closest = dot(closest, closest)
    if squared_closest > radius * radius:
        return None
    half_width = math.sqrt(max(0., (radius * radius - squared_closest) /
                               denominator))
    candidates = []
    for t in (middle - half_width, middle + half_width):
        along = along0 + t * alongv
        if 0 <= t <= 1 and 0 < along < 1:
            center = add(start, mul(velocity, t))
            contact = add(a, mul(edge, along))
            residual = math.sqrt(dot(sub(center, contact), sub(center, contact)))
            # Compute and expose residual rather than silently widening the
            # original solver's acceptance tolerance to force a pass.
            candidates.append((t, center, contact, residual))
    return min(candidates, key=lambda candidate: candidate[0]) if candidates else None


def report():
    fc = load_contact()
    triangle = fc.Triangle((0., 0., 0.), (2., 0., 0.), (0., 0., 2.))
    rows = []
    for halfspan in (2, 100, 10000, 100000, 1000000, 10000000):
        p = (1., float(halfspan), -0.25)
        q = (1., -float(halfspan), -0.25)
        original = fc.segment_hit(p, q, triangle, 0.5)
        ref = conditioned_edge_hit(p, q, triangle.a, triangle.b, 0.5)
        expected = (halfspan - math.sqrt(0.25 - 0.0625)) / (2 * halfspan)
        if ref is None:
            raise AssertionError("CONDITIONED_REFERENCE_MISSED_ANALYTIC_HIT")
        rows.append({
            "span": 2 * halfspan,
            "existing_hit": original is not None,
            "conditioned_hit": True,
            "time_error": round(abs(ref[0] - expected), 12),
            "radial_error": round(abs(ref[3] - 0.5), 9),
        })
    negatives = []
    for transverse in (-0.5001, 0.5001):
        p, q = (1., 2., transverse), (1., -2., transverse)
        got = conditioned_edge_hit(p, q, triangle.a, triangle.b, 0.5)
        negatives.append(got is None)
    # Test the same equation after a large rigid translation of the scene.
    shift = (10000., 200., -30000.)
    move = lambda v: add(v, shift)
    translated = conditioned_edge_hit(
        move((1., 1000000., -0.25)), move((1., -1000000., -0.25)),
        move(triangle.a), move(triangle.b), 0.5)
    result = {
        "study": "P0_CCD_CONDITIONED_EDGE_ROOT_V1",
        "classification": "SYNTHETIC_NUMERICAL_REFERENCE",
        "cases": rows,
        "outside_radius_misses": negatives,
        "translation_hit": translated is not None,
        "native_kcol_parity_verified": False,
        "training_approved": False,
    }
    if len(json.dumps(result, separators=(",", ":"))) > 2300:
        raise ValueError("RECEIPT_TOO_LONG")
    return result


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, separators=(",", ":")))
