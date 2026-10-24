"""Synthetic smoke-test environment. NOT a Wii Sports physics model."""
from __future__ import annotations

from .protocol import Observation, ShotAction, ShotResult


TOY_SCENARIOS: dict[str, tuple[float, float]] = {
    "toy-01": (-0.8, -0.6),
    "toy-02": (-0.4, 0.7),
    "toy-03": (0.0, -0.2),
    "toy-04": (0.5, 0.8),
    "toy-05": (0.9, -0.7),
    "toy-06": (-0.7, 0.2),
    "toy-07": (0.3, 0.3),
    "toy-08": (0.7, -0.1),
}


class ToyGolfEnvironment:
    """Deterministic stand-in used ONLY to validate interfaces and optimizer plumbing."""

    def __init__(self, scenarios: dict[str, tuple[float, float]] | None = None) -> None:
        self.scenarios = scenarios if scenarios is not None else TOY_SCENARIOS
        self._observation: Observation | None = None

    def reset(self, scenario_id: str, *, seed: int) -> Observation:
        del seed
        xy = self.scenarios[scenario_id]
        self._observation = Observation(scenario_id, xy)
        return self._observation

    def step(self, action: ShotAction) -> ShotResult:
        if self._observation is None:
            raise RuntimeError("Call reset() before step()")
        x, y = self._observation.features
        ideal_aim = 0.18 + 0.35 * y - 0.15 * x
        ideal_power = 0.55 + 0.23 * x - 0.11 * y
        # Deliberately invented objective. This does not model ball flight.
        distance_m = 45 * (action.aim - ideal_aim) ** 2 + 65 * (action.power - ideal_power) ** 2
        self._observation = None
        return ShotResult(distance_m=distance_m, holed_out=distance_m <= 0.15,
                          metadata={"source": "synthetic"})
