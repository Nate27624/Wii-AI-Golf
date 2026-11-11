"""Synthetic tests for 94 tree objects and bounded possible dispatch slots."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
import unittest
SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location("tree_dis",SCRIPTS/"p0_tree_hitbox_object_dispatch_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture(*,firstword=0x80300000,broken=False):
    base=0x90010000
    mem={}
    for i in range(94):
        obj=base+i*84
        mem[obj]=firstword
        mem[obj+4]=0
        mem[obj+8]=0
        mem[obj+0x40]=obj+0x0C
        mem[obj+0x44]=obj+0x30
    if broken:
        mem[base+0x44]=0
    vt=firstword
    mem[vt+0]=m.native.UNITS["Tree"][0]+0x100
    mem[vt+4]=m.native.UNITS["Ball"][0]+0x100
    def bank(addr,n,kind):
        return (0x80000000<=addr and addr+n<=0x81800000) if kind=="MEM1" else (0x90000000<=addr and addr+n<=0x94000000)
    return lambda x:mem.get(x,0),bank,base


class TreeObjectDispatchTests(unittest.TestCase):
    def test_94_firstwords_common_and_methods_not_promoted(self):
        read,bank,base=fixture()
        row=m.inspect_objects(read,bank,base,94)
        self.assertEqual(row["tree_count"],94)
        self.assertEqual(row["distinct_object_firstwords"],1)
        self.assertEqual(row["firstword_patterns"][0]["object_count"],94)
        self.assertEqual(row["firstword_patterns"][0]["public_method_candidates"][:2],
                         [{"slot":0,"target":"Tree+0x0100"},{"slot":1,"target":"Ball+0x0100"}])
        self.assertFalse(row["vtable_dispatch_verified"])
        self.assertFalse(row["tree_collision_geometry_verified"])

    def test_selfref_follows_object_stride_84(self):
        read,bank,base=fixture()
        row=m.inspect_objects(read,bank,base,94)
        self.assertEqual(row["rotation_self_reference_count"],94)
        self.assertEqual(row["translation_self_reference_count"],94)

    def test_missing_selfref_not_fatal(self):
        read,bank,base=fixture(broken=True)
        row=m.inspect_objects(read,bank,base,94)
        self.assertEqual(row["translation_self_reference_count"],93)

    def test_zero_firstwords_not_vtables(self):
        read,bank,base=fixture(firstword=0)
        row=m.inspect_objects(read,bank,base,94)
        self.assertEqual(row["firstword_patterns"][0]["firstword_class"],"zero")
        self.assertEqual(row["firstword_patterns"][0]["public_method_candidates"],[])

    def test_unaligned_firstword_not_vtable(self):
        read,bank,base=fixture(firstword=0x80300001)
        row=m.inspect_objects(read,bank,base,94)
        self.assertEqual(row["firstword_patterns"][0]["firstword_class"],"other_nonzero")

    def test_bad_array_bounds_abstain(self):
        read,bank,base=fixture()
        with self.assertRaises(ValueError):
            m.inspect_objects(read,bank,0x94000000,94)

    def test_bad_count_abstain(self):
        read,bank,base=fixture()
        with self.assertRaises(ValueError):
            m.inspect_objects(read,bank,93)

    def test_inline_mulli_84_in_ball_not_assumed_hitbox(self):
        base=m.native.UNITS["Ball"][0]
        w={base+0x100:(7<<26)|(4<<21)|(5<<16)|84,
           base+0x104:(14<<26)|(4<<21)|(4<<16)|84}
        summary=m.inline_stride(lambda a:w.get(a,0))
        self.assertEqual(summary["Ball"]["mulli_84"],["+0x0100"])
        self.assertEqual(summary["Ball"]["addi_84"],["+0x0104"])
        self.assertEqual(summary["Tree"]["mulli_count"],0)

    def test_output_no_actual_runtime_address_or_tree_xyz(self):
        import json
        read,bank,base=fixture()
        raw=json.dumps(m.inspect_objects(read,bank,base,94))
        self.assertNotIn("0x9001",raw)
        self.assertNotIn("0x80300000",raw)
        self.assertNotIn('"tree_positions"',raw)

    def test_tree_public_label(self):
        self.assertEqual(m.label(m.native.UNITS["Tree"][0]+0x40),"Tree+0x0040")
        self.assertIsNone(m.label(0x90000000))


if __name__=="__main__":
    unittest.main()
