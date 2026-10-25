"""Offline tests for controlled S002 motion scales."""
import sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]
from collect_outcome_transition import run_session

class PowerProbeTests(unittest.TestCase):
    def test_reject_unregistered_scale_before_any_capture(self):
        with self.assertRaisesRegex(ValueError,"motion scale"):
            run_session(None,raw_path=Path("unused.jsonl"),pre_samples=2,
                        post_samples=2,settled_samples=2,interval=0,
                        motion_scale=9.0)
    def test_reject_unregistered_scale_even_for_manual_input(self):
        with self.assertRaises(ValueError):
            run_session(None,raw_path=Path("unused.jsonl"),pre_samples=2,
                        post_samples=2,settled_samples=2,interval=0,
                        motion_scale=0.75)
if __name__=="__main__":unittest.main()
