"""Synthetic sparse MEM1 snapshots; no game content or private paths in repo."""
from __future__ import annotations

import importlib.util
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "mem1_checkpoint_audit", ROOT / "scripts" / "audit_golf_mem1_checkpoints.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

SOURCE = {
    0x804BF8C4: 0x80010000,
    0x80010094: 4,
    0x804BF4D8: 0x80020000,
    0x80020018: 5,
    0x8002000C: 0x80030000,
    0x8003001C: 5,
    0x80030020: 0x80020000,
    0x80030054: 2,
    0x8003009C: 0x80040000,
}


def create_checkpoints(directory, *, extended=False):
    names = ["B0.raw", "B1.raw", "B2.raw", "B3.raw"]
    paths = [Path(directory) / s for s in names]
    size = 32 * 1024 * 1024 if extended else audit.MEM1_BYTES
    for stage, path in enumerate(paths):
        with path.open("wb") as f:
            f.truncate(size)  # sparse, does not write copyrighted RAM
            f.seek(0)
            f.write(b"RSPE01\x00\x01")  # synthetic boot header
            for addr, value in SOURCE.items():
                f.seek(addr - audit.MEM1_BASE)
                f.write(struct.pack(">I", value))
            # Reversible B2-only candidate at one coarse memory page.
            f.seek(0x60000)
            f.write(struct.pack(">I", [1, 1, 7, 1][stage]))
            # Permanently changed B2/B3, stable B0/B1 at separate page.
            f.seek(0x70000)
            f.write(struct.pack(">I", [2, 2, 9, 9][stage]))
            # Background drift across all stages, should be demoted.
            f.seek(0x80000)
            f.write(struct.pack(">I", 20 + stage))
    return paths


class Mem1CheckpointTests(unittest.TestCase):
    def test_source_gate_and_classification_and_privacy(self):
        with tempfile.TemporaryDirectory() as d:
            paths = create_checkpoints(d)
            report = audit.analyze_files(paths)
            self.assertEqual(report["game_id"], "RSPE01")
            self.assertTrue(report["scene_identity_stable_in_four_copies"])
            self.assertFalse(report["game_power_verified"])
            self.assertFalse(report["golf_main_type_verified"])
            self.assertEqual(report["changed_word_comparisons"]["b2_only_stable_idle_words"], 1)
            self.assertEqual(report["changed_word_comparisons"]["post_pointer_persistent_words"], 1)
            self.assertEqual(report["changed_pages"], 3)
            self.assertEqual(report["top_relative_pages"][0]["page_relative_index"], 0x60000 // 4096)
            self.assertNotIn(str(d), json.dumps(report))
            self.assertNotIn("0x80040000", json.dumps(report))
            self.assertNotIn("RAW-PRIVATE", json.dumps(report))

    def test_extended_32mib_export_ignored_after_first_24mib(self):
        with tempfile.TemporaryDirectory() as d:
            report = audit.analyze_files(create_checkpoints(d, extended=True))
            self.assertEqual(report["trailing_export_bytes_not_analyzed"], 8 * 1024 * 1024)
            self.assertEqual(report["mem1_compared_bytes"], audit.MEM1_BYTES)

    def test_invalid_revision_and_mode_fail_before_diff(self):
        with tempfile.TemporaryDirectory() as d:
            paths = create_checkpoints(d)
            with paths[0].open("r+b") as f:
                f.seek(7); f.write(b"\x00")
            with self.assertRaisesRegex(ValueError, "revision"):
                audit.analyze_files(paths)
        with tempfile.TemporaryDirectory() as d:
            paths = create_checkpoints(d)
            with paths[2].open("r+b") as f:
                f.seek(0x10094); f.write(struct.pack(">I", 0))
            with self.assertRaisesRegex(ValueError, "mode"):
                audit.analyze_files(paths)

    def test_scene_relocation_and_sport_fail(self):
        with tempfile.TemporaryDirectory() as d:
            paths = create_checkpoints(d)
            with paths[3].open("r+b") as f:
                f.seek(0x4BF4D8); f.write(struct.pack(">I", 0x80021000))
            with self.assertRaises(ValueError):
                audit.analyze_files(paths)
        with tempfile.TemporaryDirectory() as d:
            paths = create_checkpoints(d)
            with paths[1].open("r+b") as f:
                f.seek(0x30054); f.write(struct.pack(">I", 3))
            with self.assertRaisesRegex(ValueError, "sport"):
                audit.analyze_files(paths)

    def test_distinct_paths_and_dump_size_and_symlink_gates(self):
        with tempfile.TemporaryDirectory() as d:
            paths = create_checkpoints(d)
            with self.assertRaisesRegex(ValueError, "distinct"):
                audit.analyze_files([paths[0], paths[1], paths[2], paths[2]])
            paths[2].write_bytes(b"small")
            with self.assertRaisesRegex(ValueError, "not 24 MiB"):
                audit.analyze_files(paths)

    def test_cli_invalid_file_path_does_not_echo_user_path(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "private_secret_ram_pointer_0x81234567.raw"
            output = io.StringIO()
            with redirect_stderr(output):
                status = audit.main(["--b0", str(p), "--b1", str(p),
                                     "--b2", str(p), "--b3", str(p)])
            self.assertEqual(status, 1)
            self.assertNotIn(str(d), output.getvalue())
            self.assertNotIn("0x81234567", output.getvalue())

    def test_disallowed_public_page_limit(self):
        with tempfile.TemporaryDirectory() as d:
            paths = create_checkpoints(d)
            with self.assertRaisesRegex(ValueError, "cap"):
                audit.analyze_files(paths, max_pages=25)


if __name__ == "__main__":
    unittest.main()
