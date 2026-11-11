"""Synthetic local FC2 asset selection; NEVER contains game art or extracts ROM."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import importlib.util
import io
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.inspector.private_course_catalog import (
    inspect_private_course, private_course_report)


def _load_launcher():
    spec = importlib.util.spec_from_file_location(
        "private_course_test_launcher",
        ROOT / "scripts" / "p0_memory_inspector.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PrivateCourseCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "WiiGolfVisualPrivate"
        self.root.mkdir()
        self.export = (
            self.root / "visual_exports" / "glf_course_fc2" /
            "glf_course_fc2.dae")

    def test_probe_distinguishes_missing_brres_and_source_dae_without_reading(self):
        result = inspect_private_course(2, self.root)
        self.assertEqual(result.status, "COURSE_NOT_YET_EXTRACTED_OR_EXPORTED")
        self.assertIsNone(result.exported_dae)
        self.assertFalse(private_course_report(result)
                         ["original_training_hole_identity_verified"])
        brres = self.root / "unpacked" / "glf_course_fc2" / "G3D" / "glf_course_fc2.brres"
        brres.parent.mkdir(parents=True)
        brres.write_bytes(b"synthetic BRRES sentinel - not actual original asset")
        result = inspect_private_course(2, self.root)
        self.assertEqual(result.status, "SOURCE_BRRES_PRESENT_EXPORT_DAE_WITH_BRAWLCRATE")
        self.assertTrue(result.source_brres_present)
        self.export.parent.mkdir(parents=True)
        self.export.write_text("synthetic DAE sentinel - not actual game art")
        result = inspect_private_course(2, self.root)
        self.assertEqual(result.status, "LOCAL_SOURCE_DAE_CANDIDATE_FOUND")
        self.assertEqual(result.exported_dae, self.export)
        self.assertFalse(result.native_course_identity_verified)
        report = private_course_report(result)
        self.assertNotIn(str(self.root), json.dumps(report))
        self.assertFalse(report["collision_world_alignment_verified"])
        self.assertFalse(report["training_approved"])

    def test_no_fc1_fallback_when_fc2_missing(self):
        fc1 = (self.root / "visual_exports" / "glf_course_fc1" /
               "glf_course_fc1.dae")
        fc1.parent.mkdir(parents=True)
        fc1.write_text("synthetic prior FC1")
        launcher = _load_launcher()
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("wii_ai_golf.inspector.gui.launch") as gui_launch, \\
             redirect_stdout(stdout), redirect_stderr(stderr):
            rc = launcher.main([
                "--visual-course", "2",
                "--course-private-root", str(self.root),
            ])
        self.assertEqual(rc, 3)
        gui_launch.assert_not_called()
        self.assertIn("COURSE_NOT_YET_EXTRACTED_OR_EXPORTED",
                      stdout.getvalue())
        self.assertNotIn(str(fc1), stdout.getvalue())

    def test_explicit_fc2_launch_path_overrides_saved_fc1(self):
        self.export.parent.mkdir(parents=True)
        self.export.write_text("synthetic DAE sentinel")
        launcher = _load_launcher()
        with patch("wii_ai_golf.inspector.gui.launch", return_value=0) as launch:
            rc = launcher.main([
                "--visual-course", "2",
                "--course-private-root", str(self.root),
                "--terrain-obj", "private-collision.obj",
                "--terrain-labels", "private-sha-bound.json",
            ])
        self.assertEqual(rc, 0)
        launch.assert_called_once_with(
            "", "", "private-collision.obj",
            "private-sha-bound.json", str(self.export))

    def test_probe_course_does_not_launch_the_gui(self):
        launcher = _load_launcher()
        out = io.StringIO()
        with patch("wii_ai_golf.inspector.gui.launch") as launch, \\
             redirect_stdout(out):
            rc = launcher.main([
                "--probe-visual-course", "2",
                "--course-private-root", str(self.root),
            ])
        self.assertEqual(rc, 0)
        self.assertFalse(json.loads(out.getvalue())["dae_export_ready"])
        launch.assert_not_called()

    def test_invalid_course_numbers_and_ambiguous_flags_fail_closed(self):
        for value in (0, 10, True, "2", 2.0):
            with self.subTest(course=value), self.assertRaises(ValueError):
                inspect_private_course(value, self.root)
        launcher = _load_launcher()
        with self.assertRaises(SystemExit):
            launcher.main([
                "--visual-course", "2", "--visual-dae", "FC1.dae"])

    def test_gui_try_course2_leaves_prior_preview_if_missing(self):
        from wii_ai_golf.inspector.gui import Inspector
        instance = object.__new__(Inspector)
        instance.visual_status = Mock()
        instance.load_visual_path = Mock(return_value=True)
        missing = inspect_private_course(2, self.root)
        with patch("wii_ai_golf.inspector.gui.inspect_private_course",
                   return_value=missing):
            self.assertFalse(Inspector.try_visual_course_2(instance))
        instance.load_visual_path.assert_not_called()
        self.assertIn("NOT YET EXPORTED",
                      instance.visual_status.set.call_args.args[0])
        self.export.parent.mkdir(parents=True)
        self.export.write_text("synthetic")
        ready = inspect_private_course(2, self.root)
        with patch("wii_ai_golf.inspector.gui.inspect_private_course",
                   return_value=ready):
            self.assertTrue(Inspector.try_visual_course_2(instance))
        instance.load_visual_path.assert_called_once_with(str(self.export))


if __name__ == "__main__":
    unittest.main()
