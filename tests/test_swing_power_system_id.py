import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src")]
from trial_swing_power import waveform,public_record
class CalibrationTests(unittest.TestCase):
    def test_power_trial_requires_separate_a_prehold(self):
        import inspect
        import trial_swing_power
        src=inspect.getsource(trial_swing_power.main)
        self.assertIn("prime_a_button(rpc,remote=0,requests=60)",src)
        self.assertIn("release_buttons(rpc,remote=0)",src)
        self.assertIn("trace.swing_capabilities",src)

    def test_single_variable_only(self):
        original=waveform("baseline")
        for variant in ("shorter","slower","faster","longer-backswing"):
            trace=waveform(variant)
            self.assertEqual(len(trace),len(original))
            self.assertEqual([s.hold_a for s in trace],[s.hold_a for s in original])
            self.assertEqual([s.direction for s in trace],[s.direction for s in original])
            diff=[i for i,(a,b) in enumerate(zip(original,trace)) if a!=b]
            self.assertTrue(diff)
            allowed=range(12,27) if variant=="longer-backswing" else range(27,47)
            self.assertTrue(all(i in allowed for i in diff))
    def test_no_inferred_power_or_contact(self):
        trace=waveform("baseline")
        result=public_record("baseline",trace,{"state":"done"},"unknown",None)
        self.assertIsNone(result["power_percent_human"])
        self.assertFalse(result["power_verified_by_memory"])
        self.assertFalse(result["contact_verified_by_memory"])
if __name__=="__main__": unittest.main()
