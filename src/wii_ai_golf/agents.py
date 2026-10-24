"""Framework-agnostic policy implementations and lightweight optimization baseline."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import random
import statistics
from typing import Protocol

from .protocol import Observation, ShotAction, ShotResult


class Policy(Protocol):
    def act(self, observation: Observation, *, explore: bool = False) -> ShotAction:
        ...


class RandomPolicy:
    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)

    def act(self, observation: Observation, *, explore: bool = False) -> ShotAction:
        del observation, explore
        return ShotAction(aim=self.rng.uniform(-1, 1), power=self.rng.random())


@dataclass
class _Estimate:
    aim: float = 0.0
    power: float = 0.5
    std_aim: float = 0.65
    std_power: float = 0.32


class EliteSearchPolicy:
    """Per-scenario elite sampling baseline, NOT a generalizing neural network.

    Explicitly keyed to observed scenario IDs. Unseen IDs use default estimates.
    """

    def __init__(self, seed: int = 0, elite_fraction: float = 0.2,
                 min_samples: int = 16) -> None:
        if not 0 < elite_fraction <= 1 or min_samples < 2:
            raise ValueError("invalid elite search settings")
        self.rng = random.Random(seed)
        self.elite_fraction = elite_fraction
        self.min_samples = min_samples
        self.history: dict[str, list[tuple[float, ShotAction]]] = defaultdict(list)
        self.estimates: dict[str, _Estimate] = {}

    def act(self, observation: Observation, *, explore: bool = False) -> ShotAction:
        p = self.estimates.get(observation.scenario_id, _Estimate())
        if not explore:
            return ShotAction(aim=p.aim, power=p.power)
        return ShotAction(
            aim=min(1.0, max(-1.0, self.rng.gauss(p.aim, p.std_aim))),
            power=min(1.0, max(0.0, self.rng.gauss(p.power, p.std_power))),
        )

    def observe(self, observation: Observation, action: ShotAction, result: ShotResult) -> None:
        samples = self.history[observation.scenario_id]
        samples.append((result.distance_m, action))
        if len(samples) < self.min_samples:
            return
        recent = samples[-160:]
        elite_count = max(2, int(len(recent) * self.elite_fraction))
        elite = sorted(recent, key=lambda x: x[0])[:elite_count]
        aims = [action.aim for _, action in elite]
        powers = [action.power for _, action in elite]
        self.estimates[observation.scenario_id] = _Estimate(
            aim=statistics.mean(aims),
            power=statistics.mean(powers),
            std_aim=max(0.04, min(0.65, statistics.pstdev(aims) * 1.4)),
            std_power=max(0.02, min(0.32, statistics.pstdev(powers) * 1.4)),
        )
