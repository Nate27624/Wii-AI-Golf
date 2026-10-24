import unittest

from wii_ai_golf.agents import EliteSearchPolicy, RandomPolicy
from wii_ai_golf.evaluation import evaluate, train_elite_search
from wii_ai_golf.toy_env import TOY_SCENARIOS, ToyGolfEnvironment


class LearningTests(unittest.TestCase):
    def test_training_reduces_seen_scenario_loss(self):
        ids = tuple(TOY_SCENARIOS)[:6]
        before = evaluate(RandomPolicy(9), ToyGolfEnvironment(), ids, repeats=10)
        learner = EliteSearchPolicy(seed=9)
        train_elite_search(learner, ToyGolfEnvironment(), ids, iterations=1200, seed=9)
        after = evaluate(learner, ToyGolfEnvironment(), ids, repeats=10)
        self.assertLess(after.mean_distance_m, before.mean_distance_m)
        self.assertLess(after.mean_distance_m, 0.5)

    def test_held_out_id_is_not_training_id(self):
        ids = tuple(TOY_SCENARIOS)
        learner = EliteSearchPolicy(seed=1)
        train_elite_search(learner, ToyGolfEnvironment(), ids[:6], iterations=120, seed=1)
        self.assertNotIn(ids[6], learner.estimates)
        self.assertNotIn(ids[7], learner.estimates)
        metrics = evaluate(learner, ToyGolfEnvironment(), ids[6:])
        self.assertEqual(metrics.attempts, 2)

    def test_empty_split_raises(self):
        with self.assertRaises(ValueError):
            evaluate(RandomPolicy(), ToyGolfEnvironment(), [])
