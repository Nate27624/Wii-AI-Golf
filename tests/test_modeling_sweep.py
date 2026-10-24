import unittest
from wii_ai_golf.modeling.sweep import make_sweep
from wii_ai_golf.modeling.swing import SwingProfile,swing_trace,trace_hash

class SweepTests(unittest.TestCase):
    def test_recognition_balanced_deterministic(self):
        a=make_sweep(stage="recognition",scenarios=["at-ball"],seed=42)
        self.assertEqual(a,make_sweep(stage="recognition",scenarios=["at-ball"],seed=42))
        self.assertEqual(a["trial_count"],12)
        for rep in (1,2):
            self.assertEqual({x["profile"]["axis"] for x in a["trials"] if x["repetition"]==rep},
                             {"x+","x-","y+","y-","z+","z-"})

    def test_calibration_stays_on_confirmed_axis_and_fingerprints(self):
        p=make_sweep(stage="calibration",scenarios=["scene1","scene2"],confirmed_axis="z-",seed=7)
        self.assertEqual(p["trial_count"],122)
        for x in p["trials"]:
            self.assertEqual(x["profile"]["axis"],"z-")
            self.assertEqual(x["trace_sha256"],trace_hash(swing_trace(SwingProfile(**x["profile"]))))
            self.assertIsNone(x["outcome"])
        self.assertEqual({x["scenario_id"] for x in p["trials"]},{"scene1","scene2"})
        self.assertEqual(sum(x["phase"]=="reference" for x in p["trials"]),20)

    def test_invalid_gates(self):
        with self.assertRaises(ValueError):
            make_sweep(stage="calibration",scenarios=["s","s"],confirmed_axis="y+")
        with self.assertRaises(ValueError):
            make_sweep(stage="calibration",scenarios=["a","b"])
        with self.assertRaises(ValueError):
            make_sweep(stage="recognition",scenarios=["a","b"])
        with self.assertRaises(ValueError):
            make_sweep(stage="recognition",scenarios=["a"],seed=-1)
