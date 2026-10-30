"""Synthetic private OBJ loader tests; no real game geometry."""
import tempfile
import unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from wii_ai_golf.inspector.terrain import TerrainError,load_private_obj
GOOD='# synthetic terrain\nv 0 1 0\nv 20 1 0\nv 0 1 20\nf 1 2 3\n'

class TerrainTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.path=Path(self.folder.name)/'private.obj';self.path.write_text(GOOD,encoding='ascii')
    def test_load(self):
        t=load_private_obj(self.path);self.assertEqual(len(t.faces),1);self.assertEqual(len(t.sha256),64)
        self.assertEqual(len(t.drawing_faces()),1)
    def test_focus(self):
        t=load_private_obj(self.path);self.assertEqual(len(t.drawing_faces(((2.,1.,2.),))),1)
        self.assertEqual(len(t.drawing_faces(((2000.,1.,2000.),))),0)
        self.assertEqual(len(t.drawing_faces(((2000.,1.,2000.),),focused=False)),1)
    def test_degenerate(self):
        self.path.write_text(GOOD.replace('v 0 1 20','v 20 1 0'))
        with self.assertRaises(TerrainError):load_private_obj(self.path)
    def test_nan(self):
        self.path.write_text(GOOD.replace('v 0 1 20','v NaN 1 20'))
        with self.assertRaises(TerrainError):load_private_obj(self.path)
    def test_index(self):
        self.path.write_text(GOOD.replace('f 1 2 3','f 1 2 44'))
        with self.assertRaises(TerrainError):load_private_obj(self.path)
    def test_face_quad(self):
        self.path.write_text(GOOD.replace('f 1 2 3','f 1 2 3 2'))
        with self.assertRaises(TerrainError):load_private_obj(self.path)
    def test_symlink(self):
        link=self.path.with_name('alias.obj');link.symlink_to(self.path)
        with self.assertRaises(TerrainError):load_private_obj(link)
    def test_git_inside_forbidden(self):
        (self.path.parent/'.git').mkdir()
        with self.assertRaises(TerrainError):load_private_obj(self.path)
    def test_only_plain_obj(self):
        self.path.write_text(GOOD+'mtllib bad.mtl\n')
        with self.assertRaises(TerrainError):load_private_obj(self.path)
    def test_decimation_limit(self):
        self.path.write_text(GOOD+('f 1 2 3\n'*150))
        t=load_private_obj(self.path)
        self.assertLessEqual(len(t.drawing_faces(limit=7)),7)
        with self.assertRaises(TerrainError):t.drawing_faces(limit=100000)
if __name__=='__main__':unittest.main()
