"""Synthetic-only original PPC two 94-tree loops and true receiver source gates."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location(
    "tree_second_loop",SCRIPTS/"p0_tree_second_loop_geometry_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def bl(pc,target):
    delta=target-pc
    if delta&3 or not -(1<<25)<=delta<(1<<25):
        raise ValueError("PPC branch not representable")
    return (18<<26)|(delta&0x03FFFFFC)|1


def d(op,rt,ra,off):
    return (op<<26)|(rt<<21)|(ra<<16)|(off&65535)


def fake_source():
    words=dict(m.prior.ANCHORS)
    for pc,target in m.prior.TARGETS.values():
        words[pc]=bl(pc,target)
    tree=m.TREE
    fm=m.FIELD
    ball=m.native.UNITS["Ball"][0]
    loop=m.native.LOOP
    sq=m.prior.proximity.DISTANCE_FN
    words.update({
        loop+0x06E8:d(32,0,28,0x20),
        loop+0x06F0:bl(loop+0x06F0,tree+0x0C),
        loop+0x06F4:d(14,31,31,84),
        loop+0x06FC:d(32,0,28,0x1C),
        tree+0x0020:0x38630030,
        tree+0x0030:bl(tree+0x0030,sq),
        tree+0x0034:0xC002C5C0,
        tree+0x0038:0xFC010040,
        tree+0x0044:0x981F0048,
        ball+0x0750:bl(ball+0x0750,sq),
        ball+0x0760:bl(ball+0x0760,sq),
    })
    words.update(m.ANCHORS)
    for pc,target in m.LINKS.items():
        words[pc]=bl(pc,target)
    # Native second-loop method prologue and receiver assignment.
    words[fm+0x2138]=d(37,1,1,-64)
    words[fm+0x214C]=0x7C7F1B78
    words[fm+0x1E00]=d(37,1,1,-64)
    words[fm+0x1E10]=0x7C7F1B78
    return words, lambda pc:words.get(pc,0)


class TreeSecondLoopTests(unittest.TestCase):
    def test_expected_exact_public_source_windows(self):
        words,read=fake_source()
        result=m.inspect(read)
        self.assertEqual([w["words"] for w in result["windows"]],
                         [12,15,12,106,36,28])
        self.assertEqual(sum(w["words"] for w in result["windows"]),209)
        self.assertTrue(result["read_loop_and_flag_writer_use_same_plus_0x20_array_field"])
        self.assertTrue(result["both_loops_use_84_byte_element_stride"])

    def test_not_proven_ball_contact_or_tree_receiver(self):
        words,read=fake_source()
        result=m.inspect(read)
        self.assertFalse(result["native_r31_is_fieldmanager_verified"])
        self.assertFalse(result["tree_plus_0x047c_receiver_identity_verified"])
        self.assertFalse(result["tree_hitbox_geometry_verified"])
        self.assertFalse(result["ball_contact_response_verified"])
        self.assertFalse(result["training_approved"])

    def test_original_two_native_calls_same_array_offsets(self):
        words,read=fake_source()
        self.assertEqual(m.native.direct_b(
            m.FIELD+0x230C,read(m.FIELD+0x230C)),(m.TREE+0x047C,True))
        self.assertEqual(m.native.direct_b(
            m.FIELD+0x2BB4,read(m.FIELD+0x2BB4)),(m.TREE+0x000C,True))

    def test_second_loop_entry_receiver_anchor(self):
        words,read=fake_source()
        row=m.inspect(read)
        self.assertEqual(row["r31_assigned_from_method_r3_at_source_relative"],"+0x214C")
        self.assertTrue(row["second_loop_within_same_native_method_frame"])
        words[m.FIELD+0x214C]=0
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_unexpected_nested_frame_abstains(self):
        words,read=fake_source()
        words[m.FIELD+0x2200]=d(37,1,1,-48)
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_wrong_array_field_abstains(self):
        words,read=fake_source()
        words[m.FIELD+0x2300]=d(32,0,31,0x24)
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_wrong_stride_abstains(self):
        words,read=fake_source()
        words[m.FIELD+0x2310]=d(14,26,26,80)
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_wrong_global_argument_abstains(self):
        words,read=fake_source()
        words[m.FIELD+0x22F8]=d(32,29,3,0x10)
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_wrong_tree_callee_abstains(self):
        words,read=fake_source()
        pc=m.TREE+0x04EC
        words[pc]=bl(pc,0x8029BE44)
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_preamble_candidates_not_source_proof(self):
        words,read=fake_source()
        row=m.inspect(read)["r31_preamble_search"]
        self.assertIn("+0x1E10",row["candidate_mr_r31_r3_sites"])
        self.assertIn("+0x1E00",row["candidate_stack_prologue_sites"])
        self.assertFalse(row["reader_r31_source_fieldmanager_proven"])

    def test_optional_detail_bounds(self):
        words,read=fake_source()
        result=m.inspect(read,detail=True)
        for w in result["windows"]:
            self.assertEqual(len(w["code"]),w["words"])
            self.assertTrue(w["code"][0].startswith(w["public_source_owner"]+"+0x"))
        self.assertEqual(len(result["windows"]),6)

    def test_default_has_no_native_hex(self):
        import json
        words,read=fake_source()
        output=json.dumps(m.inspect(read))
        self.assertNotIn("operator_local_code_lines",output)
        self.assertNotIn('"code"',output)
        self.assertNotIn("0x9000",output)
        self.assertNotIn("tree_positions",output)


if __name__=="__main__":
    unittest.main()
