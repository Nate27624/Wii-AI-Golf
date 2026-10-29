"""Synthetic and unit checks; these never assert real golf-game performance."""
import unittest
import importlib.util
import math

from wii_ai_golf.bayes import BayesianSearchPolicy, RandomBestPolicy
from wii_ai_golf.protocol import Observation, ShotAction, ShotResult
from wii_ai_golf.toy_env import ToyGolfEnvironment
from scripts.benchmark_bayes import benchmark

HAVE_NUMPY = importlib.util.find_spec("numpy") is not None


@unittest.skipUnless(HAVE_NUMPY, "install optional extra: pip install -e '.[bayes]'")
class BayesianTests(unittest.TestCase):
    def test_untrained_fallback_and_bounds(self):
        policy = BayesianSearchPolicy(seed=3, initial_random=4, candidate_count=16)
        observation = Observation("shot-1", (.1, .2))
        self.assertEqual(policy.act(observation), ShotAction(0, .5))
        for _ in range(12):
            action = policy.act(observation, explore=True)
            self.assertTrue(-1 <= action.aim <= 1)
            self.assertTrue(0 <= action.power <= 1)
            policy.observe(observation, action, ShotResult(abs(action.aim) + abs(action.power - .4), False))
        self.assertEqual(len(policy.history["shot-1"]), 12)

    def test_best_observed_is_frozen_and_isolated_by_id(self):
        policy = BayesianSearchPolicy(seed=42, initial_random=3, candidate_count=16)
        a, b = Observation("one", (.5,)), Observation("two", (.3,))
        good = ShotAction(.2, .7)
        policy.observe(a, ShotAction(-.5, .4), ShotResult(3, False))
        policy.observe(a, good, ShotResult(.02, True))
        self.assertEqual(policy.act(a), good)
        self.assertEqual(policy.act(b), ShotAction(0, .5))
        self.assertNotIn("two", policy.history)

    def test_reproducible_actions_after_updates(self):
        a = Observation("one", (.5,))
        policies = [BayesianSearchPolicy(seed=19, initial_random=3, candidate_count=20) for _ in range(2)]
        for _ in range(10):
            moves = [p.act(a, explore=True) for p in policies]
            self.assertEqual(moves[0], moves[1])
            for policy, move in zip(policies, moves):
                policy.observe(a, move, ShotResult(move.aim ** 2 + (move.power - .67) ** 2, False))

    def test_repeated_actions_are_numerically_stable(self):
        policy = BayesianSearchPolicy(seed=1, initial_random=3, candidate_count=16)
        state = Observation("repeat", (.1,))
        for _ in range(8):
            policy.observe(state, ShotAction(.0, .5), ShotResult(2.0, False))
        proposed = policy.act(state, explore=True)
        self.assertIsInstance(proposed, ShotAction)
        self.assertNotEqual(proposed, ShotAction(.0, .5))

    def test_capped_history_does_not_repeat_archived_best_action(self):
        # The GP fits only the most recent 2 points, but the proposal must
        # avoid ALL previously sampled actions, including the old incumbent.
        policy = BayesianSearchPolicy(seed=9, initial_random=2,
                                      candidate_count=8, max_fit_samples=2)
        state = Observation("capped-constant-targets", (.1,))
        archived_best = ShotAction(-1.0, 0.0)
        recent_duplicate = ShotAction(1.0, 1.0)
        policy.observe(state, archived_best, ShotResult(0.0, False))
        for _ in range(2):
            policy.observe(state, recent_duplicate, ShotResult(10.0, False))
        self.assertEqual(policy.act(state), archived_best)
        # Force the global incumbent into the proposal pool, so this
        # regression cannot pass by luck from random candidate selection.
        policy._random_action = lambda: archived_best
        suggested = policy.act(state, explore=True)
        self.assertNotEqual(suggested, archived_best)
        self.assertNotEqual(suggested, recent_duplicate)
        self.assertTrue(-1.0 <= suggested.aim <= 1.0)
        self.assertTrue(0.0 <= suggested.power <= 1.0)

    def test_zero_variance_targets_at_distinct_actions_stay_finite(self):
        policy = BayesianSearchPolicy(seed=13, initial_random=2,
                                      candidate_count=16, max_fit_samples=3)
        state = Observation("constant", (.1,))
        measured_actions = (ShotAction(-0.8, 0.2), ShotAction(0.1, 0.5),
                            ShotAction(0.8, 0.9))
        for action in measured_actions:
            policy.observe(state, action, ShotResult(5.0, False))
        proposed = policy.act(state, explore=True)
        self.assertTrue(math.isfinite(proposed.aim))
        self.assertTrue(math.isfinite(proposed.power))
        self.assertNotIn(proposed, measured_actions)

    def test_synthetic_learning_reduces_loss(self):
        policy = BayesianSearchPolicy(seed=2, initial_random=4, candidate_count=96)
        env = ToyGolfEnvironment()
        observation = env.reset("toy-01", seed=42)
        initial_loss = env.step(policy.act(observation)).distance_m
        for i in range(28):
            obs = env.reset("toy-01", seed=42 + i)
            action = policy.act(obs, explore=True)
            policy.observe(obs, action, env.step(action))
        obs = env.reset("toy-01", seed=444)
        after = env.step(policy.act(obs)).distance_m
        self.assertLess(after, initial_loss)
        self.assertLess(after, 1.0)

    def test_benchmark_budget_and_no_generalization_claim(self):
        output = benchmark(seed=7, attempts_per_scenario=8, repeats=2)
        for record in output["results"].values():
            self.assertEqual(record["training_attempts"], 64)
            self.assertEqual(record["evaluation_attempts"], 16)
        self.assertIn("NOT unseen-scenario", output["evaluation_note"])

    def test_bad_config_rejected(self):
        for kwargs in ({"initial_random": 1}, {"candidate_count": 0},
                       {"length_scale": 0}, {"observation_noise": -1},
                       {"max_fit_samples": 3}):
            with self.assertRaises(ValueError):
                BayesianSearchPolicy(**{"initial_random": 6, **kwargs})


if __name__ == "__main__":
    unittest.main()
