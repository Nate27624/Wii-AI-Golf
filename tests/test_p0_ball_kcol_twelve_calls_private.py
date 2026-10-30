"""Synthetic-only cross Ball/KCol source calls and bounded context controls."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location("ball_kcol",SCRIPTS/"p0_ball_kcol_twelve_calls_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def bl(pc,target):
    delta=target-pc
    if not -(1<<25)<=delta<(1<<25) or delta&3:
        raise ValueError
    return (18<<26)|(delta & 0x03FFFFFC)|1


def lwz(reg,base,off):
    return (32<<26)|(reg<<21)|(base<<16)|(off&65535)


def lfs(reg,base,off):
    return (48<<26)|(reg<<21)|(base<<16)|(off&65535)


def stfs(reg,base,off):
    return (52<<26)|(reg<<21)|(base<<16)|(off&65535)


def source():
    w={}
    for owner,dest,count in m.EDGES:
        base=m.links.UNITS[owner][0]
        dbase=m.links.UNITS[dest][0]
        for i in range(count):
            site=base+0x100+i*0x100
            target=dbase+0x900+i*0x40
            w[site]=bl(site,target)
            w[site-4]=lfs(1,3,0x30)
            w[site+4]=stfs(1,3,0x54)
    return w,lambda pc:w.get(pc,0)


class BallKColReceiverTests(unittest.TestCase):
    def test_twelve_links_and_exact_counts(self):
        words,read=source()
        r=m.inspect(read)
        self.assertEqual(len(r["calls"]),12)
        self.assertEqual(r["pair_counts"][0]["calls"],5)
        self.assertEqual(r["pair_counts"][1]["calls"],7)
        self.assertEqual(r["status"],"BALL_GOLFKCOL_DIRECT_CALLS_SOURCE_AUDITED")
        self.assertTrue(r["tree_math_helpers_not_hitboxes"])

    def test_nearby_float_offsets_are_only_clues(self):
        words,read=source()
        r=m.inspect(read)
        for row in r["calls"]:
            self.assertEqual(row["caller_fp_load_store_prior_10"],{"lfs":1})
            self.assertEqual(row["caller_fp_load_store_after_8"],{"stfs":1})
            self.assertFalse(row["tree_hitbox_verified"])

    def test_full_detail_has_bound(self):
        words,read=source()
        r=m.inspect(read,detail=True)
        self.assertEqual(len(r["calls"]),12)
        for row in r["calls"]:
            self.assertEqual(len(row["caller_code"]),19)
            self.assertEqual(len(row["callee_code"]),14)

    def test_zero_edge_abstains(self):
        with self.assertRaises(ValueError):
            m.inspect(lambda pc:0)

    def test_one_missing_link_abstains(self):
        words,read=source()
        pc=m.links.UNITS["Ball"][0]+0x100
        with self.assertRaises(ValueError):
            m.inspect(lambda a:0 if a==pc else read(a))

    def test_wrong_target_no_promote(self):
        words,read=source()
        pc=m.links.UNITS["Ball"][0]+0x100
        bad=m.links.UNITS["Tree"][0]
        with self.assertRaises(ValueError):
            m.inspect(lambda a:bl(pc,bad) if a==pc else read(a))

    def test_unlinked_jump_no_count(self):
        words,read=source()
        pc=m.links.UNITS["Ball"][0]+0x100
        with self.assertRaises(ValueError):
            m.inspect(lambda a:read(a)&~1 if a==pc else read(a))

    def test_routine_explicitly_marks_unverified_physics(self):
        words,read=source()
        r=m.inspect(read)
        self.assertFalse(r["ball_tree_collision_path_verified"])
        self.assertFalse(r["native_hitbox_geometry_verified"])
        self.assertFalse(r["native_contact_response_verified"])
        self.assertFalse(r["training_approved"])

    def test_code_outputs_only_public_source_offsets(self):
        words,read=source()
        r=m.inspect(read,detail=True)
        s="\n".join(r["calls"][0]["caller_code"])
        self.assertIn("Ball+0x",s)
        self.assertNotIn("0x9000",s)

    def test_requires_exact_original_pair_counts_not_approximate(self):
        words,read=source()
        pc=m.links.UNITS["GolfKCol"][0]+0xD00
        target=m.links.UNITS["Ball"][0]+0xF00
        w=dict(words);w[pc]=bl(pc,target)
        with self.assertRaises(ValueError):
            m.inspect(lambda at:w.get(at,0))

    def test_no_count_promotion_if_non_strict_synthetic_only(self):
        r=m.inspect(lambda pc:0,strict=False)
        self.assertEqual(r["calls"],[])
        self.assertFalse(r["native_hitbox_geometry_verified"])


if __name__=="__main__":
    unittest.main()
