"""Synthetic-only, source-safe full public map classification of tree firstword."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/"scripts"
TESTS=ROOT/"tests"
sys.path.insert(0,str(SCRIPTS))


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    x=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(x)
    return x


m=load("full_tree_public_targets",SCRIPTS/"p0_tree_full_public_table_targets_private.py")
prior=load("tree_indirect_fixture",
           TESTS/"test_p0_tree_ball_indirect_dispatch_private.py")


class TreeFullPublicTargetsTests(unittest.TestCase):
    def test_retained_public_source_map_is_qualified(self):
        p=json.loads(m.MAP.read_text(encoding="utf-8"))
        rows=m.validated_intervals(p)
        self.assertGreater(len(rows),100)
        self.assertTrue(all(rows[i][1]<=rows[i+1][0]
                            for i in range(len(rows)-1)))

    def test_true_public_unit_source_and_offset(self):
        entries=[
            (0x80296238,0x80296EA8,"Pack/RPSports/RPGolScene/RPGolMapObjTree.cpp"),
            (0x80296FD8,0x8029B240,"Pack/RPSports/RPGolScene/RPGolMapObjBall.cpp"),
        ]
        self.assertEqual(
            m.label_target(0x80296FD8+0x1394,entries),
            ("Pack/RPSports/RPGolScene/RPGolMapObjBall.cpp","+0x1394"))
        self.assertEqual(m.label_target(0x80296FD7,entries),(None,None))
        self.assertEqual(m.label_target(0x8029B240,entries),(None,None))

    def test_all_64_slots_resolved_without_promoting_physics(self):
        words,read,ram,u32,bank=prior.fixture()
        p=json.loads(m.MAP.read_text(encoding="utf-8"))
        entries=m.validated_intervals(p)
        x=m.examine(u32,prior.TREE_OBJECT,94,bank,entries)
        self.assertEqual(x["candidate_table_slots_bounded"],64)
        self.assertEqual(len(x["candidate_target_sites"]),64)
        self.assertGreaterEqual(x["resolved_code_target_count"],3)
        self.assertFalse(x["shared_firstword_is_true_cpp_vtable_proven"])
        self.assertFalse(x["table_entry_called_on_tree_from_ball_proven"])
        self.assertFalse(x["tree_collision_hitbox_proven"])
        self.assertFalse(x["training_approved"])
        self.assertTrue(m.native.tree_loop_source_gated(read))
        self.assertTrue(m.active.inspect_source(read))

    def test_94_source_tree_firstword_gate_abstains_if_changed(self):
        words,read,ram,u32,bank=prior.fixture()
        ram[prior.TREE_OBJECT+3*84]=prior.TABLE+4
        with self.assertRaises(ValueError):
            m.examine(u32,prior.TREE_OBJECT,94,bank,
                      m.validated_intervals(json.loads(m.MAP.read_text())))

    def test_wrong_public_revision_or_hash_fails_closed(self):
        raw=json.loads(m.MAP.read_text(encoding="utf-8"))
        for key,value in (("disc_revision",2),("source_blob_sha","0"*40)):
            changed=dict(raw)
            changed[key]=value
            with self.assertRaises(ValueError):
                m.validated_intervals(changed)

    def test_overlapping_or_reversed_source_map_abstains(self):
        raw=json.loads(m.MAP.read_text(encoding="utf-8"))
        for intervals in (list(reversed(raw["intervals"])),
                          raw["intervals"][:1]+raw["intervals"][:1]+raw["intervals"][1:]):
            changed=dict(raw)
            changed["intervals"]=intervals
            with self.assertRaises(ValueError):
                m.validated_intervals(changed)

    def test_outside_selected_units_not_claimed_noncode(self):
        words,read,ram,u32,bank=prior.fixture()
        table=prior.TABLE
        # Known selected-source-range outsider but actual public source .text.
        public=m.validated_intervals(json.loads(m.MAP.read_text()))
        target=next(lo for lo,hi,n in public if "nw4r/math/" in n)
        ram[table+16]=target
        x=m.examine(u32,prior.TREE_OBJECT,94,bank,public)
        self.assertTrue(x["candidate_target_sites"][4]["within_retained_public_text"])
        self.assertTrue(any("nw4r/math/" in k for k in
                            x["classification_counts_by_public_compilation_unit"]))
        self.assertFalse(x["table_entry_called_on_tree_from_ball_proven"])


if __name__=="__main__":
    unittest.main()
