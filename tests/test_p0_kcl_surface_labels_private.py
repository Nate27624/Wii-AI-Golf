"""Synthetic-only surface labels for *unchanged* private OBJ."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT/"scripts"
for name in ("p0_kcl_private_probe", "p0_kcl_full_validation_private",
             "p0_kcl_obj_export_private", "p0_kcl_surface_labels_private"):
    spec = importlib.util.spec_from_file_location(name,SCRIPTS/(name+".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
import p0_kcl_obj_export_private as geometry
import p0_kcl_surface_labels_private as labels

TRIANGLES = (
    ((0.,0.,0.),(1.,0.,0.),(0.,0.,1.)),
    ((1.,0.,0.),(1.,0.,1.),(0.,0.,1.)),
)


class SourceLabelsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo=Path(self.temp.name)
        subprocess.run(["git","init","-q",str(self.repo)],check=True,
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.root=self.repo/"Wii-AI-Golf-Data"
        self.derived=self.root/"derived"
        self.derived.mkdir(parents=True)
        (self.derived/".gitignore").write_text("*.obj\n*-PRIVATE.json\n",encoding="ascii")
        self.obj=self.derived/"hole01-collision-candidate-PRIVATE.obj"
        self.blob=geometry._obj_bytes(TRIANGLES)
        self.obj.write_bytes(self.blob)
        self.target=self.derived/"hole01-collision-candidate-labels-PRIVATE.json"

    def fact(self, n, *, changed=False):
        return {
            "hole":1, "count":2,
            "private_geometry_fingerprint": b"other" if changed else b"same",
            "triangles_PRIVATE": TRIANGLES if n==5 else None,
            "attributes_PRIVATE": [6,2] if n==5 else None,
        }

    def _run(self, changed=False):
        import audit_selected_ball_start_link_private as selected
        import audit_p0_seven_numbered_source_pairs_private as seven
        def fake(_, n, *args, **kwargs):
            return self.fact(n,changed=(changed and n==7))
        with patch.object(selected,"DATA_ROOT",self.root), \
             patch.object(seven,"_check_archive",return_value={}), \
             patch.object(geometry,"_source_qualified_mesh",side_effect=fake):
            return labels.make_labels(self.root,self.obj,self.target)

    def test_labels_per_face_original_sha_and_unchanged_obj(self):
        before=self.obj.read_bytes()
        report=self._run()
        self.assertEqual(report["status"],"PRIVATE_LABELS_CREATED")
        self.assertTrue(report["original_obj_unchanged"])
        self.assertEqual(self.obj.read_bytes(),before)
        d=json.loads(self.target.read_text(encoding="ascii"))
        self.assertEqual(d["source_attributes"],[6,2])
        self.assertEqual(d["geometry_obj_sha256"],hashlib.sha256(before).hexdigest())
        self.assertEqual(d["faces"],2)
        self.assertFalse(d["training_approved"])
        self.assertFalse(d["allowed_to_publish"])

    def test_standalone_projects_obj_and_labels_without_git(self):
        with tempfile.TemporaryDirectory() as folder:
            external = Path(folder) / "Projects"
            external.mkdir()
            original = external / self.obj.name
            output = external / self.target.name
            original.write_bytes(self.blob)
            before = original.read_bytes()
            import audit_selected_ball_start_link_private as selected
            import audit_p0_seven_numbered_source_pairs_private as seven
            def fake(_, number, *args, **kwargs):
                return self.fact(number)
            with patch.object(selected,"DATA_ROOT",self.root), \
                 patch.object(seven,"_check_archive",return_value={}), \
                 patch.object(geometry,"_source_qualified_mesh",side_effect=fake):
                result = labels.make_labels(self.root,original,output)
            self.assertEqual(result["status"], "PRIVATE_LABELS_CREATED")
            self.assertEqual(original.read_bytes(), before)
            saved=json.loads(output.read_text(encoding="ascii"))
            self.assertEqual(saved["geometry_obj_sha256"],
                             hashlib.sha256(before).hexdigest())
            self.assertEqual(saved["source_attributes"], [6,2])

    def test_standalone_projects_inside_git_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            external = Path(folder) / "Projects"
            external.mkdir()
            (external / ".git").mkdir()
            original = external / self.obj.name
            output = external / self.target.name
            original.write_bytes(self.blob)
            with self.assertRaises(labels.LabelsGate) as exc:
                self._run_standalone(original, output)
            self.assertEqual(exc.exception.stage, "PROJECTS_ROOT_INSIDE_GIT")
            self.assertFalse(output.exists())

    def _run_standalone(self, original, output):
        import audit_selected_ball_start_link_private as selected
        import audit_p0_seven_numbered_source_pairs_private as seven
        with patch.object(selected,"DATA_ROOT",self.root), \
             patch.object(seven,"_check_archive",return_value={}), \
             patch.object(geometry,"_source_qualified_mesh",
                          side_effect=lambda _, n, *a, **kw: self.fact(n)):
            return labels.make_labels(self.root,original,output)

    def test_standalone_projects_labels_in_other_folder_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            external = Path(folder) / "Projects"
            external.mkdir()
            original = external / self.obj.name
            original.write_bytes(self.blob)
            with self.assertRaises(labels.LabelsGate) as exc:
                self._run_standalone(original,self.target)
            self.assertEqual(exc.exception.stage, "LABELS_MUST_BE_NEXT_TO_OBJ")
            self.assertFalse(self.target.exists())

    def test_cross_capture_mismatch_rejects(self):
        with self.assertRaises(labels.LabelsGate):
            self._run(changed=True)
        self.assertFalse(self.target.exists())

    def test_obj_geometry_change_abstains_without_json(self):
        text=self.obj.read_text(encoding="ascii")
        self.obj.write_text(text.replace("v 1 0 0", "v 2 0 0"),encoding="ascii")
        with self.assertRaises(labels.LabelsGate) as exc:
            self._run()
        self.assertEqual(exc.exception.stage,"ORIGINAL_OBJ_FACE_ORDER_OR_COORDINATES")
        self.assertFalse(self.target.exists())

    def test_existing_label_json_never_overwritten(self):
        self.target.write_text("private",encoding="ascii")
        with self.assertRaises(labels.LabelsGate) as exc:
            self._run()
        self.assertEqual(exc.exception.stage,"LABEL_OUTPUT_ALREADY_EXISTS")
        self.assertEqual(self.target.read_text(encoding="ascii"),"private")

    def test_unignored_output_rejected_before_archive(self):
        (self.derived/".gitignore").write_text("*.obj\n",encoding="ascii")
        with self.assertRaises(labels.LabelsGate) as exc:
            self._run()
        self.assertEqual(exc.exception.stage,"GIT_IGNORE_REQUIRED")

    def test_tracked_label_path_rejected(self):
        self.target.write_text("private",encoding="ascii")
        subprocess.run(["git","-C",str(self.repo),"add","-f","--",str(self.target)],
                       check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        with self.assertRaises(labels.LabelsGate) as exc:
            self._run()
        self.assertEqual(exc.exception.stage,"GIT_INDEX_NOT_UNTRACKED")

    def test_failed_file_provenance_does_not_touch_original_obj(self):
        original=self.obj.read_bytes()
        with patch.object(labels,"_read_existing_obj",
                          side_effect=labels.LabelsGate("ORIGINAL_OBJ_CHANGED_DURING_READ")):
            with self.assertRaises(labels.LabelsGate):
                self._run()
        self.assertEqual(self.obj.read_bytes(),original)
        self.assertFalse(self.target.exists())


if __name__=="__main__":
    unittest.main()
