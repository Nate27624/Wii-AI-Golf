"""Map object controls remain distinct from actual physics-ball observations."""
import unittest
from unittest.mock import patch
from wii_ai_golf.landmark_control import observe_landmarks,summarize_landmarks

class FakeRPC:
    def __init__(self):
        self.calls=[]
    def call(self,method,args=None):
        self.calls.append((method,args))
        if method=="frame.get_count":return 100+sum(c[0]==method for c in self.calls)
        if method=="memory.read_u32":
            addr=args[0]
            return {0x804BF868:0x91000000,0x91000044:0x91000100,
                    0x91000050:0x91000200,0x91000054:0}.get(addr,0)
        if method=="memory.read_bytes":
            import struct
            return struct.pack(">fff",1.,2.,3.).hex()
        raise AssertionError(method)

class LandmarkTests(unittest.TestCase):
    @patch("wii_ai_golf.landmark_control.preflight",return_value=0x91000000)
    def test_source_offsets_and_no_ball_label(self,preflight):
        rpc=FakeRPC()
        row=observe_landmarks(rpc)
        self.assertEqual(row["landmarks"]["pin"],[1.,2.,3.])
        self.assertEqual(row["landmarks"]["start"],[1.,2.,3.])
        self.assertIsNone(row["landmarks"]["cup"])
        self.assertEqual(row["frame_span"],1)
        self.assertFalse(any("0x91000004" in str(c) for c in rpc.calls))
    def test_gap_is_not_movement(self):
        def row(x):return {"landmarks":{"pin":x,"start":None,"cup":None}}
        out=summarize_landmarks([row([0,0,0]),row(None),row([100,0,0]),row([101,0,0])])
        self.assertEqual(out["landmarks"]["pin"]["moving_steps"],1)
        self.assertEqual(out["landmarks"]["pin"]["present"],3)
        self.assertIn("NOT_BALL",out["claim"])
if __name__=="__main__":unittest.main()
