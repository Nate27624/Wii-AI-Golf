"""Synthetic source-owned tree array stride and translation candidate tests."""
import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
p=SCRIPTS/"p0_tree_array_layout_private.py"
spec=importlib.util.spec_from_file_location("p0_tree_layout",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture(*,count=94,stride=0x58,valid=True,distinct=True):
    base=0x90001000
    words={}
    xyz={}
    vt=0x803C7788
    for i in range(count):
        at=base+i*stride
        words[at]=vt if valid or i<3 else 0
        words[at+4]=0x9000A000
        words[at+8]=0x9000B000
        xyz[at+0x30]=(float(i*3) if distinct else 1.,
                       float(i%3),
                       float(i*5) if distinct else 2.)
    def word(a):
        return words.get(a,0)
    def vec(a):
        return xyz.get(a,(float("nan"),)*3)
    def valid_mem(a,size):
        return 0x80000000<=a and a+size<=0x81800000 or (
            0x90000000<=a and a+size<=0x94000000)
    return word,vec,base,count,valid_mem


class TestPrivateTreeLayout(unittest.TestCase):
    def test_positive_stride_94_trees(self):
        word,vec,base,n,mem=fixture()
        result=m.study(word,vec,base,n,mem)
        self.assertEqual(result["status"],"STRUCTURAL_TREE_ARRAY_CANDIDATE")
        self.assertEqual(result["qualified_stride_candidates"][0]["candidate_stride_bytes"],0x58)
        self.assertEqual(result["qualified_stride_candidates"][0]["common_vtable_hits"],94)
        self.assertEqual(result["qualified_stride_candidates"][0]["distinct_translation_candidates"],94)

    def test_cannot_promote_true_positions(self):
        word,vec,base,n,mem=fixture()
        result=m.study(word,vec,base,n,mem)
        self.assertFalse(result["tree_position_world_alignment_verified"])
        self.assertFalse(result["actual_tree_models_verified"])
        self.assertFalse(result["training_approved"])

    def test_invalid_vtable_per_element_rejected(self):
        word,vec,base,n,mem=fixture(valid=False)
        result=m.study(word,vec,base,n,mem)
        self.assertEqual(result["status"],"TREE_LAYOUT_UNRESOLVED")

    def test_identical_coords_rejected(self):
        word,vec,base,n,mem=fixture(distinct=False)
        result=m.study(word,vec,base,n,mem)
        self.assertEqual(result["status"],"TREE_LAYOUT_UNRESOLVED")

    def test_real_tree_count_bounds(self):
        word,vec,base,n,mem=fixture()
        self.assertIsNone(m.probe_stride(word,vec,base,4097,0x58,memory_check=mem))
        self.assertIsNone(m.probe_stride(word,vec,base,2,0x58,memory_check=mem))

    def test_reject_invalid_stride(self):
        word,vec,base,n,mem=fixture()
        self.assertIsNone(m.probe_stride(word,vec,base,n,0x27,memory_check=mem))

    def test_reject_outside_mem_pointer(self):
        word,vec,base,n,mem=fixture()
        with self.assertRaises(ValueError):
            m.study(word,vec,0x50000000,n,mem)

    def test_return_never_contains_coords_or_vtable_addresses(self):
        word,vec,base,n,mem=fixture()
        import json
        raw=json.dumps(m.study(word,vec,base,n,mem))
        self.assertNotIn("214",raw)
        self.assertNotIn("2415",raw)
        self.assertNotIn("803C7788",raw)


if __name__=="__main__":
    unittest.main()
