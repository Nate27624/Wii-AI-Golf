"""Synthetic-only exact PPC and source-owned contiguous 84-byte tree array."""
import importlib.util
from pathlib import Path
import sys
import unittest

DIR=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(DIR))
spec=importlib.util.spec_from_file_location("tree_stride84",DIR/"p0_tree_stride84_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def native_fixture(*,count=94,stride=84,bad_position=None,
                   outlier=False, identical=False, zero_vtables=False):
    base=0x90008000
    words={}
    positions={}
    for i in range(count):
        at=base+i*stride
        words[at]=0 if zero_vtables else 0x803C6000
        words[at+4]=0x90050000
        words[at+8]=0x90060000
        positions[at+0x30]=(
            (1.,2.,3.) if identical else
            (float(i*12 + (50000 if outlier else 0)),
             float(i%7),
             float(i*16 + (50000 if outlier else 0))))
    if bad_position is not None:
        positions[base+bad_position*stride+0x30]=(float("nan"),0.,0.)
    def u32(at):
        return words.get(at,0)
    def vec(at):
        return positions.get(at,(float("nan"),)*3)
    def bank(at,n,name):
        if name=="MEM2":
            return 0x90000000 <= at and at+n<=0x94000000
        if name=="MEM1":
            return 0x80000000 <= at and at+n<=0x81800000
        return False
    return u32,vec,bank,base,count


class Tree84SourceTests(unittest.TestCase):
    def test_10_instruction_loop_fingerprint(self):
        self.assertEqual(len(m.CODE_FINGERPRINT),10)
        self.assertTrue(m.check_source_tree_loop(
            lambda pc:m.CODE_FINGERPRINT.get(pc-m.CODE_BASE,0)))

    def test_source_byte_change_fails(self):
        self.assertFalse(m.check_source_tree_loop(
            lambda pc:0 if pc==m.CODE_BASE+0x06F4 else
            m.CODE_FINGERPRINT.get(pc-m.CODE_BASE,0)))

    def test_verified_84byte_94_object_array_positions(self):
        w,v,b,base,n=native_fixture()
        report,pts=m.inspect_array(w,v,b,base,n,(0.,0.,0.),(400.,0.,600.))
        self.assertEqual(len(pts),94)
        self.assertEqual(report["source_proven_contiguous_stride_bytes"],84)
        self.assertEqual(report["finite_translation_triplets"],94)
        self.assertEqual(report["distinct_candidate_translations"],94)
        self.assertEqual(report["nonzero_bounded_model_pointer_candidates"],94)
        self.assertTrue(report["candidate_spatial_sanity_passed"])
        self.assertFalse(report["world_visual_alignment_verified"])

    def test_zero_vtables_not_automatically_abstain(self):
        w,v,b,base,n=native_fixture(zero_vtables=True)
        report,_=m.inspect_array(w,v,b,base,n,(0.,0.,0.),(0.,0.,0.))
        self.assertEqual(report["object_firstword_buckets"]["zero"],94)
        self.assertEqual(report["finite_translation_triplets"],94)

    def test_one_nan_prevents_full_candidate_promotion(self):
        w,v,b,base,n=native_fixture(bad_position=17)
        report,_=m.inspect_array(w,v,b,base,n,(0.,0.,0.),(0.,0.,0.))
        self.assertEqual(report["finite_translation_triplets"],93)
        self.assertFalse(report["candidate_spatial_sanity_passed"])

    def test_far_away_positions_not_promoted(self):
        w,v,b,base,n=native_fixture(outlier=True)
        report,_=m.inspect_array(w,v,b,base,n,(0.,0.,0.),(0.,0.,0.))
        self.assertEqual(report["near_source_tee_or_pin_count"],0)
        self.assertFalse(report["candidate_spatial_sanity_passed"])

    def test_identical_positions_not_promoted(self):
        w,v,b,base,n=native_fixture(identical=True)
        report,_=m.inspect_array(w,v,b,base,n,(0.,0.,0.),(0.,0.,0.))
        self.assertEqual(report["distinct_candidate_translations"],1)
        self.assertFalse(report["candidate_spatial_sanity_passed"])

    def test_array_bounds_bad(self):
        w,v,b,base,n=native_fixture()
        with self.assertRaises(ValueError):
            m.inspect_array(w,v,b,0x94000000,n,(0.,0.,0.),(0.,0.,0.))

    def test_tree_count_invalid(self):
        w,v,b,base,n=native_fixture()
        for count in (0,2,4097):
            with self.assertRaises(ValueError):
                m.inspect_array(w,v,b,base,count,(0.,0.,0.),(0.,0.,0.))

    def test_nan_tee_abstains(self):
        w,v,b,base,n=native_fixture()
        with self.assertRaises(ValueError):
            m.inspect_array(w,v,b,base,n,(float("nan"),0.,0.),(0.,0.,0.))

    def test_disclosed_result_contains_no_tree_positions(self):
        w,v,b,base,n=native_fixture()
        report,pt=m.inspect_array(w,v,b,base,n,(0.,0.,0.),(0.,0.,0.))
        import json
        result=json.dumps(report)
        self.assertNotIn("0x90008000",result)
        self.assertNotIn('"points"',result)
        self.assertNotIn('"positions"',result)
        self.assertFalse(report["collision_hitboxes_verified"])
        self.assertFalse(report["training_approved"])


if __name__=="__main__":
    unittest.main()
