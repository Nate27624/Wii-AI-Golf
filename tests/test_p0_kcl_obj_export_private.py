"""Synthetic-only tests for private KCL -> OBJ export, no original RAM."""
from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts"
for name in ("p0_kcl_private_probe",
             "p0_kcl_full_validation_private",
             "p0_kcl_obj_export_private"):
    spec = importlib.util.spec_from_file_location(name, SCRIPT / (name+".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
import p0_kcl_obj_export_private as obj

TRIANGLES = (
    ((0., 0., 0.), (1., 0., 0.), (0., 0., 1.)),
    ((1., 0., 0.), (1., 0., 1.), (0., 0., 1.)),
)


class TestPrivateObj(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / "Wii-AI-Golf-Data"
        self.derived = self.data / "derived"
        self.derived.mkdir(parents=True)
        self.output = self.derived / "hole01-collision-candidate-PRIVATE.obj"

    def test_vf_ascii_wireframe_contract(self):
        payload = obj._obj_bytes(TRIANGLES)
        self.assertTrue(payload.isascii())
        lines = payload.decode("ascii").splitlines()
        self.assertEqual(sum(x.startswith("v ") for x in lines), 6)
        self.assertEqual(sum(x.startswith("f ") for x in lines), 2)
        self.assertEqual(lines[-2:], ["f 1 2 3", "f 4 5 6"])
        self.assertTrue(all("/" not in x for x in lines))
        self.assertTrue(all(x.startswith(("#", "v ", "f ")) for x in lines))

    def test_original_face_attribute_groups_are_exactly_ordered(self):
        payload = obj._obj_bytes(TRIANGLES, attributes=(6, 3))
        lines = payload.decode("ascii").splitlines()
        self.assertEqual(
            [line for line in lines if line.startswith(("g ", "f "))],
            ["g KCL_OGWS_0006", "f 1 2 3",
             "g KCL_OGWS_0003", "f 4 5 6"])
        self.assertTrue(payload.isascii())
        self.assertNotIn("usemtl", payload.decode("ascii"))

    def test_surface_attribute_length_or_type_mismatch_rejected(self):
        for attrs in ((6,), (6, "3"), (6, -1), (6, 65536), (True, 3)):
            with self.subTest(attributes=attrs):
                with self.assertRaises(ValueError):
                    obj._obj_bytes(TRIANGLES, attributes=attrs)

    def test_surface_groups_are_explicit_not_default(self):
        legacy = obj._obj_bytes(TRIANGLES)
        self.assertNotIn(b"g KCL_OGWS_", legacy)
        source_labeled = obj._obj_bytes(TRIANGLES, attributes=(1, 7))
        self.assertIn(b"g KCL_OGWS_0007", source_labeled)
        self.assertNotEqual(legacy, source_labeled)

    def test_output_path_only_private_derived(self):
        found = obj._safe_output_path(self.output, self.data)
        self.assertEqual(found, self.output.resolve())
        with self.assertRaises(ValueError):
            obj._safe_output_path(self.data/"no.obj", self.data)
        with self.assertRaises(ValueError):
            obj._safe_output_path(self.derived/"public.obj", self.data)
        with self.assertRaises(ValueError):
            obj._safe_output_path(self.derived/"bad-PRIVATE.ply", self.data)
        with self.assertRaises(ValueError):
            obj._safe_output_path(self.derived/"nested"/"x-PRIVATE.obj", self.data)

    def test_local_appdata_destination_when_data_parent_is_git(self):
        # Private source remains in sibling Data, while generated OBJ is
        # outside a Git-controlled enclosing workspace.
        (self.data.parent / ".git").mkdir()
        with tempfile.TemporaryDirectory() as home:
            private = Path(home) / "WiiGolfAI" / "private" / "derived"
            private.mkdir(parents=True)
            target = private / "hole01-collision-candidate-PRIVATE.obj"
            with patch.dict(os.environ, {"LOCALAPPDATA": home}):
                approved = obj._safe_output_path(target, self.data)
            self.assertEqual(approved, target.resolve())
            self.assertFalse(approved.exists())

    def test_local_appdata_destination_still_rejects_git_ancestor(self):
        with tempfile.TemporaryDirectory() as home:
            private = Path(home) / "WiiGolfAI" / "private" / "derived"
            private.mkdir(parents=True)
            (Path(home) / ".git").mkdir()
            target = private / "hole01-collision-candidate-PRIVATE.obj"
            with patch.dict(os.environ, {"LOCALAPPDATA": home}):
                with self.assertRaises(ValueError):
                    obj._safe_output_path(target, self.data)

    def test_never_overwrite_existing_file(self):
        payload = obj._obj_bytes(TRIANGLES)
        obj._write_new_private_obj(self.output, payload)
        self.assertEqual(self.output.read_bytes(), payload)
        with self.assertRaises(FileExistsError):
            obj._write_new_private_obj(self.output, b"modified")
        self.assertEqual(self.output.read_bytes(), payload)
        with self.assertRaises(ValueError):
            obj._safe_output_path(self.output, self.data)

    def test_reject_symlink_output(self):
        other = self.derived / "other"
        other.write_text("existing", encoding="ascii")
        try:
            self.output.symlink_to(other)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not available to this test runner")
        with self.assertRaises(ValueError):
            obj._safe_output_path(self.output, self.data)
        self.assertEqual(other.read_text(encoding="ascii"), "existing")

    def test_git_checkout_output_forbidden(self):
        (self.data/".git").mkdir()
        with self.assertRaises(ValueError):
            obj._safe_output_path(self.output, self.data)

    def test_nonfinite_vertex_rejected(self):
        bad = (TRIANGLES[0], ((0, 0, 0), (1, float("nan"), 0), (0, 1, 0)))
        with self.assertRaises(ValueError):
            obj._obj_bytes(bad)
        with self.assertRaises(ValueError):
            obj._obj_bytes([((0,0,0), (0,1,0))])
        with self.assertRaises(ValueError):
            obj._obj_bytes([])

    def test_allow_project_obj_only_when_git_ignored(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            subprocess.run(["git", "init", "-q", str(project)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            data = project / "Wii-AI-Golf-Data"
            derived = data / "derived"
            derived.mkdir(parents=True)
            target = derived / "hole01-collision-candidate-PRIVATE.obj"
            with self.assertRaises(obj.ExportGate) as exc:
                obj._safe_output_path(target, data)
            self.assertEqual(exc.exception.stage, "OUTPUT_GIT_IGNORE_UNVERIFIED")
            (derived / ".gitignore").write_text("*.obj\n", encoding="ascii")
            self.assertEqual(obj._safe_output_path(target, data), target.resolve())

    def test_git_index_failure_has_safe_categorical_stage(self):
        # .git marker without a valid Git index must never count as proof
        # that a private OBJ is untracked or safe to place.
        (self.data / ".git").mkdir()
        (self.derived / ".gitignore").write_text("*.obj\n", encoding="ascii")
        with self.assertRaises(obj.ExportGate) as exc:
            obj._safe_output_path(self.output, self.data)
        self.assertEqual(exc.exception.stage, "OUTPUT_GIT_IGNORE_UNVERIFIED")

    def test_git_tracked_project_obj_not_approved(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            subprocess.run(["git", "init", "-q", str(project)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            data = project / "Wii-AI-Golf-Data"
            derived = data / "derived"
            derived.mkdir(parents=True)
            target = derived / "hole01-collision-candidate-PRIVATE.obj"
            target.write_text("existing", encoding="ascii")
            subprocess.run(["git", "-C", str(project), "add", "-f", "--", str(target)],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            (derived / ".gitignore").write_text("*.obj\n", encoding="ascii")
            with self.assertRaises(ValueError):
                obj._safe_output_path(target, data)

    def test_missing_private_derived_rejected(self):
        self.derived.rmdir()
        with self.assertRaises(ValueError):
            obj._safe_output_path(self.output, self.data)

    def _fake_fact(self, n, same=True):
        return {
            "hole": 1,
            "count": 2,
            "private_geometry_fingerprint": b"yes" if same else b"no",
            "triangles_PRIVATE": TRIANGLES if n == 5 else None,
            "attributes_PRIVATE": (6, 2) if n == 5 else None,
        }

    def test_export_fails_closed_when_control_differs(self):
        import audit_p0_seven_numbered_source_pairs_private as seven
        import audit_selected_ball_start_link_private as selected
        def facts(_, number, *unused, **kwargs):
            return self._fake_fact(number, same=(number != 7))
        with patch.object(selected, "DATA_ROOT", self.data), \
             patch.object(seven, "_check_archive", return_value={}), \
             patch.object(obj, "_source_qualified_mesh", side_effect=facts):
            with self.assertRaises(ValueError):
                obj.export(self.data, self.output)
        self.assertFalse(self.output.exists())

    def test_export_three_source_controls_before_write(self):
        import audit_p0_seven_numbered_source_pairs_private as seven
        import audit_selected_ball_start_link_private as selected
        visited = []
        def facts(_, number, *unused, **kwargs):
            visited.append(number)
            return self._fake_fact(number)
        with patch.object(selected, "DATA_ROOT", self.data), \
             patch.object(seven, "_check_archive", return_value={}), \
             patch.object(obj, "_source_qualified_mesh", side_effect=facts):
            report = obj.export(self.data, self.output)
        self.assertEqual(visited, [1, 7, 5])
        self.assertEqual(report["status"], "PRIVATE_OBJ_CREATED")
        self.assertEqual(report["triangle_faces"], 2)
        self.assertTrue(report["cross_capture_geometry_identical"])
        self.assertFalse(report["allowed_to_publish"])
        self.assertFalse(report["training_approved"])
        self.assertEqual(self.output.read_bytes(), obj._obj_bytes(TRIANGLES))

    def test_export_with_original_material_tags(self):
        import audit_p0_seven_numbered_source_pairs_private as seven
        import audit_selected_ball_start_link_private as selected
        def facts(_, number, *unused, **kwargs):
            return self._fake_fact(number)
        with patch.object(selected, "DATA_ROOT", self.data), \
             patch.object(seven, "_check_archive", return_value={}), \
             patch.object(obj, "_source_qualified_mesh", side_effect=facts):
            report = obj.export(self.data, self.output, surface_groups=True)
        self.assertTrue(report["original_prism_ogws_groups_included"])
        data = self.output.read_text(encoding="ascii")
        self.assertIn("g KCL_OGWS_0006\nf 1 2 3", data)
        self.assertIn("g KCL_OGWS_0002\nf 4 5 6", data)
        self.assertFalse(report["training_approved"])

    def test_bad_control_count_rejected(self):
        with self.assertRaises(ValueError):
            obj.export(self.data, self.output, controls=(1, 1))
        with self.assertRaises(ValueError):
            obj.export(self.data, self.output, capture=5, controls=(1, 5))

    def test_safe_cli_stage_and_capture_without_private_paths(self):
        stdout = io.StringIO()
        with patch.object(obj, "export",
                          side_effect=obj.ExportGate("FULL_PRISM_OR_TEE_PIN_GATE", 5)), \
             redirect_stdout(stdout):
            code = obj.main([
                "--archive", str(self.data / "PRIVATE bank path"),
                "--output", str(self.output)])
        report = json.loads(stdout.getvalue())
        self.assertEqual(code, 3)
        self.assertEqual(report["stage"], "FULL_PRISM_OR_TEE_PIN_GATE")
        self.assertEqual(report["capture_number"], 5)
        self.assertFalse(report["private_obj_created"])
        self.assertNotIn(str(self.data), stdout.getvalue())

    def test_output_path_rejection_is_categorized(self):
        import audit_selected_ball_start_link_private as selected
        stdout = io.StringIO()
        with patch.object(selected, "DATA_ROOT", self.data), redirect_stdout(stdout):
            code = obj.main([
                "--archive", str(self.data / "nonexistent"),
                "--output", str(self.data / "not-in-derived-PRIVATE.obj")])
        report = json.loads(stdout.getvalue())
        self.assertEqual(code, 3)
        self.assertEqual(report["stage"], "OUTPUT_PARENT_MISMATCH")
        self.assertIsNone(report["capture_number"])
        self.assertFalse(self.output.exists())

    def test_safe_cli_abstain_without_private_path(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = obj.main([
                "--archive", str(self.data / "unknown archive"),
                "--output", str(self.output)])
        report = json.loads(stdout.getvalue())
        self.assertEqual(code, 3)
        self.assertEqual(report["status"], "ABSTAIN_SOURCE_GEOMETRY_OR_OUTPUT_GATE")
        self.assertFalse(report["private_obj_created"])
        self.assertFalse(report["training_approved"])
        self.assertNotIn(str(self.data), stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
