"""S002 actions must coexist with current V1/auto-sync Lab UI."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from wii_ai_golf.lab.core import plan,available_experiments

class CurrentLabS002Tests(unittest.TestCase):
    def test_latest_v1_survives(self):
        registry={x["id"]:x for x in available_experiments()}
        self.assertIn("integration.v1-diagnostic",registry)
    def test_three_live_actions_are_typed(self):
        for name,study in [("evaluation.landmarks","landmarks"),
                           ("evaluation.minimap","minimap_camera"),
                           ("evaluation.minimap-swing","minimap_swing")]:
            with self.subTest(name=name):
                p=plan(name)
                self.assertTrue(p.live)
                self.assertEqual(Path(p.command[1]).name,"run_s002_lab_capture.py")
                self.assertEqual(p.command[-1],study)
                self.assertEqual(p.command[-2],"--study")
    def test_latest_test_discovery_kept(self):
        registry={x["id"]:x for x in available_experiments()}
        self.assertTrue(any(name.startswith("agent-tests.") for name in registry))
    def test_unsafe_a_prime_rejected(self):
        with self.assertRaises(ValueError):plan("evaluation.minimap",a_prime=30)
if __name__=="__main__":unittest.main()
