"""S002 private phase-stage lifecycle tests; mock bytes only, no emulator."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.audit.private_capture_staging import staged_native_bank_phase


class PrivateStageTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name) / "Wii-AI-Golf-Data" / "captures"
        self.root.mkdir(parents=True)
        self.session = self.root / "SHOT-local-test-PRIVATE"
        self.session.mkdir()

    def stages(self):
        return list(self.session.iterdir())

    def test_success_cleans_only_new_files_after_keeper_block(self):
        with staged_native_bank_phase(self.session, "PRE") as (m1, m2):
            self.assertEqual(m1.name, "mem1.raw")
            self.assertEqual(m2.name, "mem2.raw")
            self.assertTrue(m1.parent.name.startswith("STAGING-PRE-"))
            m1.write_bytes(b"test1")
            m2.write_bytes(b"test2")
            self.assertTrue(m1.is_file())
        self.assertEqual(self.stages(), [])

    def test_truncated_read_preserves_incomplete_private_artifact(self):
        with self.assertRaisesRegex(RuntimeError, "truncated"):
            with staged_native_bank_phase(self.session, "PRE") as (m1, m2):
                m1.write_bytes(b"partial")
                raise RuntimeError("truncated read")
        failed = self.stages()
        self.assertEqual(len(failed), 1)
        self.assertTrue(failed[0].name.startswith("FAILED-PRE-"))
        self.assertEqual((failed[0] / "mem1.raw").read_bytes(), b"partial")

    def test_retry_uses_fresh_stage_and_preserves_previous_failure(self):
        with self.assertRaises(ValueError):
            with staged_native_bank_phase(self.session, "POST") as (m1, _):
                m1.write_bytes(b"old-private")
                raise ValueError("failed")
        before = self.stages()[0]
        with staged_native_bank_phase(self.session, "POST") as (m1, m2):
            self.assertNotEqual(before, m1.parent)
            m1.write_bytes(b"new1")
            m2.write_bytes(b"new2")
        self.assertEqual(self.stages(), [before])
        self.assertEqual((before / "mem1.raw").read_bytes(), b"old-private")

    def test_interrupted_attempt_keeps_evidence(self):
        with self.assertRaises(KeyboardInterrupt):
            with staged_native_bank_phase(self.session, "PRE") as (m1, _):
                m1.write_bytes(b"interrupted")
                raise KeyboardInterrupt()
        self.assertEqual(len(self.stages()), 1)
        self.assertTrue(self.stages()[0].name.startswith("FAILED-PRE-"))

    def test_older_staging_not_overwritten_or_removed(self):
        previous = self.session / "STAGING-PRE-oldattempt"
        previous.mkdir()
        (previous / "mem1.raw").write_bytes(b"keep")
        with staged_native_bank_phase(self.session, "PRE") as (m1, m2):
            m1.write_bytes(b"new")
            m2.write_bytes(b"new")
        self.assertEqual((previous / "mem1.raw").read_bytes(), b"keep")

    def test_extra_file_causes_no_success_cleanup_and_quarantine(self):
        with self.assertRaisesRegex(RuntimeError, "contents changed"):
            with staged_native_bank_phase(self.session, "RESULT") as (m1, m2):
                m1.write_bytes(b"a")
                m2.write_bytes(b"b")
                (m1.parent / "unexpected").write_bytes(b"private")
        failed = self.stages()
        self.assertEqual(len(failed), 1)
        self.assertTrue(failed[0].name.startswith("FAILED-RESULT-"))
        self.assertEqual((failed[0] / "unexpected").read_bytes(), b"private")

    def test_missing_bank_cannot_be_mistaken_for_success(self):
        with self.assertRaisesRegex(RuntimeError, "contents changed"):
            with staged_native_bank_phase(self.session, "PRE") as (m1, _):
                m1.write_bytes(b"only-one")
        self.assertEqual(len(self.stages()), 1)
        self.assertTrue(self.stages()[0].name.startswith("FAILED-PRE-"))

    def test_wrong_session_or_phase_rejected(self):
        with self.assertRaises(ValueError):
            with staged_native_bank_phase(self.session, "FLIGHT"):
                pass
        outside = self.root.parent / "SHOT-not-under-captures-PRIVATE"
        outside.mkdir()
        with self.assertRaises(ValueError):
            with staged_native_bank_phase(outside, "PRE"):
                pass
        self.assertEqual(self.stages(), [])

    def test_symlinked_private_root_refused(self):
        with tempfile.TemporaryDirectory() as extra:
            link = self.root / "SHOT-link-PRIVATE"
            try:
                os.symlink(self.session, link, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink privilege unavailable")
            with self.assertRaises(ValueError):
                with staged_native_bank_phase(link, "PRE"):
                    pass

    def test_token_collision_does_not_open_old_files(self):
        prior = self.session / ("STAGING-PRE-" + "00" * 12)
        prior.mkdir()
        (prior / "mem1.raw").write_bytes(b"dont-overwrite")
        with patch("wii_ai_golf.audit.private_capture_staging.secrets.token_hex", return_value="00" * 12):
            with self.assertRaises(FileExistsError):
                with staged_native_bank_phase(self.session, "PRE"):
                    pass
        self.assertEqual((prior / "mem1.raw").read_bytes(), b"dont-overwrite")


if __name__ == "__main__":
    unittest.main()
