"""Synthetic-only original KCL archive match; no Wii source assets."""
from __future__ import annotations

from pathlib import Path
import importlib.util
import math
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "src"))

import p0_kcl_private_probe as kcl
import p0_match_course_kcl_archive_private as match
from wii_ai_golf.inspector.terrain import load_private_obj


def fake_kcl():
    """Strict synthetic KCL based on original parser tests."""
    b = bytearray(1024)
    po = 0x3c
    no = po + 3*12
    pro = no + 4*12 - 0x10
    octo = pro + 0x10 + 3*0x10
    struct.pack_into(">IIII", b, 0, po, no, pro, octo)
    struct.pack_into(">f", b, 0x10, 3.)
    struct.pack_into(">fff", b, 0x14, -100., -2., -100.)
    struct.pack_into(">III", b, 0x2c, 4, 5, 6)
    for i, point in enumerate(((0.,0.,0.), (1.,0.,1.), (2.,0.,2.))):
        struct.pack_into(">fff", b, po+i*12, *point)
    normals = ((0.,1.,0.), (1.,0.,0.), (0.,0.,1.),
               (math.sqrt(.5),0.,math.sqrt(.5)))
    for i, vec in enumerate(normals):
        struct.pack_into(">fff", b, no+i*12, *vec)
    for i in range(3):
        struct.pack_into(">fHHHHHH", b, pro+0x10+i*0x10,
                         7.0710678, i, 0, 1, 2, 3, 2)
    return bytes(b)


def original_obj_text(data):
    po,no,pro,_=struct.unpack_from(">IIII",data,0)
    pos = [kcl._v3(data,po+12*i) for i in range((no-po)//12)]
    normals = [kcl._v3(data,no+12*i)
               for i in range((pro+0x10-no)//12)]
    triangles = [kcl._triangle(data,0,pos,normals,pro,i)[:3]
                 for i in range(3)]
    rows = ["# synthetic test only"]
    for t in triangles:
        for p in t:
            rows.append("v "+" ".join(format(float(x),".9g") for x in p))
    for i in range(len(triangles)):
        j=3*i+1
        rows.append(f"f {j} {j+1} {j+2}")
    return "\n".join(rows)+"\n"


class OriginalArchiveKCLMatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.unpacked = self.root / "unpacked"
        self.unpacked.mkdir()
        self.obj = self.root / "hole01-collision-candidate-PRIVATE.obj"
        self.kcl = fake_kcl()
        self.obj.write_text(original_obj_text(self.kcl), encoding="ascii")
        self.target = (
            self.unpacked / "glf_course_fc3" / "Collision" / "course.kcl")
        self.target.parent.mkdir(parents=True)

    def test_identifies_exact_source_geometry_without_original_file_name_guess(self):
        self.target.write_bytes(self.kcl)
        self.assertEqual(kcl.parse_kcl_candidate(self.kcl,0)
                         ["prism_count_upper_bound"],3)
        result = match.inspect_extracts(self.obj,self.unpacked)
        self.assertEqual(result["status"],
                         "ONE_EXACT_ORIGINAL_ARCHIVE_KCL_MATCH")
        self.assertEqual(result["exact_matched_archive_candidates"],
                         ["glf_course_fc3"])
        self.assertEqual(result["original_disc_kcl_files_checked"],1)
        self.assertFalse(result["training_approved"])
        self.assertFalse(result["native_visual_to_collision_transform_verified"])
        self.assertNotIn(str(self.root),str(result))
        self.assertNotIn("0.70710678",str(result))

    def test_nonmatching_archive_does_not_get_credited(self):
        wrong=bytearray(self.kcl)
        po,no,pro,_=struct.unpack_from(">IIII",wrong,0)
        struct.pack_into(">f",wrong,pro+0x10,8.)
        self.target.write_bytes(wrong)
        result=match.inspect_extracts(self.obj,self.unpacked)
        self.assertEqual(result["status"],"NO_EXACT_SOURCE_KCL_MATCH_FOUND")
        self.assertEqual(result["candidates"][0]["status"],
                         "SOURCE_PRISM_GEOMETRY_DIFFERS")
        self.assertEqual(result["exact_matched_archive_candidates"],[])

    def test_no_kcl_is_not_evidence_of_mismatched_course(self):
        result=match.inspect_extracts(self.obj,self.unpacked)
        self.assertEqual(result["status"],"NO_EXACT_SOURCE_KCL_MATCH_FOUND")
        self.assertEqual(result["original_disc_kcl_files_checked"],0)

    def test_two_identical_archives_are_ambiguous(self):
        self.target.write_bytes(self.kcl)
        another=(self.unpacked/"glf_course_fc5"/"x.kcl")
        another.parent.mkdir(parents=True)
        another.write_bytes(self.kcl)
        result=match.inspect_extracts(self.obj,self.unpacked)
        self.assertEqual(result["status"],
                         "AMBIGUOUS_MULTIPLE_ORIGINAL_ARCHIVE_KCL_MATCHES")
        self.assertEqual(result["exact_matched_archive_candidates"],
                         ["glf_course_fc3","glf_course_fc5"])

    def test_course_prism_count_mismatch_is_categorical(self):
        wrong=bytearray(self.kcl)
        po,no,pro,_=struct.unpack_from(">IIII",wrong,0)
        struct.pack_into(">I",wrong,0x0c,pro+0x10+2*0x10)
        self.target.write_bytes(wrong)
        result=match.inspect_extracts(self.obj,self.unpacked)
        self.assertEqual(result["candidates"][0]["status"],
                         "ORIGINAL_PRISM_COUNT_DIFFERS")
        self.assertEqual(result["candidates"][0]["original_prism_count"],2)

    def test_outside_private_unpacked_rejected(self):
        self.target.write_bytes(self.kcl)
        with self.assertRaises(ValueError):
            match.inspect_extracts(self.obj,self.root)


if __name__ == "__main__":
    unittest.main()
