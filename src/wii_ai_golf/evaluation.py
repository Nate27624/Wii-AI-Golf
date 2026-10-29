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
    # No independently verified real-game action/outcome join exists. Refuse
    # the direct Dolphin adapter *before* reset, which can begin gameplay.
    if isinstance(env, DolphinEnvironment):
        raise ValueError("Dolphin training requires a verified real-shot outcome contract")
    for i in range(iterations):
        scenario_id = ids[i % len(ids)]
        observation = env.reset(scenario_id, seed=seed + i)
        if observation.scenario_id != scenario_id:
            raise ValueError("Training reset scenario identity mismatch")
        action = policy.act(observation, explore=True)
        result = env.step(action)
        # The legacy trainer may only fit its explicitly synthetic objective.
        # Caller-controlled metadata is NOT verified real-game provenance.
        if result.metadata.get("source") != "synthetic":
            raise ValueError("Training requires explicitly synthetic ShotResult data")
        if (result.metadata.get("measurement_type") == "offgreen_100ft_penalty"
                or any(str(result.metadata.get(key, "")).strip().lower()
                       in ("1", "true", "yes")
                       for key in ("censored", "outcome_is_censored_penalty"))):
            raise ValueError("Training rejects censored ShotResult penalties")
        policy.observe(observation, action, result)


def evaluate(policy: Policy, env: ShotEnvironment, scenario_ids: Iterable[str],
             *, repeats: int = 1, seed: int = 1234) -> Evaluation:
    ids = tuple(scenario_ids)
    if not ids or repeats < 1:
        raise ValueError("Evaluation needs scenarios and positive repeats")
    # Repeating a configuration within the ID list silently biases the
    # global mean toward it while collapsing per_scenario_mean_m keys.
    if len(set(ids)) != len(ids):
        raise ValueError("Evaluation scenario IDs must be unique")
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
            # A generic environment may return another scenario: do not
            # attribute that observation/result to the requested holdout ID.
            if observation.scenario_id != scenario_id:
                raise ValueError("Evaluation reset scenario identity mismatch")
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
