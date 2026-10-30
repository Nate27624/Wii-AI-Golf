"""Synthetic PPC source windows for five Wii Golf Ball/KCol -> Tree calls."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location("hitbox_calls",SCRIPTS/"p0_tree_hitbox_five_calls_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def b(pc,target,link=True):
    delta=target-pc
    if delta&3 or not -(1<<25)<=delta<(1<<25):
        raise ValueError
    return (18<<26)|(delta&0x03FFFFFC)|int(link)


def d(op,rt,ra,off):
    return (op<<26)|(rt<<21)|(ra<<16)|(off&65535)


def fixture():
    w={}
    # Exactly five audited callsites and separate tree target functions.
    for i,(caller,offs) in enumerate(m.FOCUSED_SITES.items()):
        for j,off in enumerate(offs):
            pc=m.links.UNITS[caller][0]+off
            w[pc]=b(pc,m.links.UNITS["Tree"][0]+0x20+(i*3+j)*0x40)
            w[pc-4]=d(32,3,28,0x20)
            w[pc+4]=d(48,0,3,0x30)
    return lambda pc:w.get(pc,0)


class TreeFiveCallsTests(unittest.TestCase):
    def test_five_source_callsite_locations(self):
        self.assertEqual(m.FOCUSED_SITES["Ball"],(0x025C,0x02C0,0x231C))
        self.assertEqual(m.FOCUSED_SITES["GolfKCol"],(0x1FC8,0x21D4))
        self.assertEqual(sum(len(v) for v in m.FOCUSED_SITES.values()),5)

    def test_all_five_call_targets_resolved(self):
        rows=m.inspect(fixture())
        self.assertEqual(len(rows),5)
        self.assertTrue(all(r["tree_source_target"].startswith("Tree+") for r in rows))
        self.assertTrue(all("*** call to Tree" in " ".join(r["caller_instructions"])
                            for r in rows))

    def test_context_capped_and_not_optimized_away(self):
        rows=m.inspect(fixture())
        for r in rows:
            self.assertEqual(len(r["caller_instructions"]),21)
            self.assertEqual(len(r["target_entry_instructions"]),18)
            self.assertFalse(r["hitbox_semantics_verified"])

    def test_bad_call_target_rejected(self):
        normal=fixture()
        site=m.links.UNITS["Ball"][0]+0x025C
        new_target=m.links.UNITS["GolfKCol"][0]
        with self.assertRaises(ValueError):
            m.inspect(lambda pc:b(pc,new_target) if pc==site else normal(pc))

    def test_unlinked_branch_rejected(self):
        normal=fixture()
        site=m.links.UNITS["Ball"][0]+0x025C
        target=m.links.UNITS["Tree"][0]+0x20
        with self.assertRaises(ValueError):
            m.inspect(lambda pc:b(pc,target,False) if pc==site else normal(pc))

    def test_non_branch_rejected(self):
        normal=fixture()
        site=m.links.UNITS["Ball"][0]+0x025C
        with self.assertRaises(ValueError):
            m.inspect(lambda pc:d(32,3,28,0x20) if pc==site else normal(pc))

    def test_source_labels_never_call_native_rom_target_raw(self):
        pc=m.links.UNITS["Tree"][0]+0x20
        self.assertEqual(m.source_label(pc),"Tree+0x0020")
        self.assertEqual(m.source_label(0x80000000),"outside_public_relevant_units")

    def test_decode_prologue_and_float(self):
        self.assertEqual(m.ppc(0,d(37,1,1,-64)),"stwu r1,-64(r1)")
        self.assertEqual(m.ppc(0,d(48,0,3,0x30)),"lfs f0,+48(r3)")
        self.assertEqual(m.ppc(0,d(52,0,3,0x34)),"stfs f0,+52(r3)")

    def test_decode_float_comparison(self):
        self.assertTrue(m.ppc(0,(63<<26)).startswith("fcmpu"))

    def test_decode_mr(self):
        w=(31<<26)|(3<<21)|(28<<16)|(3<<11)|(444<<1)
        self.assertEqual(m.ppc(0,w),"mr r28,r3")

    def test_out_of_unit_callee_rejected(self):
        normal=fixture()
        site=m.links.UNITS["GolfKCol"][0]+0x21D4
        target=m.links.UNITS["Tree"][1]-4
        with self.assertRaises(ValueError):
            m.inspect(lambda pc:b(pc,target) if pc==site else normal(pc))

    def test_real_source_offsets_not_absolute_printed(self):
        rows=m.inspect(fixture())
        text="\n".join(r["caller_source_site"]+"".join(r["caller_instructions"])
                       for r in rows)
        self.assertIn("Ball+0x025C",text)
        self.assertNotIn("0x9000",text)
        self.assertNotIn("training_approved=true",text)


if __name__=="__main__":
    unittest.main()
