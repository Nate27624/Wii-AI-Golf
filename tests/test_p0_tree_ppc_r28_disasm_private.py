"""Synthetic-only boundaries and instruction decoding for r28 source disassembly."""
import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location("tree_r28",SCRIPTS/"p0_tree_ppc_r28_disasm_private.py")
d=importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


def df(op,rt,ra,imm):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&0xFFFF)


def mr(dst,src):
    return (31<<26)|(src<<21)|(dst<<16)|(src<<11)|(444<<1)


def branch(pc,target,link=1):
    delta=target-pc
    if delta%4 or not -(1<<25)<=delta<(1<<25):
        raise ValueError("not PPC branch")
    return (18<<26)|(delta&0x03FFFFFC)|(link&1)


class DisasmUnit(unittest.TestCase):
    def test_96_exact_words_and_source_anchors(self):
        words=[0]*d.MAX_WORDS
        words[(0x06BC-d.START)//4]=mr(28,3)
        words[(0x06E8-d.START)//4]=df(32,0,28,0x20)
        words[(0x06FC-d.START)//4]=df(32,0,28,0x1C)
        rows=d.build_lines(words)
        self.assertEqual(len(rows),96)
        self.assertIn("mr r28,r3",rows[(0x06BC-d.START)//4])
        self.assertIn("lwz r0,+32(r28)",rows[(0x06E8-d.START)//4])
        self.assertIn("lwz r0,+28(r28)",rows[(0x06FC-d.START)//4])
        self.assertEqual(sum("***" in x for x in rows),3)

    def test_wrong_length_rejected(self):
        with self.assertRaises(ValueError):
            d.build_lines([0]*95)

    def test_stack_stores_explicit(self):
        self.assertEqual(d.decode(d.BASE,df(36,0,1,0x20)),"stw r0,+32(r1)")

    def test_pc_relative_tree_call(self):
        pc=d.BASE+0x06C0
        target=d.src.UNITS["MapObjTree"][0]+0x20
        self.assertIn("MapObjTree+0x0020",d.decode(pc,branch(pc,target)))

    def test_bc_control_transfer(self):
        pc=d.BASE+0x06E4
        w=(16<<26)|(12<<21)|(2<<16)|(0xFFF8)
        self.assertIn("bc BO=12 BI=2",d.decode(pc,w))

    def test_mflr(self):
        self.assertEqual(d.decode(d.BASE,0x7C0802A6),"mflr r0")

    def test_mr(self):
        self.assertEqual(d.decode(d.BASE,mr(28,3)),"mr r28,r3")

    def test_mulli_scale_cue_not_inference(self):
        self.assertEqual(d.decode(d.BASE,df(7,9,8,84)),"mulli r9,r8,+84")

    def test_undecoded_keeps_opcode(self):
        self.assertIn("undecoded",d.decode(d.BASE,0))

    def test_no_dynamic_coordinates_or_training_fields(self):
        words=[0]*d.MAX_WORDS
        rows=d.build_lines(words)
        self.assertFalse(any("0x9000" in x for x in rows))
        self.assertEqual(len(d.ANCHORS),3)


if __name__=="__main__":
    unittest.main()
