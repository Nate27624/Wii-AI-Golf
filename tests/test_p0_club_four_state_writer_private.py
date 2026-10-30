"""Synthetic proof-gated PPC four-state index and pointer-root tests."""
import importlib.util
from pathlib import Path
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
P=ROOT/"scripts"/"audit_p0_club_four_state_writer_private.py"
spec=importlib.util.spec_from_file_location("p0_four_state",P)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

UNIT_MANAGER="Pack/RPSports/RPGolScene/RPGolPlayerManager.cpp"
UNIT_SCENE="Pack/RPSports/RPGolScene/RPGolScene_unsplit.o"
UNITS={UNIT_MANAGER:(0x802A2210,0x802A3560),
       UNIT_SCENE:(0x802A79F8,0x802C7924)}
FUNCS=sorted([(m.MANAGER_PC,m.MANAGER_PC+984,"fn_802A28DC",UNIT_MANAGER),
              (m.HANDLER_PC,m.HANDLER_PC+1048,"fn_802A9BC8",UNIT_SCENE)])

def di(primary,reg,base,imm):
    return (primary<<26)|(reg<<21)|(base<<16)|(imm&0xffff)

def branch(pc,target,link=0,conditional=False):
    d=target-pc
    assert d%4==0
    if conditional:
        assert -0x8000 <= d < 0x8000
        return (16<<26)|(12<<21)|(2<<16)|(d&0xfffc)
    assert -(1<<25) <= d < (1<<25)
    return (18<<26)|(d&0x03fffffc)|link

def make():
    mg=bytearray(984)
    handler=bytearray(1048)
    for offset,arg,setup in m.MANAGER_CALLS:
        struct.pack_into(">I",mg,setup,di(32,3,13,-0x5a80))
        struct.pack_into(">I",mg,offset-4,di(14,4,0,arg))
        struct.pack_into(">I",mg,offset,branch(m.MANAGER_PC+offset,m.HANDLER_PC,1))
    put=lambda offset,value:struct.pack_into(">I",handler,offset,value)
    put(0x0e8,di(11,0,4,0))
    put(0x0ec,branch(m.HANDLER_PC+0x0ec,m.HANDLER_PC+0x234,conditional=True))
    put(0x0f0,di(32,4,3,0x1c))
    put(0x0f4,di(11,0,4,3))
    put(0x0f8,branch(m.HANDLER_PC+0x0f8,m.HANDLER_PC+0x1a8,conditional=True))
    put(0x0fc,di(14,0,4,1))
    put(0x100,di(36,0,3,0x1c))
    put(0x234,di(32,4,3,0x1c))
    put(0x238,di(11,0,4,0))
    put(0x23c,branch(m.HANDLER_PC+0x23c,m.HANDLER_PC+0x300,conditional=True))
    put(0x240,di(14,0,4,-1))
    put(0x244,di(36,0,3,0x1c))
    return mg,handler

class TestFourStateWriter(unittest.TestCase):
    def test_same_receiver_field_with_two_directions(self):
        mg,handler=make()
        report=m.evidence(mg,handler,FUNCS,UNITS)
        self.assertIn("FOUR_STATE_INDEX_WRITER",report["status"])
        self.assertEqual(len(report["static_direction_calls"]),4)
        self.assertEqual([r["direction_argument_r4"] for r in report["static_direction_calls"]],[0,1,0,1])
        self.assertEqual(report["selector_behavior_source"]["field_displacement"],"+0x01C")
        self.assertEqual(report["selector_behavior_source"]["observed_index_bounds"],{"minimum":0,"maximum":3})
        self.assertFalse(report["game_club_id_verified"])
        self.assertFalse(report["training_approved"])

    def test_other_member_displacement_abstains(self):
        mg,handler=make()
        struct.pack_into(">I",handler,0x244,di(36,0,3,0x20))
        with self.assertRaises(m.base.Abstain):
            m.evidence(mg,handler,FUNCS,UNITS)

    def test_wrong_index_bound_abstains(self):
        mg,handler=make()
        struct.pack_into(">I",handler,0x0f4,di(11,0,4,4))
        with self.assertRaises(m.base.Abstain):
            m.evidence(mg,handler,FUNCS,UNITS)

    def test_branch_target_wrong_abstains(self):
        mg,handler=make()
        struct.pack_into(">I",handler,0x0ec,branch(m.HANDLER_PC+0x0ec,
                                                    m.HANDLER_PC+0x200,conditional=True))
        with self.assertRaises(m.base.Abstain):
            m.evidence(mg,handler,FUNCS,UNITS)

    def test_caller_receiver_global_source_required(self):
        mg,handler=make()
        struct.pack_into(">I",mg,0x158,di(32,3,13,-0x5a70))
        with self.assertRaises(m.base.Abstain):
            m.evidence(mg,handler,FUNCS,UNITS)

    def test_wrong_direction_argument_abstains(self):
        mg,handler=make()
        struct.pack_into(">I",mg,0x264,di(14,4,0,3))
        with self.assertRaises(m.base.Abstain):
            m.evidence(mg,handler,FUNCS,UNITS)

    def test_selected_function_bounds_are_public(self):
        import json
        source_map=m.base.source_units(json.loads(m.base.INDEX.read_text("utf-8")))
        fs=m.graph.parse_public_functions(json.loads(m.graph.FUNCS.read_text("utf-8")),source_map)
        for pc in (m.MANAGER_PC,m.HANDLER_PC):
            f=m.graph.function_at(pc,fs)
            self.assertIsNotNone(f)
            self.assertEqual(f[0],pc)

if __name__=="__main__":
    unittest.main()
