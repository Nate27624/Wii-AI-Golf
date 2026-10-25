"""Offline trace segmentation guards and no invented shot labels."""
import json
from pathlib import Path
import tempfile
import unittest
from wii_ai_golf.evaluation.focused_trace import analyze_trace

class TraceTests(unittest.TestCase):
    def test_two_motion_segments_and_reset_are_not_three_swings(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"capture.jsonl"
            rows=[
                {"elapsed_s":0,"frame_start":0,"object_base":"0x90000000","xyz":[0.,0.,0.]},
                {"elapsed_s":1,"frame_start":10,"object_base":"0x90000000","xyz":[1.,0.,0.]},
                {"elapsed_s":2,"frame_start":20,"object_base":"0x90000000","xyz":[2.,0.,0.]},
                {"elapsed_s":3,"frame_start":30,"object_base":"0x90000000","xyz":[102.,0.,0.]},
                {"elapsed_s":4,"frame_start":40,"object_base":"0x90000000","xyz":[103.,0.,0.]},
                {"elapsed_s":5,"frame_start":50,"object_base":"0x90000000","xyz":[103.,0.,0.]},
                {"elapsed_s":6,"frame_start":60,"object_base":"0x90000000","xyz":None},
            ]
            p.write_text("\n".join(json.dumps(x) for x in rows)+"\n")
            result=analyze_trace(p)
            self.assertEqual(result["moving_steps_below_reset"],3)
            self.assertEqual(len(result["motion_episodes"]),2)
            self.assertEqual(len(result["discontinuities"]),1)
            self.assertEqual(result["null_or_invalid_pointer_samples"],1)
            self.assertNotIn("shot_count",result)
            self.assertNotIn("0x90000000",json.dumps(result))

    def test_bad_rows_counted_not_silent(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"x.jsonl"
            p.write_text("not json\n"+json.dumps({"elapsed_s":0,"frame_start":0,"xyz":[1,2,float("nan")],"object_base":"x"})+"\n")
            self.assertEqual(analyze_trace(p)["malformed_rows"],2)

    def test_invalid_config(self):
        with self.assertRaises(ValueError):
            analyze_trace("unused.jsonl",motion_threshold=2,reset_threshold=1)
if __name__=="__main__":
    unittest.main()
