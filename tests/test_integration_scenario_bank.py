import json
from pathlib import Path
import tempfile
import unittest

from wii_ai_golf.integration.savestates import StateCatalog, StateProfile
from wii_ai_golf.integration.scenario_bank import Scenario, ScenarioBank


class ScenarioCoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.catalog = StateCatalog(root / "states.json")
        for name, slot in (("tee1a", 20), ("tee1b", 21), ("tee2a", 22),
                           ("tee3a", 23), ("tee8a", 24), ("putt", 25)):
            self.catalog.add(StateProfile(name, slot))
        self.catalog.save()
        self.bank = ScenarioBank(root / "scenarios.json", self.catalog)
        for entry in (
            Scenario("green1a", "tee1a", "hitting-green", 1, "pin-a", {"wind":"unknown"}, True),
            Scenario("green1b", "tee1b", "hitting-green", 1, "pin-b", {"wind":"unknown"}, True),
            Scenario("green2a", "tee2a", "hitting-green", 2, "pin-a", {}, True),
            Scenario("green3a", "tee3a", "hitting-green", 3, "pin-a", {}, False),
            Scenario("green8a", "tee8a", "hitting-green", 8, "pin-a", {}, True),
        ):
            self.bank.add(entry)
        self.bank.save()

    def test_bank_roundtrip_and_requires_existing_profile(self):
        other = ScenarioBank(self.bank.path, StateCatalog(self.catalog.path))
        self.assertEqual(sorted(other.scenarios), sorted(self.bank.scenarios))
        with self.assertRaises(ValueError):
            other.add(Scenario("lost", "absent", "hitting-green", 4))
        with self.assertRaises(ValueError):
            other.add(Scenario("duplicate", "putt", "hitting-green", 1, "pin-b"))
        with self.assertRaises(ValueError):
            Scenario("bad", "putt", "hitting-green", True)

    def test_balanced_shot_groups_and_holdout_isolation(self):
        p = self.bank.plan(rounds=6, seed=42, balance="shot", holdout_shots=frozenset({8}))
        rows = p["attempts"]
        train = [x for x in rows if x["split"] == "train"]
        held = [x for x in rows if x["split"] == "holdout"]
        self.assertEqual(len(train), 12)  # 6 x shot indices 1 and 2
        self.assertEqual(len(held), 6)  # shot 8, no train leakage
        self.assertEqual({x["shot_index"] for x in train}, {1, 2})
        self.assertEqual({x["shot_index"] for x in held}, {8})
        self.assertEqual({x["scenario"] for x in train if x["shot_index"] == 1}, {"green1a", "green1b"})
        self.assertNotIn(3, p["seen_hitting_green_shots"])  # unverified scenario excluded
        self.assertIn(10, p["missing_hitting_green_shots"])
        self.assertEqual(p, self.bank.plan(rounds=6, seed=42, balance="shot", holdout_shots=frozenset({8})))

    def test_all_observed_profiles_per_round_option(self):
        p = self.bank.plan(rounds=2, seed=9, balance="scenario", verified_only=False)
        self.assertEqual(p["train_count"], 10)
        self.assertEqual(p["holdout_count"], 0)
        self.assertEqual(sorted(p["seen_hitting_green_shots"]), [1, 2, 3, 8])

    def test_refuses_unsupported_plans(self):
        with self.assertRaises(ValueError):
            self.bank.plan(rounds=0, seed=1)
        with self.assertRaises(ValueError):
            self.bank.plan(rounds=1, seed=1, holdout_shots=frozenset({10}))
        with self.assertRaises(ValueError):
            self.bank.plan(rounds=1, seed=1, holdout_shots=frozenset({1, 2, 8}))
        with self.assertRaises(ValueError):
            self.bank.plan(rounds=1, seed=1, balance="unknown")
        with self.assertRaises(ValueError):
            Scenario("x", "putt", "hitting-green", 1, conditions={"wind":4})


if __name__ == "__main__":
    unittest.main()
