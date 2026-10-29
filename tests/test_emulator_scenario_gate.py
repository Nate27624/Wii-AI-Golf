"""Offline S004 bridge-reset identity and stale-state safety regressions.

These tests use fabricated objects only; they do not launch Dolphin.
"""
from __future__ import annotations

import unittest

from wii_ai_golf.emulator import DolphinEnvironment
from wii_ai_golf.protocol import Observation, ShotAction, ShotResult


_DEFAULT = object()


class FakeBridge:
    def __init__(self):
        self.loads = []
        self.swings = []
        self.reads = 0
        self.next_observation = _DEFAULT
        self.fail_next_reset = False

    def load_scenario(self, scenario_id, seed):
        self.loads.append((scenario_id, seed))
        if self.fail_next_reset:
            self.fail_next_reset = False
            raise RuntimeError("synthetic reset failure")
        if self.next_observation is not _DEFAULT:
            return self.next_observation
        return Observation(scenario_id, (0.1, 0.2))

    def perform_swing(self, action):
        self.swings.append(action)

    def read_final_result(self):
        self.reads += 1
        return ShotResult(1.5, False, metadata={"source": "synthetic"})


class S004EmulatorScenarioGateTests(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.env = DolphinEnvironment(self.bridge)
        self.action = ShotAction(0.1, 0.5)

    def assert_cannot_swing(self):
        with self.assertRaisesRegex(RuntimeError, "reset"):
            self.env.step(self.action)
        self.assertEqual(self.bridge.swings, [])
        self.assertEqual(self.bridge.reads, 0)

    def test_matching_scenario_still_allows_exactly_one_step(self):
        obs = self.env.reset("first-ball", seed=42)
        self.assertEqual(obs.scenario_id, "first-ball")
        self.assertEqual(self.bridge.loads, [("first-ball", 42)])
        result = self.env.step(self.action)
        self.assertEqual(result.distance_m, 1.5)
        self.assertEqual(self.bridge.swings, [self.action])
        self.assertEqual(self.bridge.reads, 1)
        with self.assertRaisesRegex(RuntimeError, "reset"):
            self.env.step(self.action)
        self.assertEqual(self.bridge.swings, [self.action])

    def test_mismatched_scenario_rejected_before_swing(self):
        self.bridge.next_observation = Observation("wrong-ball", (0.1, 0.2))
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.env.reset("first-ball", seed=1)
        self.assert_cannot_swing()

    def test_non_observation_rejected_before_swing(self):
        for invalid in (None, {"scenario_id": "first-ball"}, "first-ball"):
            with self.subTest(value=invalid):
                self.bridge.next_observation = invalid
                with self.assertRaisesRegex(ValueError, "validated Observation"):
                    self.env.reset("first-ball", seed=1)
                self.assert_cannot_swing()

    def test_failed_later_reset_clears_previous_ready_state(self):
        self.env.reset("first-ball", seed=1)
        self.bridge.fail_next_reset = True
        with self.assertRaisesRegex(RuntimeError, "synthetic reset failure"):
            self.env.reset("second-ball", seed=2)
        self.assert_cannot_swing()

    def test_mismatched_later_reset_clears_previous_ready_state(self):
        self.env.reset("first-ball", seed=1)
        self.bridge.next_observation = Observation("first-ball", (0.1, 0.2))
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.env.reset("second-ball", seed=2)
        self.assert_cannot_swing()


if __name__ == "__main__":
    unittest.main()
