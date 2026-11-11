"""Synthetic-only Rev1 Golf live club indicator; no emulator or private RAM."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts"),str(ROOT/"tests")]

from test_p0_memory_inspector_fast import FixtureRPC
from wii_ai_golf.inspector.club import (
    CLUB_GLOBAL_SLOT, CLUB_FIELD_OFFSET, PLAYER_MANAGER_GLOBAL_SLOT,
    club_label,
)
from wii_ai_golf.inspector.fast import packet as fast_packet
from wii_ai_golf.inspector.live import LiveSampler, LiveEvent, ReadOnlyRPC


class CandidateBridge(FixtureRPC):
    def __init__(self,club=2,owner=0x900B0000):
        super().__init__()
        self.owner=owner
        self.words[CLUB_GLOBAL_SLOT]=owner
        if 0x90000000 <= owner < 0x94000000:
            self.words[owner+CLUB_FIELD_OFFSET]=club
        self.index_reads=0
        self.mutate_index=False
        self.mutate_pointer=False
        self.global_block_reads=0

    def call(self,method,args):
        if method=="memory.read_bytes":
            addr,size=args
            if addr==self.owner+CLUB_FIELD_OFFSET and size==4:
                self.index_reads+=1
                if self.mutate_index and self.index_reads==2:
                    return (3).to_bytes(4,"big").hex()
            if addr<=CLUB_GLOBAL_SLOT<addr+size:
                self.global_block_reads+=1
                if self.mutate_pointer and self.global_block_reads==2:
                    saved=self.words[CLUB_GLOBAL_SLOT]
                    self.words[CLUB_GLOBAL_SLOT]=0x900C0000
                    try:
                        return super().call(method,args)
                    finally:
                        self.words[CLUB_GLOBAL_SLOT]=saved
        return super().call(method,args)


class ClubIndexTests(unittest.TestCase):
    def test_club_values_operator_confirmed_all_four(self):
        for index,name in enumerate(("DRIVER","IRON","WEDGE","PUTTER")):
            with self.subTest(index=index):
                self.assertEqual(club_label(index),name)
        for value in (-1,4,None,True,False,0.0,1.0,"1",[],{}):
            with self.subTest(bad=value):
                self.assertEqual(club_label(value),"UNKNOWN")

    def test_source_separate_global_and_field(self):
        self.assertEqual(CLUB_GLOBAL_SLOT,0x804BF900)
        self.assertEqual(CLUB_FIELD_OFFSET,0x1C)
        self.assertEqual(PLAYER_MANAGER_GLOBAL_SLOT,0x804BF8D0)
        self.assertEqual(CLUB_GLOBAL_SLOT-PLAYER_MANAGER_GLOBAL_SLOT,0x30)

    def test_fast_packet_source_checked_club(self):
        for value in range(4):
            with self.subTest(value=value):
                x=CandidateBridge(club=value)
                data=fast_packet(x,"LIVE",0,include_a_state=True,include_club_state=True)
                self.assertEqual(data["club_index"],value)
                self.assertEqual(x.index_reads,2)
                self.assertEqual(x.global_block_reads,2)
                self.assertEqual(data["identity"][4],x.words[PLAYER_MANAGER_GLOBAL_SLOT])
                self.assertEqual(data["words"]["selected_ball_plus_0x30"][0],0x3f000000)
                self.assertIsNotNone(data["a_record"])
                self.assertTrue(all(m in {"memory.read_bytes","frame.get_count"} for m,_ in x.calls))

    def test_source_specific_opt_in_keeps_old_packet_schema(self):
        x=CandidateBridge()
        self.assertNotIn("club_index",fast_packet(x,"LIVE",0))
        self.assertEqual(x.index_reads,0)

    def test_invalid_slot_pointer_is_unknown_not_trusted(self):
        for owner in (0,0x1234,0x804BF900,0x94000000,
                      0x90040000,True):
            with self.subTest(owner=owner):
                x=CandidateBridge(owner=0x900B0000)
                x.words[CLUB_GLOBAL_SLOT]=owner
                result=fast_packet(x,"LIVE",0,include_club_state=True)
                self.assertIsNone(result["club_index"])

    def test_invalid_field_range_abstains_from_label_only(self):
        for word in (4,0xffffffff):
            x=CandidateBridge(club=word)
            result=fast_packet(x,"LIVE",0,include_club_state=True)
            self.assertIsNone(result["club_index"])

    def test_changing_index_during_packet_unknown(self):
        x=CandidateBridge()
        x.mutate_index=True
        r=fast_packet(x,"LIVE",0,include_club_state=True)
        self.assertIsNone(r["club_index"])

    def test_changing_pointer_during_packet_unknown(self):
        x=CandidateBridge()
        x.mutate_pointer=True
        r=fast_packet(x,"LIVE",0,include_club_state=True)
        self.assertIsNone(r["club_index"])

    def test_missing_event_club_defaults_unknown(self):
        e=LiveEvent("sample")
        self.assertEqual(e.club_label,"UNKNOWN")
        self.assertIsNone(e.club_index)

    def test_worker_readonly_allowlist_kept(self):
        x=CandidateBridge()
        p=ReadOnlyRPC(x)
        self.assertEqual(p.call("frame.get_count",[]),1)
        with self.assertRaises(PermissionError):
            p.call("memory.write_u32",[0x804BF900,123])
        with self.assertRaises(PermissionError):
            p.call("controller.set_buttons",[0,0])

    def test_ui_has_live_and_stale_status_resets(self):
        source=(ROOT/"src/wii_ai_golf/inspector/gui.py").read_text("utf-8")
        self.assertIn('self.club_status.set("CLUB " + event.club_label)',source)
        self.assertGreaterEqual(source.count('self.club_status.set("CLUB UNKNOWN")'),5)
        self.assertNotIn('memory.write_u32',source)
        self.assertNotIn('controller.set_buttons',source)


if __name__=="__main__":
    unittest.main()
