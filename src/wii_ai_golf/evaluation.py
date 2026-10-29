"""Training and testing helpers: one shot per episode; ten-shot aggregates explicit."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean, median
from types import MemberDescriptorType
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



def _refuse_visible_dolphin_adapter(env: ShotEnvironment, *, purpose: str) -> None:
    """Refuse direct or transparently wrapped Dolphin adapters before any action.

    This checks ordinary instance attributes and native slot attributes in
    nested environment wrappers without calling their reset/step methods.
    Arbitrary opaque Python adapters or computed delegates are not verifiable
    by a generic ShotEnvironment interface; this is defense in depth, NOT a
    trust or authorization contract for real shots.
    """
    pending = [env]
    seen: set[int] = set()
    while pending:
        candidate = pending.pop()
        if id(candidate) in seen:
            continue
        seen.add(id(candidate))
        if len(seen) > 64:
            raise ValueError("Cannot validate deeply nested environment wrappers")
        if isinstance(candidate, DolphinEnvironment):
            raise ValueError(f"Dolphin {purpose} requires a verified real-shot outcome contract")

        try:
            children = list(vars(candidate).values())
        except TypeError:
            children = []
        # A transparent proxy may use __slots__ instead of __dict__. Read
        # only native slot descriptors, never arbitrary properties/getters.
        for owner in type(candidate).__mro__:
            slots = owner.__dict__.get("__slots__", ())
            if isinstance(slots, str):
                slots = (slots,)
            for slot in slots:
                descriptor = owner.__dict__.get(slot)
                if isinstance(descriptor, MemberDescriptorType):
                    try:
                        children.append(descriptor.__get__(candidate, type(candidate)))
                    except AttributeError:
                        pass
        for child in children:
            if isinstance(child, DolphinEnvironment) or (
                callable(getattr(type(child), "reset", None))
                and callable(getattr(type(child), "step", None))
            ):
                pending.append(child)


def train_elite_search(policy: EliteSearchPolicy, env: ShotEnvironment,
                       scenario_ids: Iterable[str], *, iterations: int = 800,
                       seed: int = 0) -> None:
    ids = tuple(scenario_ids)
    if not ids or iterations < 1:
        raise ValueError("Training needs scenarios and positive iterations")
    # No independently verified real-game action/outcome join exists. Refuse
    # the direct Dolphin adapter *before* reset, which can begin gameplay.
    _refuse_visible_dolphin_adapter(env, purpose="training")
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
    _refuse_visible_dolphin_adapter(env, purpose="evaluation")
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
