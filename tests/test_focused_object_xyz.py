"""Focused leading XYZ offset is read-only and pointer validated every sample."""
import struct,unittest
from unittest.mock import patch
from wii_ai_golf.focused_object_xyz import preflight,observe,summarize

class Bridge:
    def __init__(self,ptr=0x92583488):
        self.ptr=ptr;self.calls=[];self.count=100
    def call(self,method,params=None):
        self.calls.append((method,params))
        if method=="frame.get_count":
            self.count+=1
            return self.count
        if method=="memory.read_u32":return self.ptr
        if method=="memory.read_bytes":
            self.asserted=params
            return struct.pack(">fff",5.,10.,15.).hex()
        raise AssertionError(method)

class FocusedTests(unittest.TestCase):
    def test_revision_gate(self):
        with patch("wii_ai_golf.focused_object_xyz.probe_rev1",
                   return_value={"supported":False}):
            with self.assertRaises(RuntimeError):preflight(Bridge())
    def test_read_only_follow_one_pointer_offset(self):
        rpc=Bridge()
        row=observe(rpc,0x91BF4590)
        self.assertEqual(rpc.calls[1],("memory.read_u32",[0x91BF4594]))
        self.assertEqual(rpc.asserted,[0x925834D8,12])
        self.assertEqual(row["xyz"],[5.,10.,15.])
        self.assertEqual(row["frame_span"],1)
        self.assertTrue(all(n in ("frame.get_count","memory.read_u32","memory.read_bytes") for n,_ in rpc.calls))
    def test_invalid_pointer_never_dereferenced(self):
        rpc=Bridge(ptr=0)
        with self.assertRaises(RuntimeError):observe(rpc,0x91BF4590)
        self.assertNotIn("memory.read_bytes",[n for n,_ in rpc.calls])
    def test_summary_keeps_different_pointer_instances_separate(self):
        samples=[{"object_base":"0x92583488","frame_start":i*4,"frame_end":i*4+2,
                  "xyz":[float(i*2),0.,0.]} for i in range(4)]
        samples.append({"object_base":"0x90001000","frame_start":20,"frame_end":21,"xyz":[1.,2.,3.]})
        result=summarize(samples)
        self.assertEqual(len(result["object_instances"]),2)
        self.assertEqual(result["object_instances"][0]["moving_steps"],3)

if __name__=="__main__":unittest.main()
