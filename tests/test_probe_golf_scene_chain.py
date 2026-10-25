"""No-input, source-gated Wii Sports scene chain probe tests."""
from __future__ import annotations
import importlib.util
import struct
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("scene_probe",ROOT/"scripts"/"probe_golf_scene_chain.py")
probe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

def _set(block,off,val):
    struct.pack_into(">I",block,off,val)

class StubRPC:
    def __init__(self,scene_id=5,sport_id=2,revision=1,game_mode=4):
        self.calls=[]
        self.clock=1000
        self.ptr_config=0x80010000
        self.ptr_manager=0x80020000
        self.ptr_scene=0x80030000
        self.globals=bytearray(probe.PAGE_SIZE)
        _set(self.globals,0x60,self.ptr_manager)
        self.manager=bytearray(0x20)
        _set(self.manager,0x0C,self.ptr_scene)
        self.scene=bytearray(0xA0)
        _set(self.scene,0x40,scene_id)
        _set(self.scene,0x54,sport_id)
        _set(self.scene,0x9C,0x80040000)
        self.revision=revision
        self.game_mode=game_mode
    def call(self,name,args):
        self.calls.append(name)
        if name=="frame.get_count":
            self.clock+=1
            return self.clock
        if name=="memory.read_u32":
            if args[0]==0x804BF8C4:return self.ptr_config
            if args[0]==self.ptr_config+0x94:return self.game_mode
            raise AssertionError("Unexpected word read")
        if name=="memory.read_bytes":
            addr,size=args
            if addr==0x80000000 and size==8:
                return (b"RSPE01"+bytes([0,self.revision])).hex()
            if probe.PAGE_START<=addr and addr+size<=probe.PAGE_START+probe.PAGE_SIZE:
                off=addr-probe.PAGE_START
                return bytes(self.globals[off:off+size]).hex()
            content={
                self.ptr_manager:self.manager,
                self.ptr_scene:self.scene
            }.get(addr)
            if content is None or len(content)<size:
                raise AssertionError("Unexpected memory read")
            return bytes(content[:size]).hex()
        raise AssertionError("Non-read RPC: "+name)

class SceneProbeTests(unittest.TestCase):
    def test_finds_only_source_verified_chain(self):
        rpc=StubRPC()
        report=probe.find_scene_chains(rpc)
        self.assertEqual(report["matching_scene_chains"],1)
        self.assertEqual(report["candidate_global_slot_relative_offsets"],["+0x060"])
        self.assertEqual(report["pointer_candidates"],1)
        self.assertFalse(report["swing_power_verified"])
        self.assertTrue(all(name in ("frame.get_count","memory.read_u32","memory.read_bytes")
                            for name in rpc.calls))
        output=str(report)
        self.assertNotIn("0x80030000",output)
        self.assertNotIn("0x80040000",output)
    def test_wrong_scene_id_not_misidentified(self):
        self.assertEqual(probe.find_scene_chains(StubRPC(scene_id=4))["matching_scene_chains"],0)
    def test_wrong_sport_id_not_misidentified(self):
        self.assertEqual(probe.find_scene_chains(StubRPC(sport_id=1))["matching_scene_chains"],0)
    def test_wrong_disc_revision_rejected(self):
        with self.assertRaises(RuntimeError):
            probe.find_scene_chains(StubRPC(revision=0))
    def test_wrong_training_mode_rejected(self):
        with self.assertRaises(RuntimeError):
            probe.find_scene_chains(StubRPC(game_mode=5))
    def test_no_manager_match_is_not_claimed_absent(self):
        result=probe.find_scene_chains(StubRPC(scene_id=0))
        self.assertEqual(result["matching_scene_chains"],0)
        self.assertIn("does NOT prove absence",result["warning"])
if __name__=="__main__":unittest.main()
