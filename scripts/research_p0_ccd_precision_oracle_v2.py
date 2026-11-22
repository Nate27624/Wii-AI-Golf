"""Synthetic, analytic first-entry CCD oracle; NOT a production collision solver.

The restricted fixture family consists of vertical line segments against one
triangle's AB edge or A vertex. Its exact radial cross-section is known in
advance. Decimal geometry is truth; the production solver is an optional,
read-only comparator and cannot change that truth.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, localcontext
import json
from pathlib import Path
import struct
import sys
from typing import Iterable

PRECISION = 100
RADIUS = Decimal("0.5")  # illustrative source query route, NOT physical ball size
TRIANGLE = ((0, 0, 0), (2, 0, 0), (0, 0, 2))


def D(value: str | int | Decimal) -> Decimal:
    """Use decimal inputs, not implicitly rounded native float parameters."""
    if isinstance(value, float):
        raise TypeError("provide a decimal string or Decimal; float requires explicit from_float")
    return Decimal(value)


def f32(value: float) -> float:
    return struct.unpack(">f", struct.pack(">f", value))[0]


# Exactly one IEEE binary32 ULP in the negative direction from -0.5.
ONE_F32_ULP_OUTSIDE = Decimal.from_float(struct.unpack(">f", bytes.fromhex("bf000001"))[0])


@dataclass(frozen=True)
class Fixture:
    name: str
    x: Decimal
    z: Decimal
    feature: str


FIXTURES = {
    "edge": Fixture("edge", D("1"), D("-0.25"), "edge"),
    "vertex": Fixture("vertex", D("-0.1"), D("-0.1"), "vertex"),
    "tangent": Fixture("tangent", D("1"), D("-0.5"), "edge"),
    "near_inside": Fixture("near_inside", D("1"), D("-0.4999"), "edge"),
    "one_f32_ulp_outside": Fixture("one_f32_ulp_outside", D("1"), ONE_F32_ULP_OUTSIDE, "edge"),
}


def _triple(v: Iterable[str | int | Decimal]) -> tuple[Decimal, Decimal, Decimal]:
    t = tuple(D(x) for x in v)
    if len(t) != 3 or not all(x.is_finite() for x in t):
        raise ValueError("three finite Decimal coordinates required")
    return t  # type: ignore[return-value]


def analytic_vertical(
    fixture: str, start_y: str | int | Decimal, end_y: str | int | Decimal,
    translation: Iterable[str | int | Decimal] = (0, 0, 0),
) -> dict:
    """Analytical cross-section only: vertical lines, known AB/vertex regions.

    This is deliberately not a mesh CCD algorithm and has no native-Wii semantics.
    Coordinates passed here are local to the synthetic triangle before shift.
    """
    if fixture not in FIXTURES:
        raise ValueError("unsupported analytic fixture")
    p, q = D(start_y), D(end_y)
    tx, ty, tz = _triple(translation)
    if not p.is_finite() or not q.is_finite():
        raise ValueError("nonfinite vertical coordinate")
    f = FIXTURES[fixture]
    with localcontext() as ctx:
        ctx.prec = PRECISION
        radial2 = f.z * f.z + (f.x * f.x if f.feature == "vertex" else D(0))
        gap2 = RADIUS * RADIUS - radial2
        base = {
            "fixture": fixture,
            "status": "MISS",
            "feature": f.feature,
            "radius_tag_only": str(RADIUS),
            "radial_gap2": str(gap2),
            "native_kcol_parity_verified": False,
            "training_approved": False,
        }
        if gap2 < 0:
            return base
        height = gap2.sqrt()
        if p == q:
            base["status"] = "ABSTAIN_INITIAL_OVERLAP" if abs(p) <= height else "MISS_ZERO_LENGTH"
            return base
        if abs(p) <= height:
            base["status"] = "ABSTAIN_INITIAL_OVERLAP"
            return base
        entry_y = height if p > 0 else -height
        # Moving toward the triangle, crossing first-entry altitude within [0,1].
        if (p > height and q > height) or (p < -height and q < -height):
            return base
        t = (entry_y - p) / (q - p)
        if not D(0) <= t <= D(1):
            return base
        center = (tx + f.x, ty + entry_y, tz + f.z)
        surface = ((tx + f.x, ty, tz) if f.feature == "edge" else (tx, ty, tz))
        # Local displacement avoids catastrophic translation cancellation.
        delta = ((f.x if f.feature == "vertex" else D(0)), entry_y, f.z)
        normal = tuple(v / RADIUS for v in delta)
        residual = sum((v * v for v in delta), D(0)) - RADIUS**2
        closest_t = -p / (q - p)
        fraction64 = float(t)
        closest64 = float(closest_t)
        # Closest-approach time is not the first-entry time at H >> 1.
        reconstructed_y = float(p) + fraction64 * (float(q) - float(p))
        gap_in_t = abs(t - closest_t)
        resolution = ("ABSTAIN_BINARY64_TIME_COLLAPSE" if fraction64 == closest64
                      and gap_in_t != 0 else "BINARY64_TIME_DISTINCT")
        base.update({
            "status": "HIT",
            "t_decimal": str(t),
            "first_center_xyz_decimal": [str(v) for v in center],
            "surface_xyz_decimal": [str(v) for v in surface],
            "outward_normal_decimal": [str(v) for v in normal],
            "squared_radius_residual_decimal": str(residual),
            "t_float64": fraction64,
            "closest_t_float64": closest64,
            "time_resolution": resolution,
            "float64_reconstructed_local_y": reconstructed_y,
            "float64_local_y_error": reconstructed_y - float(entry_y),
            "time_fraction_gap_decimal": str(gap_in_t),
        })
        return base


def _positions(fixture: str, p: Decimal, q: Decimal,
               shift: tuple[Decimal, Decimal, Decimal]) -> tuple[tuple[float, ...], tuple[float, ...], tuple[tuple[float, ...], ...]]:
    f = FIXTURES[fixture]
    tx, ty, tz = shift
    start = (float(tx + f.x), float(ty + p), float(tz + f.z))
    end = (float(tx + f.x), float(ty + q), float(tz + f.z))
    tri = tuple(tuple(float(D(v) + shift[i]) for i, v in enumerate(point)) for point in TRIANGLE)
    return start, end, tri


def observe_existing_solver(fixture: str, start_y: str | int | Decimal,
                            end_y: str | int | Decimal,
                            translation: Iterable[str | int | Decimal] = (0, 0, 0)) -> dict:
    """Read-only diagnostic. Does not assert the existing implementation must fail."""
    shift = _triple(translation)
    expected = analytic_vertical(fixture, start_y, end_y, shift)
    repo_root = Path(__file__).resolve().parents[1]
    src = str(repo_root / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from wii_ai_golf.physics.first_contact import Triangle, segment_hit  # local offline only

    start, end, tri = _positions(fixture, D(start_y), D(end_y), shift)
    try:
        hit = segment_hit(start, end, Triangle(*tri), float(RADIUS))
    except ValueError as exc:
        return {"observed": "ABSTAIN", "detail": type(exc).__name__,
                "comparison": ("AGREES" if expected["status"] == "ABSTAIN_INITIAL_OVERLAP"
                               else "DISAGREES")}
    if hit is None:
        return {"observed": "MISS", "comparison": (
            "AGREES" if expected["status"].startswith("MISS") else "FALSE_NEGATIVE")}
    t, center, surface, feature = hit
    actual_center = tuple(float(v) for v in center)
    observed = {"observed": "HIT", "feature": feature, "t_float64": t,
                "first_center_xyz_float64": actual_center,
                "surface_xyz_float64": tuple(float(v) for v in surface)}
    if expected["status"] != "HIT":
        observed["comparison"] = "PHANTOM_HIT"
    else:
        truth = tuple(float(Decimal(v)) for v in expected["first_center_xyz_decimal"])
        error = max(abs(a-b) for a,b in zip(actual_center, truth))
        observed["maximum_center_error"] = error
        observed["comparison"] = ("FEATURE_MISMATCH" if feature != expected["feature"]
                                   else "FIRST_ENTRY_CENTER_ERROR" if error > 1e-6
                                   else "AGREES")
    return observed


def split_path(fixture: str, h: str | int | Decimal, parts: int,
               *, quantize_f32: bool = False, compare: bool = False) -> dict:
    """Partition one straight, vertical segment; analytic truth is invariant."""
    if type(parts) is not int or not 1 <= parts <= 200:
        raise ValueError("parts must be 1..200")
    H = D(h)
    if H <= 0:
        raise ValueError("h must be positive")
    with localcontext() as ctx:
        ctx.prec = PRECISION
        ys = [H - D(2) * H * D(i) / D(parts) for i in range(parts + 1)]
    if quantize_f32:
        ys = [Decimal.from_float(f32(float(y))) for y in ys]
    first = None
    observations = []
    for i, (a, b) in enumerate(zip(ys, ys[1:])):
        expected = analytic_vertical(fixture, a, b)
        if first is None and expected["status"] == "HIT":
            local_t = Decimal(expected["t_decimal"])
            with localcontext() as ctx:
                ctx.prec = PRECISION
                entry_y = a + local_t * (b - a)
                global_t = (entry_y - ys[0]) / (ys[-1] - ys[0])
            first = {"index": i, "t_global_decimal": str(global_t),
                     "center_xyz_decimal": expected["first_center_xyz_decimal"]}
        if compare:
            observations.append(observe_existing_solver(fixture, a, b)["comparison"])
    return {"fixture": fixture, "pieces": parts, "quantized_f32": quantize_f32,
            "expected": "HIT" if first is not None else "MISS", "first": first,
            "observed_comparisons": observations if compare else None}


def report(*, compare: bool = False) -> dict:
    """Deterministic bounded reference matrix; no ROM, RAM, or real gameplay data."""
    cases = []
    suite = ([("edge", str(h), str(-h), (0, 0, 0)) for h in
              (2, 100, 10000, 100000, 1000000, 100000000, 10000000000,
               100000000000000, 10000000000000000)] +
             [("vertex", str(h), str(-h), (0, 0, 0)) for h in
              (2, 10000, 100000, 1000000, 100000000, 10000000000,
               10000000000000000)] +
             [("tangent", "0.01", "-0.01", (0, 0, 0)),
              ("near_inside", "0.01", "-0.01", (0, 0, 0)),
              ("one_f32_ulp_outside", "0.01", "-0.01", (0, 0, 0)),
              ("one_f32_ulp_outside", "0.1", "-0.1", (0, 0, 0)),
              ("edge", "100000", "-100000", (10000, 250, -30000)),
              ("edge", "-100000", "100000", (0, 0, 0)),
              ("edge", "1", "1", (0, 0, 0)),
              ("edge", "0", "0", (0, 0, 0))])
    for fixture, p, q, shift in suite:
        truth = analytic_vertical(fixture, p, q, shift)
        row = {"fixture": fixture, "start_y": p, "end_y": q,
               "translation": shift, "expected": truth}
        if compare:
            row["existing_solver_observation"] = observe_existing_solver(fixture, p, q, shift)
        cases.append(row)
    splits = [split_path("one_f32_ulp_outside", "0.1", n, quantize_f32=True,
                         compare=compare) for n in (1, 2, 4, 10, 20)]
    splits.append(split_path("edge", "2", 10, compare=compare))
    return {"classification": "SYNTHETIC_ANALYTICAL_DECIMAL_CCD_ORACLE",
            "source_query_radius_not_physical_ball_size": True,
            "native_kcol_parity_verified": False,
            "selected_ball_launch_verified": False,
            "training_approved": False,
            "cases": cases, "splits": splits}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare-existing", action="store_true",
                        help="read-only comparison to current provisional first_contact.segment_hit")
    parser.add_argument("--summary", action="store_true",
                        help="print concise deterministic classification instead of full Decimal matrix")
    args = parser.parse_args()
    data = report(compare=args.compare_existing)
    if args.summary:
        small = {k: v for k, v in data.items() if k not in ("cases", "splits")}
        small["cases"] = [{"fixture": x["fixture"], "start_y": x["start_y"],
                          "end_y": x["end_y"], "expected": x["expected"]["status"],
                          "time_resolution": x["expected"].get("time_resolution"),
                          "observed": x.get("existing_solver_observation", {}).get("comparison")}
                          for x in data["cases"]]
        small["splits"] = [{"pieces": x["pieces"], "expected": x["expected"],
                            "observed": x["observed_comparisons"] if args.compare_existing else None}
                           for x in data["splits"]]
        data = small
    print(json.dumps(data, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()