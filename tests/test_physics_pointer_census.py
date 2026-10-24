"""One-hop pointer census safety and motion ranking."""
import struct
import unittest
from unittest.mock import patch
from wii_ai_golf.physics_pointer_census import (
    valid_mem, read_bytes, discover_roots, find_pointer_candidates, capture, analyze,
)
class Fake:
    def __init__(self):
        self.calls=[]
        self.frame=0
    def call(self,method,params=None):
        self.calls.append((method,params))
        if method=="frame.get_count":
            self.frame+=1
            return self.frame
        if method=="memory.read_bytes":
            address,count=params
            if address==0x90001000:
                data=bytearray(count)
                struct.pack_into(">I",data,0,0x90002000)
                struct.pack_into(">I",data,4,0x90002000)
                struct.pack_into(">I",data,8,0x7FFFFFFF)
                return bytes(data).hex()
            return bytes(count).hex()
        raise AssertionError(method)

class CensusTests(unittest.TestCase):
    def test_region_bounds(self):
        self.assertTrue(valid_mem(0x90001000,128))
        self.assertFalse(valid_mem(0x7FFFFFFF,128))
        self.assertFalse(valid_mem(0x93FFFFF0,128))

    def test_source_gate(self):
        with patch("wii_ai_golf.physics_pointer_census.probe_rev1",
                   return_value={"supported":False}):
            with self.assertRaises(RuntimeError):
                discover_roots(Fake())

    def test_candidate_dedup_and_one_level(self):
        rpc=Fake()
        out=find_pointer_candidates(rpc,{"golf_field":0x90001000})
        self.assertEqual(len(out),1)
        self.assertEqual(out[0]["address"],"0x90002000")
        self.assertEqual(out[0]["owner_offset"],"+0x0")
        self.assertTrue(all(n=="memory.read_bytes" for n,_ in rpc.calls))

    def test_read_rejects_invalid_pointer_without_rpc(self):
        rpc=Fake()
        with self.assertRaises(ValueError):read_bytes(rpc,0x1000,128)
        self.assertEqual(rpc.calls,[])

    def test_frame_brackets_and_only_reads(self):
        rpc=Fake()
        r=capture(rpc,[{"address":"0x90002000"},{"address":"0x90002000"}])
        self.assertEqual(r["frame_span"],1)
        self.assertEqual(len(r["objects"]),1)
        self.assertTrue(all(n in ("memory.read_bytes","frame.get_count") for n,_ in rpc.calls))

    def test_motion_candidates_no_false_identity(self):
        scans=[]
        for i in range(5):
            blob=struct.pack(">fff",float(i*2),10.,100.)+bytes(116)
            scans.append({"objects":[{"address":"0x90002000","bytes_hex":blob.hex()}]})
        result=analyze(scans)
        self.assertTrue(result["candidates_total"])
        self.assertEqual(result["candidates"][0]["address"],"0x90002000")
        self.assertIn("UNVERIFIED",result["candidates"][0]["status"])
if __name__=="__main__":unittest.main()
