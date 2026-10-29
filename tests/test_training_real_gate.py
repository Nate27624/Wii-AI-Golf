"""S004 offline training-helper eligibility tests: no live emulator is used."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.agents import EliteSearchPolicy
from wii_ai_golf.emulator import DolphinEnvironment
from wii_ai_golf.evaluation import train_elite_search
from wii_ai_golf.protocol import Observation, ShotAction, ShotResult
from wii_ai_golf.toy_env import ToyGolfEnvironment


class TrackingPolicy:
    def __init__(self):
        self.acts = 0
        self.observations = []

    def act(self, observation, *, explore=False):
        self.acts += 1
        return ShotAction(0.0, 0.5)

    def observe(self, observation, action, result):
        self.observations.append((observation, action, result))


class FakeResultEnvironment:
    def __init__(self, metadata=None, *, returned_id=None):
        self.metadata = metadata if metadata is not None else {"source": "synthetic"}
        self.returned_id = returned_id
        self.loads = 0
        self.steps = 0

    def reset(self, scenario_id, *, seed):
        self.loads += 1
        return Observation(self.returned_id or scenario_id, (0.2, 0.3))

    def step(self, action):
        self.steps += 1
        # 30.48 is the metric equivalent of 100 ft, NOT physical carry here.
        return ShotResult(30.48, False, metadata=self.metadata)


class TrainerPreactionGateTests(unittest.TestCase):
    def test_dolphin_adapter_refused_before_reset_or_any_swing(self):
        class FakeBridge:
            def __init__(self):
                self.loads = 0
                self.swings = 0
                self.reads = 0

            def load_scenario(self, scenario_id, seed):
                self.loads += 1
                return Observation(scenario_id, (0.2, 0.3))

            def perform_swing(self, action):
                self.swings += 1

            def read_final_result(self):
                self.reads += 1
                return ShotResult(30.48, False, {"source": "human"})

        bridge = FakeBridge()
        policy = TrackingPolicy()
        with self.assertRaisesRegex(ValueError, "verified real-shot"):
            train_elite_search(policy, DolphinEnvironment(bridge), ["real-01"], iterations=1)
        self.assertEqual((bridge.loads, bridge.swings, bridge.reads), (0, 0, 0))
        self.assertEqual((policy.acts, policy.observations), (0, []))

    def test_wrong_scenario_rejected_before_policy_action_or_step(self):
        env = FakeResultEnvironment(returned_id="other-scene")
        policy = TrackingPolicy()
        with self.assertRaisesRegex(ValueError, "scenario identity mismatch"):
            train_elite_search(policy, env, ["intended-scene"], iterations=1)
        self.assertEqual((env.loads, env.steps), (1, 0))
        self.assertEqual((policy.acts, policy.observations), (0, []))

    def test_unverified_human_legacy_and_test_results_never_train(self):
        records = (
            {},
            {"source": "human", "measurement_type": "offgreen_100ft_penalty"},
            {"source": "test", "kind": "test"},
            {"source": "legacy_v1", "run": "unjoined"},
        )
        for metadata in records:
            with self.subTest(metadata=metadata):
                env = FakeResultEnvironment(metadata)
                policy = TrackingPolicy()
                with self.assertRaisesRegex(ValueError, "explicitly synthetic"):
                    train_elite_search(policy, env, ["scenario"], iterations=1)
                self.assertEqual((env.loads, env.steps), (1, 1))
                self.assertEqual(policy.observations, [])

    def test_synthetic_label_cannot_override_explicit_censor_flag(self):
        for key in ("censored", "outcome_is_censored_penalty"):
            with self.subTest(key=key):
                env = FakeResultEnvironment({"source": "synthetic", key: "true"})
                policy = TrackingPolicy()
                with self.assertRaisesRegex(ValueError, "censored"):
                    train_elite_search(policy, env, ["scenario"], iterations=1)
                self.assertEqual(policy.observations, [])

    def test_synthetic_compatible_generic_environment_still_trains(self):
        env = FakeResultEnvironment({"source": "synthetic"})
        policy = TrackingPolicy()
        train_elite_search(policy, env, ["scenario"], iterations=3)
        self.assertEqual((env.loads, env.steps), (3, 3))
        self.assertEqual(len(policy.observations), 3)

    def test_existing_toy_elite_search_still_updates(self):
        policy = EliteSearchPolicy(seed=10)
        train_elite_search(policy, ToyGolfEnvironment(), ["toy-01"], iterations=24, seed=10)
        self.assertEqual(len(policy.history["toy-01"]), 24)
        self.assertIn("toy-01", policy.estimates)


if __name__ == "__main__":
    unittest.main()
