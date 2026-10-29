"""S005 offline direct-learner reward boundary: no real Dolphin action or score."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.agents import EliteSearchPolicy
from wii_ai_golf.evaluation import train_elite_search
from wii_ai_golf.protocol import Observation, ShotAction, ShotResult
from wii_ai_golf.toy_env import ToyGolfEnvironment


class S005EliteDirectRewardGateTests(unittest.TestCase):
    def setUp(self):
        self.policy = EliteSearchPolicy(seed=11, min_samples=2)
        self.observation = Observation("toy-01", (0.1, 0.2))
        self.action = ShotAction(0.1, 0.6)

    def assert_refused_without_history(self, metadata):
        # A 100-foot off-green display is a censored *penalty*, not carry.
        # A bare numeric 30.48m result must never authorize direct training.
        result = ShotResult(30.48, False, metadata=metadata)
        with self.assertRaisesRegex(ValueError, "explicitly synthetic"):
            self.policy.observe(self.observation, self.action, result)
        self.assertEqual(dict(self.policy.history), {})
        self.assertEqual(self.policy.estimates, {})

    def test_human_offgreen_100foot_penalty_cannot_poison_history(self):
        self.assert_refused_without_history({
            "source": "human", "green": "no",
            "distance_label": "offgreen_100ft_penalty",
        })

    def test_unjoined_and_legacy_sources_cannot_poison_history(self):
        for metadata in (
            {},
            {"source": "visual_first", "kind": "test"},
            {"source": "legacy_v1", "run": "other", "shot": "other"},
            {"source": "dolphin", "shot": "missing-identity"},
        ):
            with self.subTest(metadata=metadata):
                self.assert_refused_without_history(metadata)

    def test_explicit_censor_flags_rejected_even_if_synthetic_labeled(self):
        # Training helper checks censoring too; direct policy calls must not
        # bypass that boundary by claiming source='synthetic'.
        for metadata in (
            {"source": "synthetic",
             "measurement_type": "offgreen_100ft_penalty"},
            {"source": "synthetic",
             "distance_label": "offgreen_100ft_penalty"},
            {"source": "synthetic", "censored": "TRUE"},
            {"source": "synthetic", "outcome_is_censored_penalty": "yes"},
        ):
            with self.subTest(metadata=metadata):
                with self.assertRaisesRegex(ValueError, "censored"):
                    self.policy.observe(
                        self.observation, self.action,
                        ShotResult(30.48, False, metadata=metadata),
                    )
                self.assertEqual(dict(self.policy.history), {})
                self.assertEqual(self.policy.estimates, {})

    def test_rejection_preserves_existing_synthetic_learning(self):
        first = ShotAction(-0.1, 0.4)
        second = ShotAction(0.2, 0.7)
        for action, distance in ((first, 0.9), (second, 0.1)):
            self.policy.observe(
                self.observation, action,
                ShotResult(distance, False, metadata={"source": "synthetic"}),
            )
        before_history = list(self.policy.history["toy-01"])
        before_estimate = self.policy.estimates["toy-01"]
        with self.assertRaisesRegex(ValueError, "explicitly synthetic"):
            self.policy.observe(
                self.observation, ShotAction(0.99, 0.99),
                ShotResult(0.0, True, metadata={"source": "human"}),
            )
        self.assertEqual(self.policy.history["toy-01"], before_history)
        self.assertEqual(self.policy.estimates["toy-01"], before_estimate)

    def test_toy_environment_training_still_updates_policy(self):
        train_elite_search(
            self.policy, ToyGolfEnvironment(), ["toy-01"],
            iterations=8, seed=123,
        )
        self.assertEqual(len(self.policy.history["toy-01"]), 8)
        self.assertIn("toy-01", self.policy.estimates)
        self.assertIsInstance(self.policy.act(self.observation), ShotAction)

    def test_valid_synthetic_distance_is_not_rejected_by_magic_constant(self):
        # A genuine synthetic toy-tagged numerical value can equal 100ft.
        # The caller-provided tag does NOT authenticate a real-game result.
        self.policy.observe(
            self.observation, self.action,
            ShotResult(30.48, False, metadata={"source": "synthetic"}),
        )
        self.assertEqual(self.policy.history["toy-01"], [(30.48, self.action)])


if __name__ == "__main__":
    unittest.main()
