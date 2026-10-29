"""S005 offline refusal tests: toy data is not a real Dolphin score."""
from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.agents import RandomPolicy
from wii_ai_golf.emulator import DolphinEnvironment
from wii_ai_golf.evaluation import evaluate
from wii_ai_golf.protocol import Observation, ShotResult
from wii_ai_golf.toy_env import ToyGolfEnvironment


class S005EvaluationEvidenceGateTests(unittest.TestCase):
    def test_toy_evaluation_remains_allowed_and_explicitly_synthetic(self):
        result = evaluate(RandomPolicy(1), ToyGolfEnvironment(), ["toy-01"], repeats=2)
        self.assertEqual(result.attempts, 2)
        self.assertGreaterEqual(result.mean_distance_m, 0)

    def test_duplicate_scenario_ids_refused_before_any_reset(self):
        class CountingToy(ToyGolfEnvironment):
            def __init__(self):
                super().__init__()
                self.reset_calls = 0
                self.step_calls = 0

            def reset(self, scenario_id, *, seed):
                self.reset_calls += 1
                return super().reset(scenario_id, seed=seed)

            def step(self, action):
                self.step_calls += 1
                return super().step(action)

        env = CountingToy()
        with self.assertRaisesRegex(ValueError, "must be unique"):
            evaluate(RandomPolicy(5), env, ["toy-01", "toy-01"], repeats=2)
        self.assertEqual((env.reset_calls, env.step_calls), (0, 0))
        # Legitimate distinct holdout IDs still receive equal attempt counts.
        metrics = evaluate(RandomPolicy(5), env, ["toy-01", "toy-02"], repeats=2)
        self.assertEqual(metrics.attempts, 4)
        self.assertEqual(set(metrics.per_scenario_mean_m), {"toy-01", "toy-02"})

    def test_wrong_reset_scenario_refused_before_step_or_policy_action(self):
        class MislabeledToy:
            def __init__(self):
                self.reset_calls = 0
                self.step_calls = 0

            def reset(self, scenario_id, *, seed):
                self.reset_calls += 1
                # A valid-looking, fully synthetic observation, but for a
                # different scenario than the requested heldout group.
                return Observation("toy-02", (0.5, 0.8))

            def step(self, action):
                self.step_calls += 1
                return ShotResult(0.0, True, metadata={"source": "synthetic"})

        class NoActPolicy:
            def act(self, observation, *, explore=False):
                raise AssertionError("policy must not act on wrong scenario")

        env = MislabeledToy()
        with self.assertRaisesRegex(ValueError, "scenario identity mismatch"):
            evaluate(NoActPolicy(), env, ["toy-01"], repeats=1)
        self.assertEqual(env.reset_calls, 1)
        self.assertEqual(env.step_calls, 0)

    def test_unverified_dolphin_bridge_never_even_resets_or_swings(self):
        class FakeDolphinBridge:
            def __init__(self):
                self.loads = 0
                self.swings = 0
                self.reads = 0

            def load_scenario(self, scenario_id, seed):
                self.loads += 1
                return Observation(scenario_id, (.2, .3))

            def perform_swing(self, action):
                self.swings += 1

            def read_final_result(self):
                self.reads += 1
                # A displayed 100ft off-green penalty is not physical carry.
                return ShotResult(30.48, False, metadata={"source": "human",
                                                           "green": "no"})

        bridge = FakeDolphinBridge()
        with self.assertRaisesRegex(ValueError, "verified real-shot"):
            evaluate(RandomPolicy(2), DolphinEnvironment(bridge), ["first_ball"])
        self.assertEqual((bridge.loads, bridge.swings, bridge.reads), (0, 0, 0))

    def test_generic_environment_cannot_aggregate_unjoined_or_test_receipts(self):
        class UnverifiedEnvironment:
            def __init__(self, metadata):
                self.metadata = metadata

            def reset(self, scenario_id, *, seed):
                return Observation(scenario_id, (1.0,))

            def step(self, action):
                return ShotResult(30.48, False, metadata=self.metadata)

        for metadata in ({}, {"source": "human", "green": "no"},
                         {"source": "visual_first", "kind": "test"},
                         {"source": "legacy_v1", "run": "other", "shot": "other"}):
            with self.subTest(metadata=metadata):
                with self.assertRaisesRegex(ValueError, "explicitly synthetic"):
                    evaluate(RandomPolicy(3), UnverifiedEnvironment(metadata), ["holdout"])

    def test_real_source_must_not_be_misclassified_as_synthetic(self):
        class UnverifiedEnvironment:
            def reset(self, scenario_id, *, seed):
                return Observation(scenario_id, (1.0,))

            def step(self, action):
                return ShotResult(0.0, True, metadata={"source": "dolphin"})

        with self.assertRaisesRegex(ValueError, "explicitly synthetic"):
            evaluate(RandomPolicy(4), UnverifiedEnvironment(), ["seen"])


if __name__ == "__main__":
    unittest.main()
