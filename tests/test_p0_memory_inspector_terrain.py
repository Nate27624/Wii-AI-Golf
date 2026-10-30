"""Synthetic-only private terrain helper tests; never read real Wii RAM."""
import tempfile
import unittest
from pathlib import Path

from wii_ai_golf.inspector.terrain import TerrainError, load_private_obj

GOOD = "# private KCL collision hypothesis\nv 0 1 0\nv 20 1 0\nv 0 1 20\nf 1 2 3\n"


class TerrainTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.p = Path(self.folder.name) / "private.obj"
        self.p.write_text(GOOD, encoding="ascii")

    def test_loaded_triangles_and_hash(self):
        t = load_private_obj(self.p)
        self.assertEqual(len(t.faces), 1)
        self.assertEqual(len(t.sha256), 64)
        self.assertEqual(len(t.drawing_faces()), 1)

    def test_landmark_focus_rejects_far_mesh(self):
        t = load_private_obj(self.p)
        self.assertEqual(len(t.drawing_faces(((2000., 1., 2000.),))), 0)
        self.assertEqual(len(t.drawing_faces(((2., 1., 2.),))), 1)
        self.assertEqual(len(t.drawing_faces(((2000., 1., 2000.),), focused=False)), 1)

    def test_invalid_coordinate(self):
        self.p.write_text(GOOD.replace("v 20 1 0", "v nan 1 0"))
        with self.assertRaises(TerrainError):
            load_private_obj(self.p)

    def test_invalid_index(self):
        self.p.write_text(GOOD.replace("f 1 2 3", "f 1 2 999"))
        with self.assertRaises(TerrainError):
            load_private_obj(self.p)

    def test_quad_rejected(self):
        self.p.write_text(GOOD.replace("f 1 2 3", "f 1 2 3 2"))
        with self.assertRaises(TerrainError):
            load_private_obj(self.p)

    def test_obj_path_must_be_private(self):
        (Path(self.folder.name) / ".git").mkdir()
        with self.assertRaises(TerrainError):
            load_private_obj(self.p)

    def test_symlink_rejected(self):
        link = Path(self.folder.name) / "alias.obj"
        link.symlink_to(self.p)
        with self.assertRaises(TerrainError):
            load_private_obj(link)

    def test_face_decimation(self):
        self.p.write_text(GOOD + "f 1 2 3\n" * 159)
        t = load_private_obj(self.p)
        self.assertEqual(len(t.drawing_faces(limit=9)), 9)

    def test_extra_records_rejected(self):
        self.p.write_text(GOOD + "mtllib something.mtl\n")
        with self.assertRaises(TerrainError):
            load_private_obj(self.p)


if __name__ == "__main__":
    unittest.main()
