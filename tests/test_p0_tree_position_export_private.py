"""Synthetic-only private 94-tree JSON export and no-overwrite safety tests."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location(
    "p0_tree_export",SCRIPTS/"p0_tree_position_export_private.py")
t=importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)


def points():
    return tuple((float(n*10), float(n%5), float(n*17))
                 for n in range(94))


class PrivateTreeExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"Wii-AI-Golf-Data"
        self.root.mkdir()

    def test_exact_94_translation_contract(self):
        data=t.make_payload(points())
        self.assertEqual(data["kind"],"wii_sports_golf_private_tree_positions_v1")
        self.assertEqual(data["source_count"],94)
        self.assertEqual(data["source_element_stride_bytes"],84)
        self.assertEqual(data["source_translation_offset_bytes"],48)
        self.assertEqual(data["source_captures"],[1,5,7])
        self.assertEqual(len(data["tree_positions"]),94)

    def test_payload_keeps_uncertainties_false(self):
        data=t.make_payload(points())
        for key in ("world_visual_alignment_verified",
                    "original_tree_meshes_verified",
                    "collision_hitboxes_verified",
                    "training_approved"):
            self.assertIs(data[key],False)

    def test_exact_float_values_preserved(self):
        data=t.make_payload(points())
        self.assertEqual(data["tree_positions"][17],[170.,2.,289.])

    def test_missing_position_abstains(self):
        with self.assertRaises(ValueError):
            t.make_payload(points()[:93])

    def test_nonfinite_abstains(self):
        p=list(points())
        p[4]=(float("nan"),4.,4.)
        with self.assertRaises(ValueError):
            t.make_payload(tuple(p))

    def test_duplicate_position_abstains(self):
        p=list(points())
        p[-1]=p[0]
        with self.assertRaises(ValueError):
            t.make_payload(tuple(p))

    def test_wrong_source_captures_abstain(self):
        with self.assertRaises(ValueError):
            t.make_payload(points(),captures=(1,2,7))

    def test_exclusive_private_file_and_readback(self):
        data=t.make_payload(points())
        file=t.write_private_payload(self.root,data)
        self.assertEqual(file.parent.name,"derived")
        self.assertEqual(file.name,t.FILENAME)
        self.assertEqual(json.loads(file.read_text("utf-8")),data)
        self.assertLess(file.stat().st_size,64*1024)
        self.assertNotIn("0x9000",file.read_text("utf-8"))

    def test_cannot_overwrite_private_file(self):
        data=t.make_payload(points())
        f=t.write_private_payload(self.root,data)
        initial=f.read_bytes()
        with self.assertRaises(FileExistsError):
            t.write_private_payload(self.root,data)
        self.assertEqual(f.read_bytes(),initial)

    def test_reject_non_data_root(self):
        with self.assertRaises(ValueError):
            t.write_private_payload(Path(self.tmp.name),t.make_payload(points()))

    def test_refuse_symlink_destination(self):
        data=t.make_payload(points())
        parent=self.root/"derived"
        parent.mkdir()
        path=parent/t.FILENAME
        existing=self.root/"do-not-touch.txt"
        existing.write_text("untouched")
        try:
            path.symlink_to(existing)
        except (OSError,NotImplementedError):
            self.skipTest("Operating system does not permit ordinary test symlinks")
        with self.assertRaises((ValueError,FileExistsError)):
            t.write_private_payload(self.root,data)
        self.assertEqual(existing.read_text(),"untouched")

    def test_refuse_symlink_derived_directory(self):
        data=t.make_payload(points())
        outside=Path(self.tmp.name)/"outside"
        outside.mkdir()
        try:
            (self.root/"derived").symlink_to(outside,target_is_directory=True)
        except (OSError,NotImplementedError):
            self.skipTest("Operating system does not permit ordinary test symlinks")
        with self.assertRaises(ValueError):
            t.write_private_payload(self.root,data)
        self.assertEqual(list(outside.iterdir()),[])


if __name__=="__main__":
    unittest.main()
