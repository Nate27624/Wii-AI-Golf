"""Game-independent contracts. Coordinates and controls are NORMALIZED, not Wii units."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol, runtime_checkable
import math


@dataclass(frozen=True)
class Observation:
    scenario_id: str
    features: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.scenario_id or not self.features or not all(math.isfinite(v) for v in self.features):
            raise ValueError("An observation needs an ID and finite nonempty features")


@dataclass(frozen=True)
class ShotAction:
    # Placeholder action space: mapping to physical Wii Remote swings is NOT implemented.
    aim: float  # normalized [-1, 1]
    power: float  # normalized [0, 1]

    def __post_init__(self) -> None:
        if not (math.isfinite(self.aim) and -1.0 <= self.aim <= 1.0):
            raise ValueError("aim must be in [-1, 1]")
        if not (math.isfinite(self.power) and 0.0 <= self.power <= 1.0):
            raise ValueError("power must be in [0, 1]")


@dataclass(frozen=True)
class ShotResult:
    distance_m: float
    holed_out: bool
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not math.isfinite(self.distance_m) or self.distance_m < 0:
            raise ValueError("distance_m must be nonnegative and finite")


@runtime_checkable
class ShotEnvironment(Protocol):
    """One reset/step pair represents ONE attempt, not an entire 10-shot round."""

    def reset(self, scenario_id: str, *, seed: int) -> Observation:
        ...

    def step(self, action: ShotAction) -> ShotResult:
        ...
