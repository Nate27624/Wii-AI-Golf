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
