"""Synthetic original PPC Ball→GolfKCol return context falsification tests."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
import unittest

DIR=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(DIR))
spec=importlib.util.spec_from_file_location(
    "ball_kcol_postcall",DIR/"p0_ball_kcol_postcall_context_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def bl(pc,target):
    delta=target-pc
    if delta%4 or not -(1<<25)<=delta<(1<<25):
        raise ValueError("PPC direct branch displacement unsupported")
    return (18<<26)|(delta&0x03FFFFFC)|1


def d(op,rt,ra,offset):
    return (op<<26)|(rt<<21)|(ra<<16)|(offset&65535)


def fixture():
    words={}
    blo=m.units.UNITS["Ball"][0]
    klo=m.units.UNITS["GolfKCol"][0]
    for i in range(5):
        site=blo+0x0400+0x400*i
        target=klo+0x0200+0x180*i
        words[site]=bl(site,target)
        words[site-4]=d(48,1,31,0x30)  # lfs f1,0x30(r31)
        words[site+4]=d(32,3,30,0x40)  # lwz r3,0x40(r30)
        words[site+8]=d(11,0,3,0)      # cmpwi r3,0
        words[site+12]=(16<<26)|(12<<21)|(2<<16)|0x000C
        words[site+16]=d(52,1,31,0x54) # stfs f1,+0x54(r31)
        words[target]=d(48,1,3,0x54)
        words[target+4]=d(40,4,3,0x1C)
    for i in range(7):
        site=klo+0x1800+0x200*i
        target=blo+0x2600+0x120*i
        words[site]=bl(site,target)
    return words, lambda at:words.get(at,0)


class BallKcolPostCallTests(unittest.TestCase):
    def test_original_5_plus_7_source_edges(self):
        words,read=fixture()
        r=m.inspect(read)
        self.assertEqual(r["status"],"ORIGINAL_BALL_KCOL_POSTCALL_CONTEXT")
        self.assertEqual(len(r["call_contexts"]),5)
        self.assertEqual(r["source_ball_to_kcol_call_count"],5)
        self.assertEqual(len(r["distinct_kcol_target_function_entry_offsets"]),5)
        self.assertEqual([x["calls"] for x in r["native_direct_call_gate"]],[5,7])

    def test_bounded_code_snapshots_have_expected_lengths(self):
        words,read=fixture()
        rows=m.inspect(read,detail=True)["call_contexts"]
        for row in rows:
            self.assertEqual(len(row["local_caller_code_lines"]),m.BEFORE+1+m.AFTER)
            self.assertEqual(len(row["local_callee_code_lines"]),m.TARGET)
            self.assertTrue(row["local_caller_code_lines"][0].startswith("Ball+0x"))
            self.assertTrue(row["local_callee_code_lines"][0].startswith("GolfKCol+0x"))

    def test_syntactic_status_not_assigned_to_collision_result(self):
        words,read=fixture()
        row=m.inspect(read)["call_contexts"][0]
        syntax=row["post_call_status_syntax"]
        self.assertTrue(any(c["kind"]=="integer_immediate_comparison" and
                            c["register"]=="r3"
                            for c in syntax["post_call_syntactic_compares"]))
        self.assertTrue(any(s["op"]=="stfs" for s in syntax["post_call_syntactic_stores"]))
        self.assertTrue(any(x["class"]=="conditional" for x in syntax["post_call_branches"]))
        self.assertFalse(syntax["return_value_dataflow_verified"])
        self.assertFalse(syntax["ball_velocity_store_verified"])
        self.assertFalse(syntax["tree_or_obstacle_collision_verified"])

    def test_no_ball_contact_claim_anywhere(self):
        words,read=fixture()
        r=m.inspect(read)
        self.assertFalse(r["native_kcl_resource_used_by_ball_verified"])
        self.assertFalse(r["tree_hitbox_or_collision_shape_verified"])
        self.assertFalse(r["ball_contact_response_verified"])
        self.assertFalse(r["training_approved"])
        self.assertTrue(all(not x["ball_velocity_mutation_proven"]
                            for x in r["call_contexts"]))

    def test_missing_forward_edge_abstains(self):
        words,read=fixture()
        words[m.units.UNITS["Ball"][0]+0x400]=0
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_missing_reverse_edge_abstains(self):
        words,read=fixture()
        words[m.units.UNITS["GolfKCol"][0]+0x1800]=0
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_extra_forward_edge_abstains(self):
        words,read=fixture()
        caller=m.units.UNITS["Ball"][0]+0x3600
        target=m.units.UNITS["GolfKCol"][0]+0x0F00
        words[caller]=bl(caller,target)
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_synthetic_indirect_branch_not_called_a_direct_callee(self):
        words,read=fixture()
        at=m.units.UNITS["Ball"][0]+0x400
        words[at]=0x4E800421
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_branch_is_bounded_does_not_walk_next_function(self):
        words,read=fixture()
        site=m.units.UNITS["Ball"][0]+0x400
        words[site+4]=(18<<26)|0x18
        row=m.inspect(read)["call_contexts"][0]
        self.assertEqual(len(row["post_call_status_syntax"]["post_call_branches"]),1)

    def test_details_not_implicitly_emitted(self):
        words,read=fixture()
        import json
        data=json.dumps(m.inspect(read))
        self.assertNotIn("local_caller_code_lines",data)
        self.assertNotIn("local_callee_code_lines",data)
        self.assertNotIn("0x9000",data)
        self.assertNotIn("tree_positions",data)

    def test_callsite_source_offsets_only(self):
        words,read=fixture()
        r=m.inspect(read)
        self.assertEqual(r["call_contexts"][0]["caller_site"],"+0x0400")
        self.assertEqual(r["call_contexts"][0]["callee_site"],"+0x0200")
        for item in r["call_contexts"]:
            self.assertTrue(item["callee_site"].startswith("+0x"))
            self.assertFalse(item["return_type_proven"])


if __name__=="__main__":
    unittest.main()
