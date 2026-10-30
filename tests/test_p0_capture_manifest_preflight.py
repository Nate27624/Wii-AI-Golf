"""Synthetic tests for read-only/private bank-pair provenance. No actual Wii RAM."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import p0_capture_manifest_preflight as preflight


class CapturePreflightTests(unittest.TestCase):
    SIZES = (24, 64)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, size, marker):
        (self.root / name).write_bytes(bytes([marker]) * size)

    def pair(self, phase, *, reverse=False, marker=1):
        if reverse:
            self.put(f"{phase}.1.raw", 64, marker + 1)
            self.put(f"{phase}.2.raw", 24, marker)
        else:
            self.put(f"{phase}.1.raw", 24, marker)
            self.put(f"{phase}.2.raw", 64, marker + 1)

    def audit(self, mode="numbered"):
        return preflight.audit_capture_root(self.root, mode, sizes=self.SIZES)

    def test_numbered_bank_suffix_not_mistaken_for_bank_type(self):
        self.pair(1, reverse=True)
        report = self.audit()
        self.assertEqual(report["pairs"][0]["MEM1"]["file"], "1.2.raw")
        self.assertEqual(report["pairs"][0]["MEM2"]["file"], "1.1.raw")
        self.assertFalse(report["guest_frame_verified"])
        self.assertFalse(report["training_approved"])

    def test_checkpoint_names_and_bank_sizes(self):
        self.put("B0-MEM1.bin", 24, 1)
        self.put("B0-MEM2.bin", 64, 2)
        self.assertEqual(len(self.audit("checkpoint")["pairs"]), 1)
        self.put("B1-MEM1.bin", 64, 2)
        self.put("B1-MEM2.bin", 24, 1)
        with self.assertRaisesRegex(ValueError, "native-size"):
            self.audit("checkpoint")

    def test_incomplete_pair_rejected(self):
        self.put("1.1.raw", 24, 1)
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            self.audit()

    def test_wrong_native_sizes_rejected(self):
        self.put("1.1.raw", 20, 1)
        self.put("1.2.raw", 64, 2)
        with self.assertRaises(ValueError):
            self.audit()

    def test_unlinked_symlink_rejected(self):
        self.pair(1)
        target = self.root / "1.2.raw"
        link = self.root / "2.2.raw"
        try:
            link.symlink_to(target)
        except (NotImplementedError, OSError):
            self.skipTest("Symlink creation unavailable on this OS")
        self.put("2.1.raw", 24, 7)
        with self.assertRaises(ValueError):
            self.audit()

    def test_duplicate_hash_count_does_not_prove_same_shot(self):
        self.pair(1)
        self.pair(2)
        report = self.audit()
        self.assertEqual(report["duplicate_full_bank_sha_counts"], {"MEM1": 1, "MEM2": 1})
        self.assertFalse(report["same_shot_verified"])

    def test_summary_does_not_expose_name_sha_or_paths(self):
        self.pair(1)
        report = self.audit()
        text = json.dumps(preflight.sanitized_summary(report))
        self.assertNotIn("1.1.raw", text)
        self.assertNotIn(str(self.root), text)
        self.assertNotIn(report["pairs"][0]["MEM1"]["sha256"], text)
        self.assertNotIn("guest_frame_verified\": true", text.lower())
        self.assertIn("\"training_approved\": false", text.lower())

    def test_private_manifest_exclusive_and_outside_checkout_only(self):
        self.pair(1)
        report = self.audit()
        preflight.write_local_manifest(self.root, report)
        output = self.root / preflight.MANIFEST_NAME
        self.assertTrue(output.is_file())
        self.assertIn(report["pairs"][0]["MEM1"]["sha256"], output.read_text())
        with self.assertRaises(FileExistsError):
            preflight.write_local_manifest(self.root, report)
        output.unlink()
        (self.root / ".git").mkdir()
        with self.assertRaisesRegex(ValueError, "outside"):
            preflight.write_local_manifest(self.root, report)

    def test_mutation_during_read_is_rejected(self):
        self.pair(1)
        original = preflight.hashlib.sha256

        class MutatingDigest:
            def __init__(self):
                self._hash = original()
                self.once = False

            def update(self, chunk):
                self._hash.update(chunk)
                if not self.once:
                    self.once = True
                    # mtime should differ even on filesystems with coarse clock.
                    old = (self_path.stat().st_atime_ns, self_path.stat().st_mtime_ns)
                    import os
                    os.utime(self_path, ns=(old[0], old[1] + 10_000_000_000))

            def hexdigest(self):
                return self._hash.hexdigest()

        self_path = self.root / "1.1.raw"
        with patch.object(preflight.hashlib, "sha256", side_effect=MutatingDigest):
            with self.assertRaisesRegex(ValueError, "changed during"):
                self.audit()

    def test_invalid_mode_and_missing_folder_fail_closed(self):
        self.pair(1)
        with self.assertRaises(ValueError):
            self.audit("unknown")
        with self.assertRaises(ValueError):
            preflight.audit_capture_root(self.root / "absent", "numbered",
                                         sizes=self.SIZES)


if __name__ == "__main__":
    unittest.main()
