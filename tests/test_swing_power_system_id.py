import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src")]
from trial_swing_power import waveform,public_record
class CalibrationTests(unittest.TestCase):
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
        self.assertEqual(result["initial_club_pose_human"],"unknown")
        self.assertEqual(result["power_observation_source_human"],"unavailable")
    def test_observed_start_pose_and_power_source(self):
        result=public_record("baseline",waveform("baseline"),{},"yes",45.0,"back","meter")
        self.assertEqual(result["initial_club_pose_human"],"back")
        self.assertEqual(result["power_observation_source_human"],"meter")
if __name__=="__main__": unittest.main()
