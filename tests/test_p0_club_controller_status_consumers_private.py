"""Synthetic source-bounded PPC status-consumer audit checks."""
import importlib.util
from pathlib import Path
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
P=ROOT/"scripts"/"audit_p0_club_controller_status_consumers_private.py"
spec=importlib.util.spec_from_file_location("status_club",P)
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

START=0x802B4794
DEST=0x8019BAE8
SCENE="Pack/RPSports/RPGolScene/RPGolScene_unsplit.o"
CONTROLLER="Pack/RPKernel/RPSysController.cpp"
UNITS={SCENE:(START,START+0x800),CONTROLLER:(DEST,DEST+0x800)}

def ins(op,rs=3,ra=3,imm=0):
    return (op<<26)|(rs<<21)|(ra<<16)|(imm&65535)
def word(*data):
    return struct.pack(">"+("I"*len(data)),*data)
def bl(pc,target):
    return (18<<26)|((target-pc)&0x03FFFFFC)|1

def setup(*instructions):
    code=word(*instructions)
    mm=bytearray(START-audit.base.MEM1+len(code))
    mm[START-audit.base.MEM1:]=code
    funcs=[(DEST,DEST+24,"getExCoreStatus__synthetic",CONTROLLER),
           (START,START+len(code),"fn_test",SCENE)]
    return mm,funcs[1],funcs

class TestStatusConsumer(unittest.TestCase):
    def test_status_getter_context_is_bounded(self):
        ram,f,funcs=setup(0x60000000,bl(START+4,DEST),
                          ins(32,3,3,0x10),ins(28,3,3,0x400),
                          ins(36,3,31,0x24),0x4e800020)
        result=audit.review_function(ram,f,funcs,UNITS)
        self.assertEqual(result["status_getter_call_count"],1)
        w=result["status_getter_windows"][0]
        self.assertEqual(w["target_public_function"],"getExCoreStatus__synthetic")
        self.assertEqual(w["callsite_in_function"],"+0x004")
        self.assertTrue(any(z["role"]=="STATUS_CALL" for z in w["disassembly_window"]))
        self.assertFalse(w["specific_button_mask_verified"])
        self.assertFalse(w["club_selector_write_verified"])

    def test_no_getter_no_claim(self):
        ram,f,funcs=setup(ins(36,3,31,0x24),0x4e800020)
        result=audit.review_function(ram,f,funcs,UNITS)
        self.assertEqual(result["status_getter_call_count"],0)
        self.assertEqual(len(result["nonstack_store_site_examples"]),1)

    def test_indirect_call_detected_but_not_resolved(self):
        ram,f,funcs=setup(0x4e800421,ins(36,3,31,0x24),0x4e800020)
        result=audit.review_function(ram,f,funcs,UNITS)
        self.assertEqual(result["status_getter_call_count"],0)
        self.assertEqual(result["indirect_bctrl_function_relative_sites"],["+0x000"])

    def test_known_ppc_mask_load_and_branch_decode(self):
        self.assertEqual(audit._simple_instruction(START,ins(14,3,0,1),START,START+40),"li r3,+1")
        self.assertEqual(audit._simple_instruction(START,ins(28,4,4,0x800),START,START+40),"andi. r4,r4,mask=0x0800")
        self.assertEqual(audit._simple_instruction(START,0x7c632038,START,START+40),"and r3,r3,r4")
        self.assertEqual(audit._simple_instruction(START,0x4e800020,START,START+40),"blr")

    def test_unknown_opcode_is_not_invented(self):
        self.assertIn("not decoded",audit._simple_instruction(START,0xffffffff,START,START+40))

    def test_malformed_function_bounds_abstain(self):
        ram,f,funcs=setup(0x60000000)
        with self.assertRaises(audit.base.Abstain):
            audit.review_function(ram,(START,START+3,"bad",SCENE),funcs,UNITS)

    def test_disallow_excessive_window(self):
        ram,f,funcs=setup(0x60000000)
        with self.assertRaises(audit.base.Abstain):
            audit.review_function(ram,f,funcs,UNITS,limit=50)

    def test_public_targets_are_in_index(self):
        fs=audit.graph.parse_public_functions(
            __import__("json").loads(audit.graph.FUNCS.read_text("utf-8")),
            audit.base.source_units(__import__("json").loads(audit.base.INDEX.read_text("utf-8"))))
        seen={f[0] for f in fs}
        self.assertTrue(set(audit.TARGETS["scene-status"]).issubset(seen))
        self.assertTrue(set(audit.TARGETS["player-controller"]).issubset(seen))

if __name__=="__main__":
    unittest.main()
