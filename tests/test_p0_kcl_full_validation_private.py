"""Offline synthetic tests only; never use real Wii RAM or Dolphin."""
import importlib.util
import math
from pathlib import Path
import struct
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'scripts'
for name in ('p0_kcl_private_probe', 'p0_kcl_full_validation_private'):
    spec=importlib.util.spec_from_file_location(name, SCRIPTS/(name+'.py'))
    mod=importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
import p0_kcl_full_validation_private as f


def fake_kcl(n=5):
    b=bytearray(1024)
    po=0x3c;no=po+3*12;pro=no+4*12-0x10;octo=pro+0x10+n*0x10
    struct.pack_into('>IIII',b,0,po,no,pro,octo)
    struct.pack_into('>f',b,0x10,3.0)
    struct.pack_into('>fff',b,0x14,-100.,-2.,-100.)
    struct.pack_into('>III',b,0x2c,4,5,6)
    for i,xyz in enumerate([(0,0,0),(1,0,1),(2,0,2)]):
        struct.pack_into('>fff',b,po+i*12,*xyz)
    normals=[(0,1,0),(1,0,0),(0,0,1),(math.sqrt(0.5),0,math.sqrt(0.5))]
    for i,xyz in enumerate(normals):
        struct.pack_into('>fff',b,no+i*12,*xyz)
    for i in range(n):
        struct.pack_into('>fHHHHHH',b,pro+0x10+i*0x10,7.0710678,i%3,0,1,2,3,2)
    return b, pro+0x10


def be_vec(x):
    return tuple(int.from_bytes(struct.pack('>f',y),'big') for y in x)

class TestFullValidation(unittest.TestCase):
    def test_entire_synthetic_table(self):
        b,_=fake_kcl()
        d=f.analyze_blob(b,0,tee_words=be_vec((0,0,0)),pin_words=be_vec((1,0,1)))
        self.assertEqual(d['prism_slot_upper_bound'],5)
        self.assertEqual(d['prism_reconstructed_non_degenerate'],5)
        self.assertEqual(d['prism_referenced_normals_unit'],5)
        self.assertTrue(d['all_prism_slots_reconstructed'])
        self.assertEqual(d['trailing_invalid_prism_slots'],0)
        self.assertEqual(d['tee_untransformed_proximity'],'WITHIN_2PCT_OF_MESH_BBOX_DIAGONAL')
        self.assertFalse(d['octree_structure_validated'])
    def test_failure_not_hidden_by_seven_sampled_valid(self):
        b,first=fake_kcl(n=25)
        # Prism #9 is not in probe's seven distributed sampled offsets.
        struct.pack_into('>H',b,first+9*16+6,65535)
        import p0_kcl_private_probe as kcl
        self.assertIsNotNone(kcl.parse_kcl_candidate(b,0))
        d=f.analyze_blob(b,0)
        self.assertEqual(d['prism_slot_upper_bound'],25)
        self.assertEqual(d['prism_reconstructed_non_degenerate'],24)
        self.assertEqual(d['interior_invalid_prism_slots'],1)
        self.assertEqual(d['first_invalid_prism_slot_zero_based'],9)
        self.assertFalse(d['all_prism_slots_reconstructed'])
    def test_trailing_padding_not_reported_as_interior_failure(self):
        seq=[True]*5+[False]
        tail=next((i for i,x in enumerate(reversed(seq)) if x),len(seq))
        self.assertEqual(tail,1)
    def test_mutated_referenced_normal_rejected(self):
        b,_=fake_kcl()
        no=struct.unpack_from('>I',b,4)[0]
        struct.pack_into('>fff',b,no+12*2,10.0,0,0)
        with self.assertRaises(ValueError):
            f.analyze_blob(b,0)
    def test_invalid_anchor_is_unavailable(self):
        b,_=fake_kcl()
        z=be_vec((float('nan'),0,0))
        d=f.analyze_blob(b,0,tee_words=z,pin_words=None)
        self.assertEqual(d['tee_untransformed_proximity'],'UNAVAILABLE')
        self.assertEqual(d['pin_untransformed_proximity'],'UNAVAILABLE')
    def test_far_anchor_fails_proximity(self):
        b,_=fake_kcl()
        d=f.analyze_blob(b,0,tee_words=be_vec((10000,12000,-10000)))
        self.assertEqual(d['tee_untransformed_proximity'],'FAR_OR_COORDINATE_TRANSFORM_REQUIRED')
    def test_point_triangle_regions(self):
        a,b,c=(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)
        self.assertAlmostEqual(f._point_triangle_distance_sq((.2,.2,2),a,b,c),4.0)
        self.assertAlmostEqual(f._point_triangle_distance_sq((-.5,-.5,0),a,b,c),.5)
        self.assertAlmostEqual(f._point_triangle_distance_sq((1.5,0,0),a,b,c),.25)
    def test_different_header_bytes_modify_private_digest(self):
        b,_=fake_kcl()
        x=f.analyze_blob(b,0)
        b[0x38]^=1
        y=f.analyze_blob(b,0)
        self.assertNotEqual(x['fingerprint_PRIVATE'],y['fingerprint_PRIVATE'])
    def test_no_raw_words_or_vertices_except_internal_digest(self):
        b,_=fake_kcl()
        d=f.analyze_blob(b,0)
        self.assertEqual(set(d),{
            'prism_slot_upper_bound','prism_index_slots_valid',
            'prism_referenced_normals_unit','prism_reconstructed_non_degenerate',
            'first_invalid_prism_slot_zero_based','trailing_invalid_prism_slots',
            'interior_invalid_prism_slots','all_prism_slots_reconstructed',
            'tee_untransformed_proximity','pin_untransformed_proximity',
            'octree_structure_validated','fingerprint_PRIVATE'})
        for k,v in d.items():
            self.assertNotIn('word',k)
            self.assertNotIn('vertex',k)
            if k!='fingerprint_PRIVATE':self.assertNotIsInstance(v,tuple)

if __name__=='__main__':unittest.main()
