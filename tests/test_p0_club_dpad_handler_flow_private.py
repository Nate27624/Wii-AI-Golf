"""Synthetic PPC D-pad handler control-flow contexts; no native archive."""
import importlib.util
from pathlib import Path
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
PATH=ROOT/"scripts"/"audit_p0_club_dpad_handler_flow_private.py"
spec=importlib.util.spec_from_file_location("p0_club_dpad_handler_flow",PATH)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

PC=0x802A28DC
UNIT="Pack/RPSports/RPGolScene/RPGolPlayerManager.cpp"
TARGET_UNIT="Pack/RPSports/RPGolScene/RPGolPlayer.cpp"
UNITS={UNIT:(PC,PC+0x1000), TARGET_UNIT:(0x8029E62C,0x8029F000)}
def op(primary,rt=3,ra=3,imm=0):
    return (primary<<26)|(rt<<21)|(ra<<16)|(imm&0xffff)

def call(pc,target):
    difference=target-pc
    assert -(1<<25)<=difference<(1<<25)
    return (18<<26)|(difference&0x03fffffc)|1

def setup(words):
    f=(PC,PC+4*len(words),"synthetic_manager",UNIT)
    b=struct.pack(">"+("I"*len(words)),*words)
    remote=(0x8029E62C,0x8029E63C,"synthetic_player",TARGET_UNIT)
    return b,f,sorted([f,remote])

class TestDpadHandlerFlow(unittest.TestCase):
    def test_direct_club_shape_windows(self):
        w=[op(32,4,31,0x20),op(28,4,4,8),op(16,12,2,8),
           op(14,3,3,-1),op(28,4,4,4),op(14,3,3,1),
           call(PC+24,0x8029E62C),0x4e800020]
        b,f,funcs=setup(w)
        report=m.trace_bytes(b,f,funcs,UNITS,context=4,max_lines=30)
        self.assertEqual(len(report["dpad_up_mask_sites"]),1)
        self.assertEqual(len(report["dpad_down_mask_sites"]),1)
        self.assertEqual(len(report["nearby_signed_ordinal_steps"]),2)
        self.assertEqual(report["all_resolved_direct_calls"][0]
                         ["callee_public_function"],"synthetic_player")
        self.assertEqual(len(report["instructions"]),8)
        self.assertFalse(report["club_index_destination_verified"])

    def test_branch_target_relative_fwd_and_back(self):
        w=(16<<26)|(12<<21)|(2<<16)|0x0008
        row=m.conditional(PC,w)
        self.assertEqual(row["target"],PC+8)
        self.assertEqual(m.conditional(PC,w|0xfffc)["target"],PC-4)
        self.assertEqual(m.conditional(PC,op(28,3,3,4)),None)

    def test_disassembly_has_direction_mask_source_regs(self):
        b,f,funcs=setup([op(28,4,5,0x8),op(28,4,5,0x4)])
        r=m.trace_bytes(b,f,funcs,UNITS,context=4,max_lines=30)
        masks=[a for a in r["instructions"] if a["role"]=="POSSIBLE_DPAD_MASK"]
        self.assertEqual(len(masks),2)
        self.assertEqual(masks[0]["details"]["masked_source_register"],"r4")
        self.assertEqual(masks[0]["details"]["masked_destination_register"],"r5")
        self.assertFalse(r["source_mask_applied_to_live_controller_status_verified"])

    def test_nonstack_store_preserves_receiver_unknown(self):
        b,f,funcs=setup([op(28,4,5,8),op(36,3,30,0x44),
                         op(28,4,5,4)])
        r=m.trace_bytes(b,f,funcs,UNITS,context=4,max_lines=30)
        self.assertEqual(r["nonstack_store_count"],1)
        self.assertEqual(r["all_nonstack_store_sites"][0]["displacement"],0x44)
        self.assertFalse(r["all_nonstack_store_sites"][0]["receiver_chain_verified"])

    def test_broad_mask_is_not_dpad(self):
        b,f,funcs=setup([op(28,3,3,0xffff),op(14,3,3,1)])
        r=m.trace_bytes(b,f,funcs,UNITS,context=4,max_lines=30)
        self.assertEqual(r["status"],"NO_DIRECT_BIT_SHAPE")

    def test_no_live_stores_or_verified_semantics(self):
        b,f,funcs=setup([op(28,3,3,8),0x4e800020])
        r=m.trace_bytes(b,f,funcs,UNITS,context=4,max_lines=30)
        self.assertFalse(r["training_approved"])
        self.assertFalse(r["runtime_dpad_execution_verified"])

    def test_coalesce_deterministic(self):
        self.assertEqual(m.coalesce([(8,15),(0,4),(3,7)]),[(0,15)])
        self.assertEqual(m.coalesce([(7,9),(0,1)]),[(0,1),(7,9)])

    def test_invalid_scope_limit_refuses(self):
        b,f,funcs=setup([op(28,3,3,8)])
        with self.assertRaises(m.base.Abstain):
            m.trace_bytes(b,f,funcs,UNITS,context=0,max_lines=50)
        with self.assertRaises(m.base.Abstain):
            m.trace_bytes(b,f,funcs,UNITS,context=4,max_lines=500)
        with self.assertRaises(m.base.Abstain):
            m.trace_bytes(b[:-1],f,funcs,UNITS,context=4,max_lines=50)

    def test_hardcoded_target_matches_public_rev1_function(self):
        import json
        units=m.base.source_units(json.loads(m.base.INDEX.read_text("utf-8")))
        funcs=m.graph.parse_public_functions(
            json.loads(m.graph.FUNCS.read_text("utf-8")),units)
        for name,pc in m.TARGETS.items():
            target=m.graph.function_at(pc,funcs)
            self.assertIsNotNone(target,name)
            self.assertEqual(target[0],pc,name)

if __name__=="__main__":
    unittest.main()
