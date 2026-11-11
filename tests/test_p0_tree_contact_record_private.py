"""Offline synthetic read-only WOOD/LEAVES/NEAR_MISS live recorder tests."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts"/"p0_tree_contact_record_private.py"
spec=importlib.util.spec_from_file_location("tree_live_recorder",SCRIPT)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class MockFelkRPC:
    """Pure BE word-keyed synthetic memory; no emulator or network."""
    def __init__(self):
        self.mem={}
        self.frames=100
        self.ball=0x90008000
        self.field=0x90003000
        self.pm=0x90004000
        self.rec=self.pm+4
        self.tree=0x90020000
        self.setup()

    def put(self,addr,value):
        raw=value.to_bytes(4,"big")
        for i,v in enumerate(raw):
            self.mem[addr+i]=v

    def setup(self):
        head=b"RSPE01\0\1"
        for i,v in enumerate(head):
            self.mem[0x80000000+i]=v
        manager=0x80002000
        scene=0x90001000
        config=0x90002000
        self.put(m.source.SCENE_STATIC,manager)
        self.put(m.source.SCENE_STATIC+4,0)
        self.put(manager+0x18,5)
        self.put(manager+0xC,scene)
        self.put(scene+0x1C,5)
        self.put(scene+0x20,manager)
        self.put(scene+0x54,2)
        self.put(m.source.CONFIG_STATIC,config)
        self.put(m.source.FIELD_STATIC,self.field)
        self.put(m.source.PLAYER_MANAGER_STATIC,self.pm)
        self.put(config+0x94,4)
        self.put(config+0x98,2)
        self.put(self.pm,0x803C7DD0)
        self.put(self.pm+0x334,self.rec)
        self.put(self.rec+0x88,self.ball)
        self.put(self.ball,0x803C7918)
        self.put(self.ball+0x4C,0x9000A000)
        self.put(self.field+0x1C,94)
        self.put(self.field+0x20,self.tree)
        for i in range(m.TREES):
            self.put(self.tree+i*m.TREE_STRIDE,0x803C7000)

    def call(self,method,params):
        if method=="frame.get_count":
            self.frames+=1
            return self.frames
        if method=="memory.read_u32":
            start=params[0]
            return int.from_bytes(bytes(self.mem.get(start+i,0)
                                        for i in range(4)),"big")
        if method=="memory.read_bytes":
            start,count=params
            return bytes(self.mem.get(start+i,0)
                         for i in range(count)).hex()
        raise AssertionError("Recorder attempted unsupported or writing RPC")


class TreeLiveCaptureTests(unittest.TestCase):
    def test_three_operator_intents_preserved(self):
        self.assertEqual(m.TYPES,("wood","leaves","near_miss"))
        self.assertNotIn("tree_contact_verified",m.TYPES)

    def test_preflight_qualifies_source_and_tree_array(self):
        rpc=MockFelkRPC()
        v=m.preflight(rpc)
        self.assertEqual(v["selected_index"],0)
        self.assertEqual(v["hole_raw"],2)
        self.assertEqual(v["mode_raw"],4)
        self.assertTrue(v["shared_tree_firstword_94"])
        self.assertEqual(len(v["initial_tree_bytes"]),94*84)

    def test_sample_captures_non_atomic_source_candidates(self):
        rpc=MockFelkRPC()
        state=m.preflight(rpc)
        x=m.sample(rpc,state,0,8)
        self.assertEqual(len(bytes.fromhex(x["ball_object_candidate_be_hex_PRIVATE"])),0x1C0)
        self.assertEqual(len(bytes.fromhex(x["selected_record_be_hex_PRIVATE"])),0xCC)
        self.assertEqual(len(bytes.fromhex(x["nested_translation_candidate_be_hex_PRIVATE"])),12)
        self.assertEqual(len(bytes.fromhex(x["all_94_tree_records_be_hex_PRIVATE"])),94*84)
        self.assertTrue(x["not_same_physics_frame_verified"])
        self.assertFalse(x["contact_detected_by_memory"])
        self.assertFalse(x["training_approved"])

    def test_tree_snapshot_throttled_while_ball_recorded_each_sample(self):
        rpc=MockFelkRPC()
        state=m.preflight(rpc)
        x=m.sample(rpc,state,1,8)
        self.assertIsNone(x["all_94_tree_records_be_hex_PRIVATE"])
        self.assertEqual(len(bytes.fromhex(x["ball_object_candidate_be_hex_PRIVATE"])),0x1C0)

    def test_invalid_tree_firstword_refuses(self):
        rpc=MockFelkRPC()
        rpc.put(rpc.tree+20*m.TREE_STRIDE,0x803C7200)
        with self.assertRaises(ValueError):
            m.preflight(rpc)

    def test_not_golf_refuses(self):
        rpc=MockFelkRPC()
        manager=rpc.call("memory.read_u32",[m.source.SCENE_STATIC])
        rpc.put(manager+0x18,3)
        with self.assertRaises(ValueError):
            m.preflight(rpc)

    def test_changed_ball_owner_stops_sample(self):
        rpc=MockFelkRPC()
        state=m.preflight(rpc)
        rpc.put(rpc.rec+0x88,0x90009900)
        with self.assertRaises(ValueError):
            m.sample(rpc,state,0,8)

    def test_capture_loop_is_bounded_and_never_calls_input(self):
        rpc=MockFelkRPC()
        state=m.preflight(rpc)
        import threading
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/"raw-PRIVATE.jsonl"
            stop=threading.Event()
            errors=[]
            counts={"samples":0,"tree_snapshots":0,"screenshots":0}
            m.capture_loop(rpc,state,output,stop,10.0,0.18,8,errors,counts)
            self.assertTrue(output.exists())
            self.assertGreaterEqual(counts["samples"],1)
            self.assertEqual(errors,[])
            self.assertTrue(stop.is_set())
            self.assertNotIn("training_approved\":true",output.read_text().lower())

    def test_disallows_synced_or_repo_outputs(self):
        with self.assertRaises(ValueError):
            m.safe_private_root(ROOT)
        with tempfile.TemporaryDirectory(prefix="OneDrive-Private-") as d:
            with self.assertRaises(ValueError):
                m.safe_private_root(Path(d))

    def test_source_window_bounds(self):
        rpc=MockFelkRPC()
        with self.assertRaises(ValueError):
            m.bytes_read(rpc,0x80000000,24*1024*1024+1)
        with self.assertRaises(ValueError):
            m.bytes_read(rpc,0x10000000,12)

    def test_main_offline_selftest_without_private_directory(self):
        self.assertEqual(m.main(["--selftest"]),0)


if __name__=="__main__":
    unittest.main()
