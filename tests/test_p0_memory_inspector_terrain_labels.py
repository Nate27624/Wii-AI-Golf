"""No native memory needed: private UI face-label sidecar safety tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.inspector.terrain import TerrainMesh, TerrainError, load_private_obj
from wii_ai_golf.inspector.terrain_labels import (
    LABEL_KIND, apply_private_surface_labels,
)
from wii_ai_golf.inspector.gui import Inspector

OBJ = "v 0 0 0\nv 1 0 0\nv 0 0 1\nf 1 2 3\n"
SHA = hashlib.sha256(OBJ.encode("ascii")).hexdigest()


class LabelsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        # Most source-label tests concern SHA/face identity, not Git plumbing.
        # Use a standalone Projects folder so Windows Git index differences
        # cannot cause unrelated schema/UI tests to fail.
        self.folder = self.repo/"Projects"
        self.folder.mkdir(parents=True)
        self.obj = self.folder/"hole01-collision-candidate-PRIVATE.obj"
        # Write raw bytes, not write_text: Windows text mode converts LF to CRLF.
        # The test SHA must cover the exact bytes the loader actually reads.
        self.obj.write_bytes(OBJ.encode("ascii"))
        self.labels = self.folder/"hole01-collision-candidate-labels-PRIVATE.json"
        self.mesh = load_private_obj(self.obj)

    def data(self, *, sha=SHA, attr=6, faces=1):
        return dict(kind=LABEL_KIND, version=1, geometry_obj_sha256=sha,
                    source_hole_index=1, faces=faces, source_attributes=[attr],
                    training_approved=False, allowed_to_publish=False)

    def save(self, record):
        self.labels.write_text(json.dumps(record),encoding="ascii")

    def test_fixture_sha_matches_written_obj_on_every_os(self):
        self.assertEqual(self.obj.read_bytes(), OBJ.encode("ascii"))
        self.assertEqual(self.mesh.sha256, SHA)
        self.assertEqual(self.data()["geometry_obj_sha256"], self.mesh.sha256)

    def test_line_ending_change_requires_new_sha(self):
        # A different OBJ byte stream must fail source-label SHA binding.
        # This is a negative control; never normalize real OBJ content.
        self.obj.write_bytes(OBJ.replace("\n", "\r\n").encode("ascii"))
        different = load_private_obj(self.obj)
        self.assertNotEqual(different.sha256, SHA)
        self.save(self.data())
        with self.assertRaises(TerrainError):
            apply_private_surface_labels(different, self.labels)

    def test_apply_original_labels_without_touching_obj(self):
        before = self.obj.read_bytes()
        self.save(self.data())
        labeled = apply_private_surface_labels(self.mesh, self.labels)
        self.assertEqual(labeled.face_materials,(6,))
        self.assertEqual(labeled.sha256,self.mesh.sha256)
        self.assertEqual(self.obj.read_bytes(),before)
        self.assertEqual(self.mesh.face_materials,(None,))
        self.assertEqual(labeled.material_counts(),{6:1})

    def test_wrong_sha_abstains(self):
        self.save(self.data(sha="0"*64))
        with self.assertRaises(TerrainError):
            apply_private_surface_labels(self.mesh,self.labels)

    def test_wrong_count_abstains(self):
        self.save(self.data(faces=2))
        with self.assertRaises(TerrainError):
            apply_private_surface_labels(self.mesh,self.labels)

    def test_invalid_source_label_abstains(self):
        for bad in (-1,65536,True,"6",None):
            with self.subTest(bad=bad):
                self.save(self.data(attr=bad))
                with self.assertRaises(TerrainError):
                    apply_private_surface_labels(self.mesh,self.labels)

    def test_unapproved_provenance_abstains(self):
        d=self.data()
        d["training_approved"]=True
        self.save(d)
        with self.assertRaises(TerrainError):
            apply_private_surface_labels(self.mesh,self.labels)

    def test_unignored_or_tracked_json_rejected(self):
        # Exercise the actual Git-containing private Data/derived exception
        # separately from the standalone D:\\Projects happy path.
        git_root = self.repo / "isolated-git"
        git_root.mkdir()
        subprocess.run(["git", "init", "-q", str(git_root)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        private = git_root / "Wii-AI-Golf-Data" / "derived"
        private.mkdir(parents=True)
        target = private / self.labels.name
        target.write_text(json.dumps(self.data()), encoding="ascii")
        (private / ".gitignore").write_text("*.obj\n", encoding="ascii")
        with self.assertRaises(TerrainError):
            apply_private_surface_labels(self.mesh, target)
        (private / ".gitignore").write_text(
            "*.obj\n*-PRIVATE.json\n", encoding="ascii")
        subprocess.run(["git", "-C", str(git_root), "add", "-f", "--", str(target)],
                       check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        with self.assertRaises(TerrainError):
            apply_private_surface_labels(self.mesh, target)

    def test_standalone_projects_obj_and_labels_ui_only(self):
        with tempfile.TemporaryDirectory() as folder:
            standalone = Path(folder) / "Projects"
            standalone.mkdir()
            original = standalone / self.obj.name
            private_labels = standalone / self.labels.name
            original.write_bytes(self.obj.read_bytes())
            private_labels.write_text(json.dumps(self.data()),encoding="ascii")
            before = original.read_bytes()
            mesh = load_private_obj(original)
            colored = apply_private_surface_labels(mesh,private_labels)
            self.assertEqual(colored.face_materials,(6,))
            self.assertEqual(original.read_bytes(),before)
            self.assertEqual(mesh.sha256,colored.sha256)

    def test_standalone_projects_with_git_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            standalone = Path(folder) / "Projects"
            standalone.mkdir()
            (standalone / ".git").mkdir()
            private_labels = standalone / self.labels.name
            private_labels.write_text(json.dumps(self.data()), encoding="ascii")
            with self.assertRaises(TerrainError):
                apply_private_surface_labels(self.mesh,private_labels)

    def test_unapproved_arbitrary_folder_remains_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            standalone = Path(folder) / "RandomFolder"
            standalone.mkdir()
            private_labels = standalone / self.labels.name
            private_labels.write_text(json.dumps(self.data()),encoding="ascii")
            with self.assertRaises(TerrainError):
                apply_private_surface_labels(self.mesh,private_labels)

    def test_git_ignored_untracked_private_data_sidecar_accepted(self):
        with tempfile.TemporaryDirectory() as isolated:
            git_root = Path(isolated)
            subprocess.run(["git", "init", "-q", str(git_root)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            private = git_root / "Wii-AI-Golf-Data" / "derived"
            private.mkdir(parents=True)
            (private / ".gitignore").write_text(
                "*.obj\n*-PRIVATE.json\n", encoding="ascii")
            target = private / self.labels.name
            target.write_text(json.dumps(self.data()), encoding="ascii")
            self.assertEqual(
                apply_private_surface_labels(self.mesh, target).face_materials,
                (6,))

    def test_outside_private_data_folder_rejected(self):
        self.save(self.data())
        wrong=self.repo/"labels-PRIVATE.json"
        wrong.write_bytes(self.labels.read_bytes())
        with self.assertRaises(TerrainError):
            apply_private_surface_labels(self.mesh,wrong)

    def test_ui_applies_to_existing_mesh_without_replacing_obj(self):
        self.save(self.data())
        view = type("FakeUI",(),{})()
        view.terrain_mesh = self.mesh
        view.surface_label_status = Mock()
        view.draw_path = Mock()
        self.assertTrue(Inspector.load_terrain_labels_path(view,str(self.labels)))
        self.assertEqual(view.terrain_mesh.face_materials,(6,))
        view.draw_path.assert_called_once_with()
        self.assertEqual(self.obj.read_text(encoding="ascii"), OBJ)


if __name__ == "__main__":
    unittest.main()
