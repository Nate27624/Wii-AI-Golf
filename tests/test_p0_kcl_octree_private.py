"""KCL octree tests: synthetic bytes only, never game data or Dolphin."""
import importlib.util
from pathlib import Path
import struct
import sys
import unittest
import math

HERE=Path(__file__).resolve().parents[1]/'scripts'
for name in ('p0_kcl_private_probe','p0_kcl_octree_private'):
    spec=importlib.util.spec_from_file_location(name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
import p0_kcl_octree_private as o


def fixture(n=25, *, branch=False):
    b=bytearray(8192)
    po=0x3c; no=po+36; pro=no+4*12-0x10; octo=pro+0x10+n*0x10
    struct.pack_into('>IIII',b,0,po,no,pro,octo)
    struct.pack_into('>f',b,0x10,3.0)
    struct.pack_into('>fff',b,0x14,-100.,-2.,-100.)
    struct.pack_into('>III',b,0x20,0xfffffff0,0xfffffff0,0xfffffff0)
    struct.pack_into('>III',b,0x2c,4,0,0)
    for i,xyz in enumerate(((0,0,0),(1,0,1),(2,0,2))):
        struct.pack_into('>fff',b,po+i*12,*xyz)
    normals=[(0,1,0),(1,0,0),(0,0,1),(math.sqrt(.5),0,math.sqrt(.5))]
    for i,xyz in enumerate(normals):
        struct.pack_into('>fff',b,no+i*12,*xyz)
    for i in range(n):
        struct.pack_into('>fHHHHHH',b,pro+0x10+i*0x10,7.0710678,i%3,0,1,2,3,2)
    if branch:
        struct.pack_into('>I',b,octo,0x20)
        for i in range(8):
            struct.pack_into('>I',b,octo+0x20+i*4,0x80000040)
        list_off=octo+0x20+0x40
    else:
        struct.pack_into('>I',b,octo,0x80000020)
        list_off=octo+0x20
    struct.pack_into('>H',b,list_off,0)
    for i in range(1,n+1):
        struct.pack_into('>H',b,list_off+2*i,i)
    struct.pack_into('>H',b,list_off+2*(n+1),0)
    return b,octo,list_off


class OctreeTests(unittest.TestCase):
    def test_root_leaf_references_all(self):
        buf,_,_=fixture()
        d=o.inspect_octree(buf,0)
        self.assertTrue(d['octree_candidate_structurally_valid'])
        self.assertEqual(d['root_entry_count'],1)
        self.assertEqual(d['reachable_leaf_lists'],1)
        self.assertEqual(d['distinct_prisms_referenced'],25)
        self.assertTrue(d['all_candidate_prisms_referenced'])
        self.assertFalse(d['Wii_Sports_runtime_octree_usage_verified'])
    def test_branch_traversal_shared_leaf(self):
        buf,_,_=fixture(branch=True)
        d=o.inspect_octree(buf,0)
        self.assertEqual(d['reachable_branch_blocks'],1)
        self.assertEqual(d['reachable_leaf_lists'],1)
        self.assertEqual(d['max_octree_depth'],1)
        self.assertEqual(d['distinct_prisms_referenced'],25)
    def test_invalid_leaf_reference(self):
        buf,_,start=fixture()
        struct.pack_into('>H',buf,start+2*4,26)
        with self.assertRaises(o.OctreeInvalid):
            o.inspect_octree(buf,0)
    def test_missing_leading_zero_is_not_silent_pass(self):
        buf,_,start=fixture()
        struct.pack_into('>H',buf,start,1)
        with self.assertRaises(o.OctreeUnsupported):
            o.inspect_octree(buf,0)
    def test_root_shift_mismatch(self):
        buf,_,_=fixture()
        struct.pack_into('>I',buf,0x30,3)
        with self.assertRaises(o.OctreeUnsupported):
            o.inspect_octree(buf,0)
    def test_root_dimensions_more_than_one(self):
        buf,octo,_=fixture(n=25)
        struct.pack_into('>I',buf,0x20,0xffffffe0) # width5 / root shift4 => 2 roots
        struct.pack_into('>I',buf,0x30,1)
        struct.pack_into('>I',buf,octo+4,0x80000020)
        d=o.inspect_octree(buf,0)
        self.assertEqual(d['root_entry_count'],2)
    def test_noncontiguous_mask_variant(self):
        buf,_,_=fixture()
        struct.pack_into('>I',buf,0x20,0xfffffff5)
        with self.assertRaises(o.OctreeUnsupported):
            o.inspect_octree(buf,0)
    def test_branch_cycle_rejected(self):
        buf,octo,_=fixture(branch=True)
        struct.pack_into('>I',buf,octo+0x20,0)
        with self.assertRaises(o.OctreeInvalid):
            o.inspect_octree(buf,0)
    def test_empty_leaf_rejected_if_all(self):
        buf,_,start=fixture()
        struct.pack_into('>H',buf,start+2,0)
        with self.assertRaises(o.OctreeInvalid):
            o.inspect_octree(buf,0)
    def test_no_raw_indices_or_coordinates_exposed(self):
        buf,_,_=fixture()
        d=o.inspect_octree(buf,0)
        self.assertTrue(all(isinstance(v,(str,bool,int)) for v in d.values()))
        self.assertFalse(any('address' in key or 'word' in key or 'vertex' in key
                             for key in d))
    def test_point_outside_bounded_octree_rejected(self):
        buf,octo,_=fixture()
        struct.pack_into('>I',buf,octo,0x800000ff)
        with self.assertRaises((o.OctreeUnsupported,o.OctreeInvalid)):
            o.inspect_octree(buf,0,max_octree_bytes=64)


if __name__=='__main__':
    unittest.main()
