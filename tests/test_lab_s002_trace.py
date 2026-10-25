"""Golf Lab offline S002 trace integration contract."""
import unittest
from pathlib import Path
from wii_ai_golf.lab import core

class TraceLabIntegration(unittest.TestCase):
    def test_trace_is_registered_offline(self):
        studies={x["id"]:x for x in core.load_catalog()}
        self.assertEqual(studies["evaluation.trace"]["mode"],"offline")
        self.assertEqual(studies["evaluation.trace"]["owner"],"S002")
        self.assertEqual(studies["evaluation.minimap"]["mode"],"planned")
        self.assertEqual(studies["evaluation.landmarks"]["mode"],"planned")
    def test_planned_live_actions_cannot_be_executed(self):
        for x in ("evaluation.minimap","evaluation.landmarks"):
            with self.assertRaisesRegex(ValueError,"planned, NOT runnable"):
                core.plan(x)
    def test_trace_requires_input_and_never_launches_dolphin(self):
        with self.assertRaisesRegex(ValueError,"--input"):
            core.plan("evaluation.trace")
        result=core.plan("evaluation.trace",input_path="trace.jsonl",output_path="report.json")
        self.assertFalse(result.live)
        self.assertEqual(Path(result.command[1]).name,"analyze_focused_trace.py")
        self.assertIn("--input",result.command)
        self.assertIn("--output",result.command)
        self.assertNotIn("run_golf_experiment.py",result.command)
        self.assertEqual(result.summary()["game_outcome"],"not_observed_or_verified")
    def test_trace_rejects_live_flags(self):
        with self.assertRaises(ValueError):
            core.plan("evaluation.trace",input_path="x",a_prime=60)
if __name__=="__main__":unittest.main()
