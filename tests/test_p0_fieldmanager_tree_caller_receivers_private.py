"""Synthetic PPC FieldManager receiver trace for 94-tree writer vs other reader."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
import unittest
DIR=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(DIR))
sp=importlib.util.spec_from_file_location(
    "fm_receivers",DIR/"p0_fieldmanager_tree_caller_receivers_private.py")
m=importlib.util.module_from_spec(sp)
sp.loader.exec_module(m)


def branch(pc,target):
    delta=target-pc
    if delta%4 or not -(1<<25)<=delta<(1<<25):
        raise ValueError
    return (18<<26)|(delta&0x03FFFFFC)|1


def d(op,rt,ra,off):
    return (op<<26)|(rt<<21)|(ra<<16)|(off&65535)


def fixture():
    code=dict(m.identity.ANCHORS)
    for site,target in m.identity.TARGETS.values():
        code[site]=branch(site,target)
    tree=m.TREE
    ball=m.native.UNITS["Ball"][0]
    loop=m.native.LOOP
    sq=m.identity.proximity.DISTANCE_FN
    code.update({
        loop+0x06E8:d(32,0,28,0x20),
        loop+0x06F0:branch(loop+0x06F0,tree+0xC),
        loop+0x06F4:d(14,31,31,84),
        loop+0x06FC:d(32,0,28,0x1C),
        tree+0x0020:0x38630030,
        tree+0x0030:branch(tree+0x0030,sq),
        tree+0x0034:0xC002C5C0,
        tree+0x0038:0xFC010040,
        tree+0x0044:0x981F0048,
        ball+0x0750:branch(ball+0x0750,sq),
        ball+0x0760:branch(ball+0x0760,sq),
        m.FIELD+0x230C:branch(m.FIELD+0x230C,tree+0x047C),
        m.FIELD+0x2BB4:branch(m.FIELD+0x2BB4,tree+0x000C),
    })
    code[m.FIELD+0x2308]=d(32,3,31,0x20)
    return code,lambda pc:code.get(pc,0)


class FieldManagerTreeReceiverTests(unittest.TestCase):
    def test_exact_native_source_call_edges(self):
        words,read=fixture()
        self.assertEqual(
            m.native.direct_b(m.FIELD+0x230C,read(m.FIELD+0x230C)),
            (m.TREE+0x047C,True))
        self.assertEqual(
            m.native.direct_b(m.FIELD+0x2BB4,read(m.FIELD+0x2BB4)),
            (m.TREE+0x000C,True))
        self.assertEqual(len(m.CALL_LINKS),2)

    def test_four_bounded_windows(self):
        words,read=fixture()
        rows=m.inspect(read)
        self.assertEqual([x["source_instruction_count"] for x in rows],
                         [72,64,13,20])
        self.assertEqual(len(rows),4)
        self.assertTrue(rows[1]["known_tree_array_object_receiver_verified"])
        self.assertFalse(rows[0]["separate_reader_is_94_tree_object_proven"])

    def test_window_raw_code_only_when_explicit(self):
        words,read=fixture()
        normal=m.inspect(read,False)
        detailed=m.inspect(read,True)
        self.assertTrue(all("operator_local_code_lines" not in x for x in normal))
        for x in detailed:
            self.assertEqual(len(x["operator_local_code_lines"]),
                             x["source_instruction_count"])

    def test_static_source_missing_reader_edge_abstains(self):
        words,read=fixture()
        words[m.FIELD+0x230C]=0
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_static_source_wrong_writer_edge_abstains(self):
        words,read=fixture()
        words[m.FIELD+0x2BB4]=branch(m.FIELD+0x2BB4,m.TREE+0x0010)
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_source_identity_producer_guard(self):
        words,read=fixture()
        words[m.TREE+0x0044]=0
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_source_identity_camera_guard(self):
        words,read=fixture()
        words[m.TREE+0x04CC]=branch(m.TREE+0x04CC,0x8029BE44)
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_unknown_reader_uses_offset_but_identity_unproven(self):
        words,read=fixture()
        rows=m.inspect(read)
        self.assertIn(
            {"relative_site":"+0x2308","mnemonic":"lwz",
             "base_register":"r31","displacement_bytes":32},
            rows[0]["selected_member_offset_accesses"])
        self.assertFalse(rows[0]["tree_collision_geometry_verified"])
        self.assertFalse(rows[1]["tree_collision_geometry_verified"])

    def test_no_native_ram_contents_in_source_only_summary(self):
        import json
        words,read=fixture()
        txt=json.dumps(m.inspect(read))
        self.assertIn("FieldManager",txt)
        self.assertNotIn("0x9000",txt)
        self.assertNotIn("tree_positions",txt)
        self.assertNotIn("operator_local_code_lines",txt)


if __name__=="__main__":
    unittest.main()
