"""Read-only source-gated golfer pointer discovery synthetic tests."""
import importlib.util,json,struct,sys,tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("capture_golfer_memory",ROOT/"scripts"/"capture_golfer_memory.py")
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def word(buf,off,value):struct.pack_into(">I",buf,off,value)
class FakeRPC:
    def __init__(self,scene_id=5,sport_id=2,golf_main=0x80040000,rev=1,mode=4):
        self.calls=[];self.frame=100;self.rev=rev;self.mode=mode
        self.config=0x80010000;self.manager=0x80020000;self.scene=0x80030000
        self.globals=bytearray(m.GLOBALS_SIZE)
        word(self.globals,0,self.manager)
        self.objects={self.config:bytearray(0xA0),self.manager:bytearray(0x40),
                      self.scene:bytearray(0xA0),golf_main:bytearray(m.MAIN_BYTES)}
        word(self.objects[self.manager],0x18,scene_id)
        word(self.objects[self.manager],0x0C,self.scene)
        word(self.objects[self.scene],0x1C,scene_id)
        word(self.objects[self.scene],0x20,self.manager)
        word(self.objects[self.scene],0x40,10)
        word(self.objects[self.scene],0x54,sport_id)
        word(self.objects[self.scene],0x9C,golf_main)
        word(self.objects[golf_main],0x30,0x3F800000)
    def call(self,method,args):
        self.calls.append(method)
        if method=="frame.get_count":
            self.frame+=1;return self.frame
        if method=="memory.read_u32":
            addr=args[0]
            if addr==m.CONFIG_STORAGE:return self.config
            if addr==self.config+0x94:return self.mode
            for base,data in self.objects.items():
                if base<=addr<=base+len(data)-4:
                    return struct.unpack_from(">I",data,addr-base)[0]
            raise AssertionError("unknown 32-bit read")
        if method=="memory.read_bytes":
            addr,size=args
            if addr==0x80000000:return (b"RSPE01"+bytes([0,self.rev])).hex()
            if m.GLOBALS_BASE<=addr and addr+size<=m.GLOBALS_BASE+m.GLOBALS_SIZE:
                p=addr-m.GLOBALS_BASE
                return bytes(self.globals[p:p+size]).hex()
            for base,data in self.objects.items():
                if base<=addr and addr+size<=base+len(data):
                    return bytes(data[addr-base:addr-base+size]).hex()
            raise AssertionError(f"unexpected RAM read {addr:08X}/{size}")
        raise AssertionError("unsafe RPC "+method)

class GameplayCaptureTests(unittest.TestCase):
    def test_finds_and_rechecks_scene_and_golfer(self):
        rpc=FakeRPC()
        matches,checks=m.find_golfer(rpc)
        self.assertEqual(len(matches),1)
        self.assertEqual(matches[0]["slot_offsets"],[0x4D8])
        self.assertEqual(checks["golf_scene_id_candidates"],1)
        self.assertEqual(checks["validated_scene_identity_candidates"],1)
        one=m.read_instance(rpc,matches[0])
        self.assertEqual(len(bytes.fromhex(one["bytes_hex"])),m.MAIN_BYTES)
        self.assertTrue(all(x in ("frame.get_count","memory.read_u32","memory.read_bytes") for x in rpc.calls))
    def test_second_child_batch_is_disjoint_and_small(self):
        rpc=FakeRPC()
        offsets=[x for x in range(0,0x100,4) if x not in (0x30,0x74)][:22]
        for index,off in enumerate(offsets):
            ptr=0x80070000+index*0x1000
            word(rpc.objects[0x80040000],off,ptr)
            rpc.objects[ptr]=bytearray(m.CHILD_BYTES)
        match=m.find_golfer(rpc)[0][0]
        first,overflow1=m.child_watchlist(rpc,match,start_index=0,limit=16)
        second,overflow2=m.child_watchlist(rpc,match,start_index=16,limit=4)
        self.assertEqual(len(first),16)
        self.assertEqual(len(second),4)
        self.assertTrue(overflow1)
        self.assertTrue(overflow2)
        self.assertFalse({x["parent_offset"] for x in first} &
                         {x["parent_offset"] for x in second})
        observed=m.read_instance(rpc,match,second)
        self.assertEqual(len(observed["child_windows"]),4)

    def test_child_start_beyond_inventory_fails_before_capture(self):
        rpc=FakeRPC()
        match=m.find_golfer(rpc)[0][0]
        with self.assertRaises(ValueError):
            m.child_watchlist(rpc,match,start_index=63,limit=1)

    def test_wrong_scene_never_dereferences_candidate(self):
        a,b=m.find_golfer(FakeRPC(scene_id=6))
        self.assertEqual(a,[])
        self.assertEqual(b["golf_scene_id_candidates"],0)
    def test_wrong_scene_backlink_not_accepted(self):
        rpc=FakeRPC()
        word(rpc.objects[rpc.scene],0x20,0x80060000)
        self.assertEqual(m.find_golfer(rpc)[0],[])

    def test_valid_previous_scene_creator_is_not_current_scene_id(self):
        rpc=FakeRPC()
        match=m.find_golfer(rpc)[0]
        self.assertEqual(len(match),1)
        self.assertEqual(match[0]["creator_scene_id"],10)

    def test_child_watch_and_report_no_private_values(self):
        rpc=FakeRPC()
        ptr=0x80050000
        word(rpc.objects[0x80040000],0x34,ptr)
        rpc.objects[ptr]=bytearray(m.CHILD_BYTES)
        match,checks=m.find_golfer(rpc)
        watch,over=m.child_watchlist(rpc,match[0])
        self.assertEqual(len(watch),1)
        self.assertFalse(over)
        before=m.read_instance(rpc,match[0],watch)
        before.update(stage=0,phase="idle")
        word(rpc.objects[ptr],0x20,0x3F800000)
        after=m.read_instance(rpc,match[0],watch)
        after.update(stage=1,phase="aim_only")
        report=m.summarize([before,after],{"idle":1,"aim_only":1},checks,match[0],"test",1,False)
        self.assertEqual(report["changed_candidate_words"],1)
        self.assertEqual(report["top_relative_changes"][0]["region"],"child_at_main+0x034")
        self.assertEqual(report["top_relative_changes"][0]["offset"],"+0x020")
        encoded=json.dumps(report)
        self.assertNotIn("80050000",encoded)
        self.assertNotIn("3F800000",encoded)

    def test_mode_switch_during_capture_aborts(self):
        rpc=FakeRPC()
        match=m.find_golfer(rpc)[0][0]
        rpc.mode=2
        with self.assertRaises(RuntimeError):m.read_instance(rpc,match)

    def test_wrong_sport_is_not_golf_main(self):
        a,b=m.find_golfer(FakeRPC(sport_id=1))
        self.assertEqual(a,[])
        self.assertEqual(b["validated_sport_scene_candidates"],0)
    def test_revision_gate(self):
        with self.assertRaises(RuntimeError):m.find_golfer(FakeRPC(rev=0))
    def test_mode_gate(self):
        with self.assertRaises(RuntimeError):m.find_golfer(FakeRPC(mode=0))
    def test_pointer_changed_aborts_before_ram_read(self):
        rpc=FakeRPC()
        match=m.find_golfer(rpc)[0][0]
        word(rpc.objects[rpc.scene],0x9C,0x80050000)
        with self.assertRaises(RuntimeError):m.read_instance(rpc,match)
    def test_summary_reports_only_offsets_not_values(self):
        rpc=FakeRPC()
        match,check=m.find_golfer(rpc)
        r0=m.read_instance(rpc,match[0]);r0.update(stage=0,phase="idle")
        word(rpc.objects[match[0]["gameplay"]],0x30,0x40000000)
        r1=m.read_instance(rpc,match[0]);r1.update(stage=1,phase="aim_only")
        out=m.summarize([r0,r1],{"idle":1,"aim_only":1},check,match[0],"synthetic")
        self.assertEqual(out["changed_candidate_words"],1)
        self.assertEqual(out["top_relative_changes"][0]["offset"],"+0x030")
        self.assertEqual(out["top_relative_changes"][0]["region"],"main")
        self.assertTrue(out["creator_scene_id_not_used_for_identity"])
        self.assertTrue(out["actual_scene_id_verified"])
        self.assertFalse(out["power_verified"])
        for value in ("80040000","80030000","3F800000","40000000","bytes_hex"):
            self.assertNotIn(value,json.dumps(out))
    def test_no_unique_manager_creates_no_raw_file(self):
        with tempfile.TemporaryDirectory() as d:
            rpc=FakeRPC(scene_id=6);f=Path(d)/"private.jsonl"
            out=m.capture(rpc,[("idle",2)],.05,80,f)
            self.assertEqual(out["candidate_chains"],0)
            self.assertFalse(f.exists())

if __name__=="__main__":unittest.main()
