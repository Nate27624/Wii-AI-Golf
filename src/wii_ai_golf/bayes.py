"""Per-scenario Bayesian optimization for Hitting the Green shot parameters.

Uses a Gaussian-process RBF surrogate and expected improvement to *minimize*
final distance. This is not a Wii Remote control implementation: aim/power are
unverified normalized placeholders until the real Dolphin action map is calibrated.

Only fitting samples from the same scenario ID are used. No unseen-scenario
transfer, course physics, or live game scoring is claimed.
"""
from __future__ import annotations

from collections import defaultdict
import math
import random

try:
    import numpy as np
except ImportError:  # Keep other policies usable without the optional extra.
    np = None

from .protocol import Observation, ShotAction, ShotResult


def _encode(action: ShotAction) -> tuple[float, float]:
    """Map declared action bounds to [0, 1]^2 for the GP kernel."""
    return ((action.aim + 1.0) / 2.0, action.power)


class BayesianSearchPolicy:
    """Finite candidate expected-improvement optimizer, independent per scenario.

    act(explore=True) proposes one experiment; call observe with the
    measured result before proposing another. act(explore=False) freezes
    exploration and replays the best *observed* action for that scenario.
    """

    def __init__(self, *, seed: int = 0, initial_random: int = 6,
                 candidate_count: int = 192, length_scale: float = 0.22,
                 observation_noise: float = 1e-4, max_fit_samples: int = 128) -> None:
        if np is None:
            raise ImportError('BayesianSearchPolicy needs NumPy: pip install -e ".[bayes]"')
        if initial_random < 2 or candidate_count < 8 or max_fit_samples < initial_random:
            raise ValueError("invalid Bayesian search budget")
        if not math.isfinite(length_scale) or length_scale <= 0:
            raise ValueError("length_scale must be positive and finite")
        if not math.isfinite(observation_noise) or observation_noise <= 0:
            raise ValueError("observation_noise must be positive and finite")
        self.rng = random.Random(seed)
        self.initial_random = initial_random
        self.candidate_count = candidate_count
        self.length_scale = length_scale
        self.observation_noise = observation_noise
        self.max_fit_samples = max_fit_samples
        self.history: dict[str, list[tuple[ShotAction, float]]] = defaultdict(list)

    def _random_action(self) -> ShotAction:
        return ShotAction(self.rng.uniform(-1.0, 1.0), self.rng.random())

    def act(self, observation: Observation, *, explore: bool = False) -> ShotAction:
        trials = self.history.get(observation.scenario_id, ())
        if not explore:
            if not trials:
                return ShotAction(0.0, 0.5)  # Explicit untrained fallback.
            return min(trials, key=lambda trial: trial[1])[0]
        if len(trials) < self.initial_random:
            return self._random_action()

        recent = trials[-self.max_fit_samples:]
        x = np.asarray([_encode(a) for a, _ in recent], dtype=float)
        y = np.asarray([d for _, d in recent], dtype=float)
        mean_y = float(y.mean())
        scale_y = max(float(y.std()), 1e-6)
        targets = (y - mean_y) / scale_y
        sq = np.sum(((x[:, None, :] - x[None, :, :]) / self.length_scale) ** 2, axis=2)
        kernel = np.exp(-0.5 * sq)
        # Add nugget for noisy measurements, repeated actions and round-off.
        ident = np.eye(len(x))
        chol = None
        for extra_jitter in (1e-10, 1e-8, 1e-6, 1e-4):
            try:
                chol = np.linalg.cholesky(kernel + (self.observation_noise + extra_jitter) * ident)
                break
            except np.linalg.LinAlgError:
                continue
        if chol is None:
            # A singular model must not stop actual experiment collection.
            return self._random_action()
        alpha = np.linalg.solve(chol.T, np.linalg.solve(chol, targets))

        best = min(trials, key=lambda sample: sample[1])[0]
        best_xy = _encode(best)
        candidates = [(_encode(self._random_action())) for _ in range(self.candidate_count)]
        # Include local exploitation and a few known boundaries. Avoid fitting
        # only the central mass of uniform random candidates.
        for _ in range(self.candidate_count // 2):
            candidates.append((min(1., max(0., self.rng.gauss(best_xy[0], 0.10))),
                               min(1., max(0., self.rng.gauss(best_xy[1], 0.10)))))
        candidates.extend(((0., 0.), (0., 1.), (1., 0.), (1., 1.), (.5, .5)))
        query = np.asarray(candidates, dtype=float)
        q_sq = np.sum(((query[:, None, :] - x[None, :, :]) / self.length_scale) ** 2, axis=2)
        k = np.exp(-0.5 * q_sq)
        mu = k @ alpha
        v = np.linalg.solve(chol, k.T)
        std = np.sqrt(np.maximum(1e-12, 1.0 - np.sum(v * v, axis=0)))
        incumbent = (min(d for _, d in trials) - mean_y) / scale_y
        improvement = incumbent - mu
        z = improvement / std
        # Standard normal CDF/PDF without requiring SciPy.
        cdf = np.asarray([0.5 * (1.0 + math.erf(float(t) / math.sqrt(2.0))) for t in z])
        pdf = np.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
        expected_improvement = improvement * cdf + std * pdf
        # The surrogate fits recent trials, but duplicate protection must
        # cover the full scenario history, including older capped-out actions.
        # Check in chunks to avoid allocating an unbounded query-by-history array.
        already = np.zeros(len(query), dtype=bool)
        for offset in range(0, len(trials), 256):
            observed = np.asarray([_encode(a) for a, _ in trials[offset:offset + 256]],
                                  dtype=float)
            distance_sq = np.sum((query[:, None, :] - observed[None, :, :]) ** 2,
                                 axis=2)
            already |= np.any(distance_sq < 1e-10, axis=1)
        expected_improvement[already] = -1.0
        selected = query[int(np.argmax(expected_improvement))]
        return ShotAction(float(2.0 * selected[0] - 1.0), float(selected[1]))

    def observe(self, observation: Observation, action: ShotAction, result: ShotResult) -> None:
        """Store the actual outcome; the caller manages resets and failed shots."""
        self.history[observation.scenario_id].append((action, result.distance_m))


class RandomBestPolicy:
    """Fair black-box comparator: sample randomly, deploy best observed input."""

    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)
        self.history: dict[str, list[tuple[ShotAction, float]]] = defaultdict(list)

    def act(self, observation: Observation, *, explore: bool = False) -> ShotAction:
        trials = self.history.get(observation.scenario_id, ())
        if not explore:
            return min(trials, key=lambda t: t[1])[0] if trials else ShotAction(0.0, 0.5)
        return ShotAction(self.rng.uniform(-1.0, 1.0), self.rng.random())

    def observe(self, observation: Observation, action: ShotAction, result: ShotResult) -> None:
        self.history[observation.scenario_id].append((action, result.distance_m))
