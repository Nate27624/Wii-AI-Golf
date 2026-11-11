"""Synthetic-only Wii Sports KCL file-layout falsification; never touches Dolphin."""
import importlib.util
import math
from pathlib import Path
import struct
import unittest

PATH=Path(__file__).resolve().parents[1]/'scripts'/'p0_kcl_private_probe.py'
spec=importlib.util.spec_from_file_location('p0_kcl_private_probe',PATH)
p=importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def fake_kcl():
    b=bytearray(1024)
    po=0x3c; no=po+3*12; pro=no+4*12-0x10
    octo=pro+0x10+3*0x10
    struct.pack_into('>IIII',b,0,po,no,pro,octo)
    struct.pack_into('>f',b,0x10,3.0)
    struct.pack_into('>fff',b,0x14,-100.,-2.,-100.)
    struct.pack_into('>III',b,0x2c,4,5,6)
    for i,xyz in enumerate(((0,0,0),(1,0,1),(2,0,2))):
        struct.pack_into('>fff',b,po+i*12,*xyz)
    normals=((0,1,0),(1,0,0),(0,0,1),(math.sqrt(0.5),0,math.sqrt(0.5)))
    for i,xyz in enumerate(normals):
        struct.pack_into('>fff',b,no+i*12,*xyz)
    for i in range(3):
        struct.pack_into('>fHHHHHH',b,pro+0x10+i*0x10,7.0710678,i,0,1,2,3,2)
    return b


class TestKCL(unittest.TestCase):
    def test_detects_synthetic_prisms(self):
        data=p.parse_kcl_candidate(fake_kcl(),0)
        self.assertEqual(data['prism_count_upper_bound'],3)
        self.assertEqual(data['validated_prism_samples'],3)

    def test_scan_aligned_offset(self):
        b=bytearray(5000)
        b[0x400:0x800]=fake_kcl()
        hits,n=p.scan_bank(b)
        self.assertEqual(n,1)
        self.assertEqual(hits[0][0],0x400)

    def test_rejects_nonfinite_normals(self):
        b=fake_kcl()
        struct.pack_into('>f',b,0x60,float('nan'))
        self.assertIsNone(p.parse_kcl_candidate(b,0))

    def test_rejects_impossible_prism_indices(self):
        b=fake_kcl()
        b[0x90+6:0x90+8]=b'\xff\xff'
        self.assertIsNone(p.parse_kcl_candidate(b,0))

    def test_rejects_unordered_header(self):
        b=fake_kcl()
        struct.pack_into('>I',b,0x04,0)
        self.assertIsNone(p.parse_kcl_candidate(b,0))

    def test_rejects_unaligned_header(self):
        b=bytearray(b'\0')+fake_kcl()
        self.assertIsNone(p.parse_kcl_candidate(b,1))
        self.assertEqual(p.scan_bank(b)[1],0)

    def test_no_random_ram_false_positive(self):
        self.assertEqual(p.scan_bank(bytearray(2*1024*1024))[1],0)


if __name__=='__main__':
    unittest.main()
