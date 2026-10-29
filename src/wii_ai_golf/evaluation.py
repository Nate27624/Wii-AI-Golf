"""Training and testing helpers: one shot per episode; ten-shot aggregates explicit."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean, median
from typing import Iterable

from .agents import EliteSearchPolicy, Policy
from .emulator import DolphinEnvironment
from .protocol import ShotEnvironment


@dataclass(frozen=True)
class Evaluation:
    attempts: int
    mean_distance_m: float
    median_distance_m: float
    total_distance_m: float
    hole_outs: int
    per_scenario_mean_m: dict[str, float]

    def as_dict(self) -> dict:
        return asdict(self)


def train_elite_search(policy: EliteSearchPolicy, env: ShotEnvironment,
                       scenario_ids: Iterable[str], *, iterations: int = 800,
                       seed: int = 0) -> None:
    ids = tuple(scenario_ids)
    if not ids or iterations < 1:
        raise ValueError("Training needs scenarios and positive iterations")
    for i in range(iterations):
        observation = env.reset(ids[i % len(ids)], seed=seed + i)
        action = policy.act(observation, explore=True)
        result = env.step(action)
        policy.observe(observation, action, result)


def evaluate(policy: Policy, env: ShotEnvironment, scenario_ids: Iterable[str],
             *, repeats: int = 1, seed: int = 1234) -> Evaluation:
    ids = tuple(scenario_ids)
    if not ids or repeats < 1:
        raise ValueError("Evaluation needs scenarios and positive repeats")
    # No approved real-game result reader/shot-identity join exists yet. A
    # DolphinEnvironment.step() can issue an actual swing, so refuse it BEFORE
    # even resetting the bridge; a post-step eligibility check is too late.
    if isinstance(env, DolphinEnvironment):
        raise ValueError("Dolphin evaluation requires a verified real-shot outcome contract")
    distances: list[float] = []
    per_scenario: dict[str, list[float]] = {k: [] for k in ids}
    holes = 0
    for r in range(repeats):
        for j, scenario_id in enumerate(ids):
            observation = env.reset(scenario_id, seed=seed + r * len(ids) + j)
            result = env.step(policy.act(observation, explore=False))
            # Generic ShotEnvironment can also return arbitrary numerical
            # scores. Only explicitly synthetic results may reach these
            # legacy distance aggregates until a real eligibility gate exists.
            if result.metadata.get("source") != "synthetic":
                raise ValueError("Evaluation requires explicitly synthetic ShotResult data")
            distances.append(result.distance_m)
            per_scenario[scenario_id].append(result.distance_m)
            holes += int(result.holed_out)
    return Evaluation(
        attempts=len(distances),
        mean_distance_m=mean(distances),
        median_distance_m=median(distances),
        total_distance_m=sum(distances),
        hole_outs=holes,
        per_scenario_mean_m={k: mean(v) for k, v in per_scenario.items()},
    )
