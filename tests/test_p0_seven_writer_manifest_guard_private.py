"""Fabricated-only provenance regression tests; no ROM, native RAM, or Dolphin."""
from __future__ import annotations

import contextlib
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import audit_p0_seven_writer_manifest_guard_private as audit


def fabricated_archive(tmp):
    root = Path(tmp) / "Data"
    folder = root / "captures" / "p0-new-cohort-test-PRIVATE"
    folder.mkdir(parents=True)
    captures = []
    for n in audit.PHASES:
        banks = []
        for i, size in enumerate((3, 4)):
            name = f"{n}.{i + 1}.raw"
            payload = bytes([n, i + 1]) + b"x" * (size - 2)
            (folder / name).write_bytes(payload)
            banks.append({
                "file": name,
                "bank": ("MEM1", "MEM2")[i],
                "bytes": size,
                "copy_verified": True,
                "sha256": hashlib.sha256(payload).hexdigest(),
            })
        captures.append({"capture_number": n, "banks": banks})
    manifest = {
        "kind": audit.ARCHIVE_KIND,
        "training_approved": False,
        "human_phase_file_mapping_verified": False,
        "capture_count": 7,
        "capture_numbers": list(audit.PHASES),
        "captures": captures,
    }
    path = folder / "manifest-PRIVATE.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return root, folder, path


class ManifestGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root, self.folder, self.manifest = fabricated_archive(self.temp.name)
        self.patches = [
            patch.object(audit.source.selected, "DATA_ROOT", self.root),
            patch.object(audit, "SIZES", (3, 4)),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.temp.cleanup()

    def _update_manifest(self, transform):
        m = json.loads(self.manifest.read_text())
        transform(m)
        self.manifest.write_text(json.dumps(m), encoding="utf-8")

    def test_exact_14_original_bank_digests_pass(self):
        path, digest = audit.verify_original_archive(self.folder)
        self.assertEqual(path, self.folder)
        self.assertEqual(len(digest), 64)

    def test_preexisting_modified_bank_is_refused_even_when_stable(self):
        # This is precisely what the plain #236 pre/post-consistency check misses.
        p = self.folder / "5.1.raw"
        p.write_bytes(b"zzz")  # Correct length, wrong archived digest.
        with self.assertRaisesRegex(ValueError, "differs from original"):
            audit.verify_original_archive(self.folder)

    def test_changed_digest_in_manifest_cannot_pass(self):
        self._update_manifest(lambda m: m["captures"][1]["banks"][1].update(
            sha256="0" * 64))
        with self.assertRaises(ValueError):
            audit.verify_original_archive(self.folder)

    def test_duplicate_number_refused(self):
        self._update_manifest(lambda m: m["captures"][2].update(
            capture_number=2))
        with self.assertRaises(ValueError):
            audit.verify_original_archive(self.folder)

    def test_wrong_bank_order_refused(self):
        self._update_manifest(lambda m: m["captures"][0]["banks"][0].update(
            bank="MEM2"))
        with self.assertRaises(ValueError):
            audit.verify_original_archive(self.folder)

    def test_false_provenance_claim_refused(self):
        self._update_manifest(lambda m: m.update(training_approved=True))
        with self.assertRaises(ValueError):
            audit.verify_original_archive(self.folder)

    def test_manifest_symlink_refused(self):
        original = self.folder / "manifest-copy.json"
        original.write_bytes(self.manifest.read_bytes())
        self.manifest.unlink()
        try:
            self.manifest.symlink_to(original)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable to runner")
        with self.assertRaises(ValueError):
            audit.verify_original_archive(self.folder)

    def test_changed_during_writer_read_refused_on_second_gate(self):
        def mutate(_):
            (self.folder / "6.2.raw").write_bytes(b"ffff")
            return self._safe_result()
        with patch.object(audit.writer, "run_local", side_effect=mutate):
            with self.assertRaises(ValueError):
                audit.run_local(self.folder)

    @staticmethod
    def _safe_result():
        return {
            "sample_count_source_gated": 7,
            "approved_for_training": False,
            "allowed_to_publish": False,
            "per_snapshot_equal_components": [],
        }

    def test_good_writer_is_verified_and_flags_remain_false(self):
        with patch.object(audit.writer, "run_local",
                          return_value=self._safe_result()) as reader:
            report = audit.run_local(self.folder)
        reader.assert_called_once_with(self.folder)
        self.assertTrue(report[
            "original_seven_archive_14_bank_manifest_sha_matched_before_after"])
        self.assertFalse(report["human_phase_mapping_independently_verified"])
        self.assertFalse(report["approved_for_training"])

    def test_unsafe_writer_claim_refused(self):
        bad = self._safe_result()
        bad["approved_for_training"] = True
        with patch.object(audit.writer, "run_local", return_value=bad):
            with self.assertRaises(ValueError):
                audit.run_local(self.folder)

    def test_source_failure_not_misreported_as_pass(self):
        with patch.object(audit.writer, "run_local",
                          side_effect=ValueError("source owner mismatch")):
            with self.assertRaises(ValueError):
                audit.run_local(self.folder)

    def test_cli_abstains_without_publishing_sensitive_paths(self):
        code = audit.main(["--archive", str(self.root / "wrong-private")])
        self.assertEqual(code, 2)

    def test_isolated_import_help(self):
        cmd = [sys.executable, "-I",
               str(SCRIPTS / "audit_p0_seven_writer_manifest_guard_private.py"),
               "--help"]
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.run(cmd, cwd=td, text=True, capture_output=True,
                               timeout=20, check=False)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("--archive", p.stdout)


if __name__ == "__main__":
    unittest.main()
