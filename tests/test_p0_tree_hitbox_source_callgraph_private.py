"""Synthetic-only source-PPC branch, float offset, and game-call triage."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location(
    "hitbox_audit",SCRIPTS/"p0_tree_hitbox_source_callgraph_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def branch(pc,target,*,link=True,absolute=False):
    diff=target if absolute else target-pc
    if diff%4 or not -(1<<25)<=diff<(1<<25):
        raise ValueError("Unrepresentable synthetic PPC branch")
    return (18<<26)|(diff & 0x03FFFFFC)|(int(absolute)<<1)|int(link)


def dform(op,rt,ra,off):
    return (op<<26)|(rt<<21)|(ra<<16)|(off&0xFFFF)


def words_fixture():
    w={}
    base=m.LOOP
    tree=m.UNITS["Tree"][0]
    # Exact verified loop semantics, but synthetic (not ROM fixture).
    w[base+0x06E8]=dform(32,0,28,0x20)
    w[base+0x06F0]=branch(base+0x06F0,tree+12)
    w[base+0x06F4]=dform(14,31,31,84)
    w[base+0x06FC]=dform(32,0,28,0x1C)
    # Synthetic tree-> utility collision and ball->Tree direct calls.
    tpc=tree+0x50
    cpc=m.UNITS["CollisionChecker"][0]+0x20
    w[tpc]=branch(tpc,cpc)
    ball=m.UNITS["Ball"][0]+0x140
    w[ball]=branch(ball,tree+0x80)
    w[ball+0x4]=dform(48,1,3,0x60)   # lfs
    w[ball+0x8]=(63<<26)              # fcmpu/fcmpo subop0
    w[tree+0x58]=dform(52,0,4,0x48)   # stfs
    w[tree+0x60]=0x4E800421           # bctrl, unknown dynamic target
    return w


class HitboxSourceAudit(unittest.TestCase):
    def test_public_source_unit_windows(self):
        self.assertEqual(m.UNITS["Tree"],(0x80296238,0x80296EA8))
        self.assertEqual(m.UNITS["Ball"],(0x80296FD8,0x8029B240))
        self.assertNotEqual(m.UNITS["GolfKCol"],m.UNITS["Ball"])

    def test_direct_branch_to_tree(self):
        ball=m.UNITS["Ball"][0]
        target=m.UNITS["Tree"][0]+12
        self.assertEqual(m.direct_b(ball,branch(ball,target)),(target,True))

    def test_unlinked_branch_is_not_call(self):
        ball=m.UNITS["Ball"][0]
        target=m.UNITS["Tree"][0]
        self.assertEqual(m.direct_b(ball,branch(ball,target,link=False)),(target,False))

    def test_branch_negative_sign_extension(self):
        ball=m.UNITS["Ball"][0]+0x100
        tree=m.UNITS["Tree"][0]+0x4
        self.assertEqual(m.direct_b(ball,branch(ball,tree)),(tree,True))

    def test_absolute_branch_target(self):
        # Absolute PPC branch target must be 26-bit; low public code target.
        pc=m.UNITS["Ball"][0]
        self.assertEqual(m.direct_b(pc,branch(pc,0x00003000,absolute=True)),
                         (0x3000,True))

    def test_indirect_call_target_not_guessed(self):
        self.assertEqual(m.indirect_call(0x4E800421),"branch_to_ctr")
        self.assertIsNone(m.indirect_call(0x4E800420))
        self.assertIsNone(m.indirect_call(0x4E800020))

    def test_tree_source_loop_passes(self):
        words=words_fixture()
        self.assertTrue(m.tree_loop_source_gated(lambda pc:words.get(pc,0)))

    def test_tree_loop_wrong_stride_fails(self):
        words=words_fixture()
        words[m.LOOP+0x06F4]=dform(14,31,31,80)
        self.assertFalse(m.tree_loop_source_gated(lambda pc:words.get(pc,0)))

    def test_tree_loop_wrong_callee_fails(self):
        words=words_fixture()
        pc=m.LOOP+0x06F0
        words[pc]=branch(pc,m.UNITS["GolfKCol"][0])
        self.assertFalse(m.tree_loop_source_gated(lambda pc:words.get(pc,0)))

    def test_tree_loop_bad_receiver_fails(self):
        words=words_fixture()
        words[m.LOOP+0x06E8]=dform(32,0,1,0x20)
        self.assertFalse(m.tree_loop_source_gated(lambda pc:words.get(pc,0)))

    def test_dform_offsets(self):
        self.assertEqual(m.dform(dform(48,2,3,0x30)),("lfs",2,3,48))
        self.assertEqual(m.dform(dform(52,0,4,-16)),("stfs",0,4,-16))

    def test_floating_compare(self):
        self.assertTrue(m.float_compare(63<<26))
        self.assertFalse(m.float_compare(0))

    def test_call_graph_links(self):
        words=words_fixture()
        out=m.scan_code(lambda pc:words.get(pc,0))
        edges={(e["caller"],e["callee"]):e for e in out["direct_calls_between_selected_units"]}
        self.assertIn(("FieldManager","Tree"),edges)
        self.assertIn(("Ball","Tree"),edges)
        self.assertIn(("Tree","CollisionChecker"),edges)
        self.assertEqual(edges[("Ball","Tree")]["count"],1)
        self.assertEqual(len(edges[("Tree","CollisionChecker")]["bounded_public_relative_sites"]),1)

    def test_float_and_indirect_not_overinterpreted(self):
        words=words_fixture()
        out=m.scan_code(lambda pc:words.get(pc,0))
        self.assertTrue(any(v["access"]=="lfs" and v["displacement_bytes"]==96
                            for v in out["candidate_floating_member_offsets"]["Ball"]))
        self.assertTrue(any(v["source"]=="Tree" and v["kind"]=="branch_to_ctr"
                            for v in out["indirect_calls_by_source"]))
        self.assertFalse(out["tree_collision_geometry_verified"])
        self.assertFalse(out["tree_ball_collision_call_path_verified"])
        self.assertFalse(out["training_approved"])

    def test_zero_direct_calls_does_not_assert_no_collision(self):
        out=m.scan_code(lambda pc:0)
        self.assertEqual(out["direct_calls_between_selected_units"],[])
        self.assertFalse(out["tree_collision_geometry_verified"])


if __name__ == "__main__":
    unittest.main()
