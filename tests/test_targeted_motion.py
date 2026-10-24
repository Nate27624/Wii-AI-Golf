"""Targeted read-only sampler never issues writes, and deduplicates overlapping windows."""
import struct
import unittest
from unittest.mock import patch

from wii_ai_golf.targeted_motion import preflight, capture_one, analyze, read_hex


class Fake:
    def __init__(self):
        self.calls=[]
        self.frames=100
    def call(self, name, params=None):
        self.calls.append((name,params))
        if name=="frame.get_count":
            self.frames+=1
            return self.frames
        if name=="memory.read_u32":return 0x91BF48BC
        if name=="memory.read_bytes":
            address,size=params
            return (struct.pack(">fff",12.,25.,-30.)+bytes(size))[:size].hex()
        raise AssertionError(name)


class TargetedTests(unittest.TestCase):
    def test_bounds_and_bad_hex(self):
        with self.assertRaises(ValueError):read_hex(Fake(),0x100,12)
        with self.assertRaises(ValueError):read_hex(Fake(),0x91BF48BC,129)

    def test_preflight_source_gate(self):
        rpc=Fake()
        with patch("wii_ai_golf.targeted_motion.probe_rev1",
                   return_value={"supported":False}):
            with self.assertRaises(RuntimeError):preflight(rpc)

    def test_narrow_capture_frame_brackets_dedup_and_read_only(self):
        rpc=Fake()
        out=capture_one(rpc,{"a":0x91BF48BC,"b":0x91BF48BC},offset=0x30,length=64)
        self.assertEqual(out["frame_span"],1)
        self.assertEqual(out["windows"]["a"]["bytes_hex"],out["windows"]["b"]["bytes_hex"])
        self.assertEqual(sum(name=="memory.read_bytes" for name,_ in rpc.calls),1)
        self.assertTrue(all(n in ("frame.get_count","memory.read_bytes") for n,_ in rpc.calls))

    def test_offset_constraints(self):
        with self.assertRaises(ValueError):
            capture_one(Fake(),{"a":0x91BF48BC},offset=3)
        with self.assertRaises(ValueError):
            capture_one(Fake(),{"a":0x91BF48BC},length=256)

    def test_dedup_analysis(self):
        captures=[]
        for i in range(5):
            v=(struct.pack(">fff",2.*i,9.,-10.)+bytes(20)).hex()
            captures.append({"windows":{"a":{"address":"0x91BF4900","bytes_hex":v},
                                        "b":{"address":"0x91BF4900","bytes_hex":v}}})
        result=analyze(captures)
        self.assertEqual(result["sample_count"],5)
        self.assertGreaterEqual(result["candidate_count"],1)
        addresses=[x["address"] for x in result["candidates"]]
        self.assertEqual(len(addresses),len(set(addresses)))


if __name__=="__main__":
    unittest.main()
