"""Empirically infer Hitting-the-Green tee index, NOT the game's shot counter.

Reference XYZ are 10 distinct repeated starts and three pin positions from
the real 417-sample 2026-10-24 Dolphin capture. Applicable only to US Rev1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import dist, isfinite
from typing import Any

SOURCE = ("https://github.com/Nate27624/Wii-AI-Golf/blob/"
          "data/hitting-green-20261024T073347Z-f47fba1c/research/results/"
          "hitting-green/20261024T073347Z-f47fba1c.json")
TEE_XYZ = (
    (2.2, -5.5, -318.0),
    (-145.6, -14.0, -414.6),
    (383.6, 8.0, -545.2),
    (147.8, -8.3, -219.1),
    (-38.0, -6.4, -168.6),
    (-241.1, -24.2, -647.2),
    (-129.5, -11.6, 18.0),
    (-0.6, -12.8, -568.2),
    (283.1, 14.6, -901.4),
    (580.7, -30.8, -6.9),
)
PIN_XYZ = (
    (210.1, -7.0, -350.5),
    (249.8, -2.0, -420.0),
    (174.1, -2.5, -449.7),
)


def _point(snapshot: dict[str, Any], key: str) -> tuple[float, float, float] | None:
    raw = snapshot.get("objects", {}).get(key, {}).get("translation_xyz_unverified")
    if not isinstance(raw, (list, tuple)) or len(raw) != 3 or any(
        type(x) not in (float, int) or not isfinite(x) for x in raw
    ):
        return None
    return tuple(float(x) for x in raw)


def _match(point: tuple[float, float, float] | None,
           references: tuple[tuple[float, float, float], ...], tolerance: float) -> int | None:
    if point is None:
        return None
    d = [dist(point, ref) for ref in references]
    best = min(range(len(d)), key=d.__getitem__)
    return best + 1 if d[best] <= tolerance else None


def infer_scene(snapshot: dict[str, Any], *, match_tolerance: float = 0.25,
                cup_tolerance_xz: float = 0.2,
                cup_tolerance_y: float = 0.5) -> dict[str, Any]:
    """Match a known tee/pin and reject mismatching cup/pin transition reads.

    Neither a tee match nor a stable pair proves a swing or the official
    shot/result number. Pin assignment can lag tee changes by many seconds.
    """
    if not all(isfinite(x) and x > 0 for x in (
        match_tolerance, cup_tolerance_xz, cup_tolerance_y
    )):
        raise ValueError("positive finite tolerances required")
    if (snapshot.get("game_id") != "RSPE01" or
        snapshot.get("disc_revision") != 1 or
        snapshot.get("mode") != "GAMEMODE_TR_NEARPIN"):
        return {"scene_status": "unsupported_or_inactive", "tee_index_observed": None,
                "pin_variant_observed": None, "pin_cup_aligned": False}
    start = _point(snapshot, "current_start_obj_ptr")
    pin = _point(snapshot, "current_pin_obj_ptr")
    cup = _point(snapshot, "cup_obj_ptr")
    match_tee = _match(start, TEE_XYZ, match_tolerance)
    match_pin = _match(pin, PIN_XYZ, match_tolerance)
    aligned = (pin is not None and cup is not None and
               ((pin[0] - cup[0])**2 + (pin[2] - cup[2])**2)**.5 <= cup_tolerance_xz and
               abs(pin[1] - cup[1]) <= cup_tolerance_y)
    ok = bool(match_tee and match_pin and aligned)
    return {
        "scene_status": "aligned_candidate" if ok else "transitional_or_unknown",
        "tee_index_observed": match_tee,
        "pin_variant_observed": match_pin if aligned else None,
        "pin_cup_aligned": bool(aligned),
        "source": "417-sample-user-report-repeated-tee-positions-NOT-game-counter",
    }


@dataclass
class StableSceneTracker:
    """Confirm N consecutive aligned positions, not an authoritative shot."""

    required_samples: int = 3
    _candidate: tuple[int, int] | None = field(default=None, init=False)
    _streak: int = field(default=0, init=False)
    _last_confirmed: tuple[int, int] | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if type(self.required_samples) is not int or self.required_samples < 2:
            raise ValueError("required_samples must be >= 2")

    def feed(self, sample: dict[str, Any]) -> dict[str, Any]:
        found = infer_scene(sample)
        pair = ((found["tee_index_observed"], found["pin_variant_observed"])
                if found["scene_status"] == "aligned_candidate" else None)
        if pair is None:
            self._candidate, self._streak = None, 0
            return {**found, "stable": False, "new_configuration": False,
                    "stable_samples": 0}
        if pair == self._candidate:
            self._streak += 1
        else:
            self._candidate, self._streak = pair, 1
        stable = self._streak >= self.required_samples
        is_new = stable and self._last_confirmed != pair
        if is_new:
            self._last_confirmed = pair
        return {**found, "stable": stable, "new_configuration": is_new,
                "stable_samples": self._streak,
                "pairing_warning": "empirical match, not verified by game shot counter"}
