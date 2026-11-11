"""Offline multi-run memory cohort aggregation tests."""
import sys,unittest,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]
from analyze_golf_memory_cohort import summarize_cohort

def report(items):
    return {"kind":"golf-memory-phase-differential","scope":"broad",
            "top_changed_relative_words":[
                {"region":region,"relative_offset":offset,
                 "within_phase_changes":within,"at_phase_boundary_changes":boundary}
                for region,offset,within,boundary in items]}
class CohortTests(unittest.TestCase):
    def test_recurrence_only_and_no_raw_values(self):
        a=report([("minimap_ball_effect","+0x1EC",1,2),
                  ("minimap_player_effect","+0x7C",0,1)])
        b=report([("minimap_ball_effect","+0x1EC",0,2),
                  ("golf_config","+0x9C",1,0)])
        result=summarize_cohort([a,b],"cohort-test")
        self.assertEqual(result["shared_changed_words_all_runs"],1)
        self.assertEqual(result["recurrent_changed_words_2plus_runs"],1)
        self.assertEqual(result["distinct_changed_words"],3)
        self.assertEqual(result["recurrent_words"][0]["relative_offset"],"+0x1EC")
        self.assertEqual(result["recurrent_words"][0]["runs_changed"],2)
        self.assertEqual(result["recurrent_words"][0]["runs_within_phase"],1)
        self.assertEqual(result["recurrent_words"][0]["boundary_events"],4)
        s=json.dumps(result)
        self.assertNotIn("bytes_hex",s)
        self.assertNotIn("address",s)
        self.assertNotIn("private",s.lower())
    def test_reject_one_run(self):
        with self.assertRaises(ValueError):summarize_cohort([report([])],"x")
    def test_reject_duplicates_in_one_run(self):
        a=report([("golf_config","+0x94",1,0),("golf_config","+0x94",1,0)])
        with self.assertRaises(ValueError):summarize_cohort([a,report([])],"x")
if __name__=="__main__":unittest.main()
