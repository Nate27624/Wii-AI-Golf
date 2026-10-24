import unittest

from wii_ai_golf.protocol import Observation, ShotAction, ShotResult
from wii_ai_golf.emulator import DolphinEnvironment
from wii_ai_golf.toy_env import ToyGolfEnvironment


class ProtocolTests(unittest.TestCase):
    def test_invalid_action(self):
        for aim, power in ((1.01, .5), (0, -0.1), (float('nan'), .3)):
            with self.assertRaises(ValueError):
                ShotAction(aim, power)

    def test_invalid_observation(self):
        with self.assertRaises(ValueError):
            Observation("", (1.0,))

    def test_invalid_distance(self):
        with self.assertRaises(ValueError):
            ShotResult(-1, False)

    def test_toy_requires_reset(self):
        env = ToyGolfEnvironment()
        with self.assertRaises(RuntimeError):
            env.step(ShotAction(0, .5))
        env.reset("toy-01", seed=12)
        res = env.step(ShotAction(0, .5))
        self.assertGreaterEqual(res.distance_m, 0)
        with self.assertRaises(RuntimeError):
            env.step(ShotAction(0, .5))

    def test_bridge_adapter(self):
        class FakeBridge:
            def __init__(self):
                self.called = False
            def load_scenario(self, scenario_id, seed):
                return Observation(scenario_id, (.4, .3))
            def perform_swing(self, action):
                self.called = True
            def read_final_result(self):
                return ShotResult(1.3, False)
        bridge = FakeBridge()
        env = DolphinEnvironment(bridge)
        with self.assertRaises(RuntimeError):
            env.step(ShotAction(0, .5))
        env.reset("test", seed=1)
        result = env.step(ShotAction(0, .5))
        self.assertTrue(bridge.called)
        self.assertEqual(result.distance_m, 1.3)
