"""Synthetic original-PPC-only tree proximity flag producer/consumer windows."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
sp=importlib.util.spec_from_file_location(
    "tree_flag_consumers",SCRIPTS/"p0_tree_flag_consumer_trace_private.py")
m=importlib.util.module_from_spec(sp)
sp.loader.exec_module(m)


def d(op,rt,ra,off):
    return (op<<26)|(rt<<21)|(ra<<16)|(off&0xFFFF)


def call(pc,dst):
    diff=dst-pc
    if diff%4 or not -(1<<25)<=diff<(1<<25):
        raise ValueError
    return (18<<26)|(diff&0x03FFFFFC)|1


def code():
    tree=m.source.UNITS["Tree"][0]
    fm=m.source.UNITS["FieldManager"][0]
    ball=m.source.UNITS["Ball"][0]
    sq=m.proximity.DISTANCE_FN
    data={
        tree+0x0020:0x38630030,
        tree+0x0030:call(tree+0x0030,sq),
        tree+0x0034:0xC002C5C0,
        tree+0x0038:0xFC010040,
        tree+0x0044:0x981F0048,
        tree+0x0504:d(34,0,30,0x48),
        fm+0x0788:d(34,0,3,0x48),
        ball+0x0750:call(ball+0x0750,sq),
        ball+0x0760:call(ball+0x0760,sq),
        tree+0x0508:d(11,0,0,0),
    }
    return data,lambda x:data.get(x,0)


class TreeFlagConsumerTests(unittest.TestCase):
    def test_source_anchors_three_verified_sites(self):
        data,read=code()
        m.check_anchors(read)

    def test_full_expected_bounded_window_count(self):
        data,read=code()
        r=m.summarize(read,False)
        self.assertEqual(len(r),3)
        self.assertEqual([x["instruction_count"] for x in r],[20,92,33])
        self.assertFalse(any(x["receiver_proven_to_be_tree"] for x in r))

    def test_byte_consumer_source_syntax(self):
        data,read=code()
        r=m.summarize(read,False)
        self.assertEqual(r[1]["offset_0x48_sites"],
                         [{"site":"+0x0504","instruction":"lbz",
                           "base_register":"r30","source_owner_proven":False}])
        self.assertEqual(r[2]["offset_0x48_sites"],
                         [{"site":"+0x0788","instruction":"lbz",
                           "base_register":"r3","source_owner_proven":False}])

    def test_producer_identified_without_contact_claim(self):
        data,read=code()
        r=m.summarize(read,False)
        self.assertEqual(r[0]["offset_0x48_sites"],
                         [{"site":"+0x0044","instruction":"stb",
                           "base_register":"r31","source_owner_proven":False}])
        self.assertFalse(r[0]["collision_or_rendering_semantics_verified"])

    def test_wrong_tree_flag_receiver_abstains(self):
        data,read=code()
        data[m.source.UNITS["Tree"][0]+0x0504]=d(34,0,31,0x48)
        with self.assertRaises(ValueError):
            m.summarize(read,False)

    def test_wrong_fieldmanager_flag_receiver_abstains(self):
        data,read=code()
        data[m.source.UNITS["FieldManager"][0]+0x0788]=d(34,0,4,0x48)
        with self.assertRaises(ValueError):
            m.summarize(read,False)

    def test_wrong_flag_offset_abstains(self):
        data,read=code()
        data[m.source.UNITS["Tree"][0]+0x0504]=d(34,0,30,0x4C)
        with self.assertRaises(ValueError):
            m.summarize(read,False)

    def test_source_square_distance_anchor_change_abstains(self):
        data,read=code()
        data[m.source.UNITS["Tree"][0]+0x0030]=call(
            m.source.UNITS["Tree"][0]+0x0030,m.proximity.DISTANCE_FN+4)
        with self.assertRaises(ValueError):
            m.summarize(read,False)

    def test_detail_lines_bounded_and_operator_only(self):
        data,read=code()
        r=m.summarize(read,True)
        self.assertEqual(len(r[0]["operator_local_code_lines"]),20)
        self.assertEqual(len(r[1]["operator_local_code_lines"]),92)
        self.assertEqual(len(r[2]["operator_local_code_lines"]),33)
        self.assertTrue(r[1]["operator_local_code_lines"][0].startswith("Tree+0x0450"))
        self.assertNotIn("operator_local_code_lines",m.summarize(read,False)[0])

    def test_no_private_heap_data_in_summary(self):
        import json
        data,read=code()
        result=json.dumps(m.summarize(read,False))
        self.assertNotIn("0x9000",result)
        self.assertNotIn("tree_positions",result)
        self.assertNotIn("native_hitbox_verified",result)


if __name__=="__main__":
    unittest.main()
