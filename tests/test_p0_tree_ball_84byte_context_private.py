"""Synthetic tests for exact Ball/Tree 84-byte source windows, no physics claims."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
import unittest
SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
sp=importlib.util.spec_from_file_location("ball_tree84",SCRIPTS/"p0_tree_ball_84byte_context_private.py")
m=importlib.util.module_from_spec(sp)
sp.loader.exec_module(m)


def df(op,rt,ra,off):
    return (op<<26)|(rt<<21)|(ra<<16)|(off&0xFFFF)


def bl(pc,target):
    delta=target-pc
    return (18<<26)|(delta&0x03FFFFFC)|1


def fixture():
    ball=m.src.UNITS["Ball"][0]
    tree=m.src.UNITS["Tree"][0]
    w={
        ball+0x0738:df(14,31,31,84),
        tree+0x002C:df(14,10,10,84),
        ball+0x0720:df(32,7,28,0x20),
        ball+0x0724:df(48,1,29,0x30),
        ball+0x0740:bl(ball+0x0740,tree+0x100),
        tree+0x0050:df(36,2,1,0x20),
    }
    return w,lambda p:w.get(p,0)


class SourceStride84(unittest.TestCase):
    def test_both_bounded_source_windows(self):
        w,read=fixture()
        rows=m.scan(read)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["word_count"],120)
        self.assertEqual(rows[1]["word_count"],48)
        self.assertEqual(rows[0]["source_unit"],"Ball")
        self.assertEqual(rows[1]["source_unit"],"Tree")

    def test_ball_object_field_offset_not_receiver_proof(self):
        w,read=fixture()
        d=m.scan(read)[0]
        self.assertIn({"site":"+0x0720","kind":"lwz","base_register":"r28",
                       "field_offset":"+0x20","stack_based":False},
                      d["object_member_offset_sites"])
        self.assertFalse(d["tree_array_receiver_proven"])
        self.assertFalse(d["ball_tree_contact_proven"])

    def test_source_tree_code_call_labeled_but_not_interaction(self):
        w,read=fixture()
        d=m.scan(read)[0]
        self.assertIn({"caller":"+0x0740","target":"Tree+0x0100"},
                      d["direct_call_targets"])
        self.assertFalse(d["ball_tree_contact_proven"])

    def test_wrong_ball_stride_abstains(self):
        w,read=fixture()
        w[m.src.UNITS["Ball"][0]+0x0738]=df(14,31,31,80)
        with self.assertRaises(ValueError):
            m.scan(read)

    def test_wrong_tree_stride_abstains(self):
        w,read=fixture()
        w[m.src.UNITS["Tree"][0]+0x002C]=df(14,10,10,88)
        with self.assertRaises(ValueError):
            m.scan(read)

    def test_tiny_details_remain_bounded(self):
        w,read=fixture()
        rows=m.scan(read,detail=True)
        self.assertEqual(len(rows[0]["local_source_code_lines"]),120)
        self.assertEqual(len(rows[1]["local_source_code_lines"]),48)
        self.assertTrue(rows[0]["local_source_code_lines"][0].startswith("Ball+0x0640"))

    def test_default_does_not_expose_raw_code(self):
        w,read=fixture()
        import json
        s=json.dumps(m.scan(read))
        self.assertNotIn("394A0054",s)
        self.assertNotIn("0x9000",s)
        self.assertNotIn('"local_source_code_lines"',s)

    def test_stack_base_marked(self):
        w,read=fixture()
        r=m.scan(read)[1]
        self.assertEqual(r["stack_load_store_count"],1)
        self.assertTrue(r["object_member_offset_sites"][0]["stack_based"])

    def test_original_window_identity(self):
        self.assertEqual(m.ANCHORS[0],("Ball",0x0738,14,84))
        self.assertEqual(m.ANCHORS[1],("Tree",0x002C,14,84))
        self.assertLessEqual(sum((hi-lo)//4 for _,__,lo,hi in m.WINDOWS),m.MAX_WORDS)


if __name__=="__main__":
    unittest.main()
