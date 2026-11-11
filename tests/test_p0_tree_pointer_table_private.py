"""Synthetic, no-Dolphin tests for source-owned tree pointer table layouts."""
import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location("p0_tree_ptr",SCRIPTS/"p0_tree_pointer_table_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture(*, count=94, stride=4, offset=0, valid=94,
            duplicate=False, tree_vtables=2, bad_positions=False):
    base=0x90002000
    words={0x803C7100:0x80122220,0x803C7104:0x80133330,
           0x803C7200:0x80144440,0x803C7204:0x80155550}
    positions={}
    for i in range(count):
        address=0x90004000 + (i if not duplicate else 0) * 0x100
        words[base+i*stride+offset] = address if i < valid else 0
        words[address] = 0x803C7100 if (tree_vtables==1 or i%2==0) else 0x803C7200
        words[address+4] = 0x9004A000
        words[address+8] = 0x9004B000
        words[address+0x4C] = address+0x30
        positions[address+0x30] = ((float(i),float(i%4),float(i*2))
                                   if not bad_positions else (float("nan"),0.,0.))
    def word(addr): return words.get(addr,0)
    def vec(addr): return positions.get(addr,(float("nan"),)*3)
    def bank(addr,n,name):
        if type(addr) is not int or addr < 0 or n < 0:
            return False
        if name=="MEM1": return 0x80000000<=addr and addr+n<=0x81800000
        if name=="MEM2": return 0x90000000<=addr and addr+n<=0x94000000
        return False
    return word,vec,bank,base,count


class TreePointerTableTests(unittest.TestCase):
    def test_valid_94_two_tree_variants_4byte_pointer_table(self):
        w,v,b,base,n=fixture()
        x=m.study(w,v,b,base,n)
        self.assertEqual(x["status"],"POINTER_TABLE_STRUCTURAL_CANDIDATE")
        self.assertEqual(x["qualified_table_hypotheses"][0]["table_stride_bytes"],4)
        self.assertEqual(x["qualified_table_hypotheses"][0]["unique_object_pointers"],94)
        self.assertEqual(x["qualified_table_hypotheses"][0]["top_two_vtable_objects"],94)

    def test_valid_8byte_table_with_inline_auxiliary(self):
        w,v,b,base,n=fixture(stride=8)
        x=m.study(w,v,b,base,n)
        self.assertEqual(x["status"],"POINTER_TABLE_STRUCTURAL_CANDIDATE")
        self.assertEqual(x["qualified_table_hypotheses"][0]["table_stride_bytes"],8)

    def test_nonzero_ref_offset_detected(self):
        w,v,b,base,n=fixture(stride=12,offset=4)
        x=m.study(w,v,b,base,n)
        self.assertEqual(x["status"],"POINTER_TABLE_STRUCTURAL_CANDIDATE")
        self.assertEqual(x["qualified_table_hypotheses"][0]["table_pointer_offset_bytes"],4)

    def test_underqualified_rows_not_promoted(self):
        w,v,b,base,n=fixture(valid=23)
        x=m.study(w,v,b,base,n)
        self.assertEqual(x["status"],"POINTER_TABLE_UNRESOLVED")

    def test_repeated_single_pointer_not_94_objects(self):
        w,v,b,base,n=fixture(duplicate=True)
        x=m.study(w,v,b,base,n)
        self.assertEqual(x["status"],"POINTER_TABLE_UNRESOLVED")

    def test_nonfinite_xyz_not_qualified(self):
        w,v,b,base,n=fixture(bad_positions=True)
        x=m.study(w,v,b,base,n)
        self.assertEqual(x["status"],"POINTER_TABLE_UNRESOLVED")

    def test_bad_vtable_no_refs_fails(self):
        w,v,b,base,n=fixture()
        def broken(addr):
            if addr in (0x803C7100,0x803C7104,0x803C7200,0x803C7204):
                return 0
            return w(addr)
        x=m.study(broken,v,b,base,n)
        self.assertEqual(x["status"],"POINTER_TABLE_UNRESOLVED")

    def test_reject_invalid_array_range(self):
        w,v,b,base,n=fixture()
        self.assertIsNone(m.check_table(w,v,b,0x51000000,n,4,0))

    def test_unknown_stride_not_tested(self):
        w,v,b,base,n=fixture()
        self.assertIsNone(m.check_table(w,v,b,base,n,7,0))

    def test_invalid_count_fails(self):
        w,v,b,base,n=fixture()
        self.assertIsNone(m.check_table(w,v,b,base,0,4,0))

    def test_no_private_positions_or_pointers_in_output(self):
        w,v,b,base,n=fixture()
        import json
        output=json.dumps(m.study(w,v,b,base,n))
        for forbidden in ("0x9000","0x803C", "0x8012", "90004000"):
            self.assertNotIn(forbidden,output)
        self.assertFalse(m.study(w,v,b,base,n)["actual_tree_coordinates_verified"])
        self.assertFalse(m.study(w,v,b,base,n)["training_approved"])


if __name__=="__main__":
    unittest.main()
