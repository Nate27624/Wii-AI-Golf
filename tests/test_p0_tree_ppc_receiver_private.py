"""Small synthetic receiver and stack confounder checks."""
import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location("tree_receiver",SCRIPTS/"p0_tree_ppc_receiver_private.py")
r=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def op_d(op,rt,ra,imm):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm & 65535)


def mr(dst,src):
    return (31<<26)|(src<<21)|(dst<<16)|(src<<11)|(444<<1)


def fixture():
    b=r.BASE
    d={
        b+0x06E8:op_d(32,0,28,0x20),
        b+0x06FC:op_d(32,0,28,0x1C),
        b+0x06C8:mr(28,3),
        b+0x0140:op_d(36,0,1,0x20),
        b+0x01B0:op_d(36,0,1,0x1C),
    }
    return lambda pc:d.get(pc,0)


class TreePpcReceiver(unittest.TestCase):
    def test_exact_anchor_r28(self):
        x=r.inspect(fixture())
        self.assertEqual(len(x["field_window_loads"]),2)
        self.assertEqual(x["field_window_loads"][0]["receiver_register"],"r28")
        self.assertEqual(x["field_window_loads"][1]["member_offset"],"+0x1C")

    def test_last_register_assignment(self):
        x=r.inspect(fixture())
        first=x["field_window_loads"][0]["candidate_receiver_assignments"]
        self.assertEqual(first[-1]["assignment"],"mr")
        self.assertEqual(first[-1]["from"],"r3")
        self.assertEqual(first[-1]["distance_bytes"],0x20)

    def test_stack_writes_never_treated_as_field(self):
        x=r.inspect(fixture())
        self.assertTrue(x["stack_r1_writes_excluded"])
        self.assertFalse(any(p["shared_base_register"]=="r1"\n                             for p in x["nearest_nonstack_field_offset_pairs"]))

    def test_unknown_receiver_stays_false(self):
        x=r.inspect(fixture())
        self.assertFalse(x["receiver_dataflow_proven"])
        self.assertFalse(x["tree_layout_verified"])
        self.assertFalse(x["training_approved"])

    def test_dform_decodes_destination_and_receiver(self):
        self.assertEqual(r.dform(op_d(36,7,1,0x20)),
                         ("store",7,1,0x20))

    def test_mr_requires_identical_sources(self):
        self.assertEqual(r.r28_set(mr(28,3)),("mr","r3"))
        self.assertIsNone(r.r28_set(mr(27,3)))

    def test_bad_anchor_abstains(self):
        w=fixture()
        with self.assertRaises(ValueError):
            r.inspect(lambda pc: 0 if pc==r.BASE+0x06E8 else w(pc))

    def test_nearby_real_field_pair_is_hypothesis_only(self):
        old=fixture()
        lo=r.FIELD_LO
        d={lo+0xC0:op_d(32,8,29,0x20),
           lo+0xD0:op_d(32,9,29,0x1C)}
        x=r.inspect(lambda pc:d.get(pc,old(pc)))
        pairs=x["nearest_nonstack_field_offset_pairs"]
        self.assertTrue(any(p["shared_base_register"]=="r29" for p in pairs))
        self.assertFalse(pairs[0]["source_owner_verified"])

    def test_context_caps_to_three_assignments(self):
        old=fixture()
        b=r.BASE
        d={b+0x0660:mr(28,3),b+0x0670:mr(28,4),
           b+0x0680:mr(28,5),b+0x0690:mr(28,6)}
        x=r.inspect(lambda pc:d.get(pc,old(pc)))
        self.assertLessEqual(len(x["field_window_loads"][0]["candidate_receiver_assignments"]),3)

    def test_no_native_word_or_heap_pointer_output(self):
        import json
        raw=json.dumps(r.inspect(fixture()))
        self.assertNotIn("0x9000",raw)
        self.assertNotIn("0x8029",raw)


if __name__=="__main__":
    unittest.main()
