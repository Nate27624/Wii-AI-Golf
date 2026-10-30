"""Synthetic-only KCL material and OG Golf PMP tree metadata verification."""
import importlib.util
import math
from pathlib import Path
import struct
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p0_kcl_surface_tree_inventory_private.py"


def load():
    import sys
    sys.path.insert(0,str(SCRIPT.parent))
    spec=importlib.util.spec_from_file_location("p0_kcl_surface",SCRIPT)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


s=load()


def kcl(attrs=(1,2,6)):
    po,no,prism=0x3c,0x60,0x90
    octo=prism+16*len(attrs)
    blob=bytearray(max(512,octo+4))
    struct.pack_into(">4I",blob,0,po,no,prism-16,octo)
    struct.pack_into(">f",blob,0x10,30.)
    struct.pack_into(">3I",blob,0x2c,0,0,0)
    for i,p in enumerate(((0.,0.,0.),(10.,0.,0.),(0.,0.,10.))):
        struct.pack_into(">3f",blob,po+i*12,*p)
    for i,n in enumerate(((0.,1.,0.),(0.,0.,1.),(1.,0.,0.),
                          (math.sqrt(.5),0.,math.sqrt(.5)))):
        struct.pack_into(">3f",blob,no+i*12,*n)
    for i,attr in enumerate(attrs):
        struct.pack_into(">f6H",blob,prism+i*16,1.,0,0,1,2,3,attr)
    return blob


def records(ids):
    out=bytearray(0x58*len(ids))
    for i,identifier in enumerate(ids):
        off=i*0x58
        struct.pack_into(">I",out,off,identifier)
        struct.pack_into(">3f",out,off+0x08,float(i),10.,20.)
        struct.pack_into(">3f",out,off+0x14,1.,1.,1.)
    return out


class TerrainTypes(unittest.TestCase):
    def test_original_game_surface_values_are_not_resort(self):
        self.assertEqual(s.FLAGS[0x0001],"fairway")
        self.assertEqual(s.FLAGS[0x0002],"rough")
        self.assertEqual(s.FLAGS[0x0003],"bunker")
        self.assertEqual(s.FLAGS[0x0006],"green")
        self.assertEqual(s.FLAGS[0x0007],"water")
        self.assertEqual(s.FLAGS[0x0009],"fringe")
        self.assertNotIn(0x0106,s.FLAGS)

    def test_valid_mixed_kcl_attributes(self):
        result=s.read_prism_histogram(kcl((1,2,6,3)))
        self.assertEqual(dict(result),{1:1,2:1,6:1,3:1})

    def test_duplicate_attributes_retained_as_counts(self):
        self.assertEqual(s.read_prism_histogram(kcl((1,1,1,6)))[1],3)

    def test_unknown_attribute_not_pretended_as_green(self):
        result=s.read_prism_histogram(kcl((0xCAFE,6,6)))
        self.assertEqual(result[0xCAFE],1)
        self.assertNotIn(0xCAFE,s.FLAGS)

    def test_bad_indices_abstain(self):
        data=kcl()
        struct.pack_into(">H",data,0x90+4,999)
        self.assertIsNone(s.read_prism_histogram(data))

    def test_nonunit_normal_abstain(self):
        data=kcl()
        struct.pack_into(">f",data,0x60+4,20.)
        self.assertIsNone(s.read_prism_histogram(data))

    def test_truncated_prism_abstains(self):
        data=kcl()
        struct.pack_into(">I",data,0x0c,0x10000)
        self.assertIsNone(s.read_prism_histogram(data))

    def test_find_candidate_in_bank(self):
        blob=bytearray(1024)
        mesh=kcl()
        blob[256:256+len(mesh)]=mesh
        self.assertEqual(len(s.scan(blob)),1)

    def test_two_tree_variants_and_water_reflections(self):
        d=records((0x00010002,0x00010003,0x00010004,0x00010005))
        result=s.classify_tree_records(d)
        self.assertEqual(sum(result.values()),4)
        self.assertEqual(result["tree_variant_1"],1)
        self.assertEqual(result["tree_variant_2_water_reflection"],1)

    def test_non_tree_excluded(self):
        d=records((0x00010000,0x00010001,0x0001000A))
        self.assertEqual(dict(s.classify_tree_records(d)),{})

    def test_tree_nonfinite_location_refused(self):
        d=records((0x00010002,))
        struct.pack_into(">f",d,0x08,float("nan"))
        self.assertIsNone(s.classify_tree_records(d))

    def test_tree_partial_object_refused(self):
        self.assertIsNone(s.classify_tree_records(b"x"*0x57))


if __name__ == "__main__":
    unittest.main()
