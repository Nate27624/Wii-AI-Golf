"""Synthetic-only offline B0/B1/B2/B3 MEM1 comparator regression tests."""
from __future__ import annotations
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_mem1_checkpoints_private as subject

PAGE = subject.PAGE

def _four_pages(tmp, *, n_pages=2, extra=None):
    dumps = [bytearray(PAGE * n_pages) for _ in range(4)]
    # B0 -> B1 idle drift (never flag as input-only).
    _set(dumps, 0, 4, [0, 1, 2, 3])
    # B0 == B1, B2 differs, B3 reverts (pointer-phase candidate).
    _set(dumps, 0, 8, [0, 0, 100, 0])
    # B0 == B1, B2 changes and B3 persists (pointer-phase candidate).
    _set(dumps, 1, 0, [0, 0, 55, 55])
    # Change exclusively after pointer release.
    _set(dumps, 1, 4, [0, 0, 0, 2])
    # Unexplained third state after pointer.
    _set(dumps, 1, 8, [0, 0, 3, 5])
    if extra:
        extra(dumps)
    paths = []
    for index, payload in enumerate(dumps):
        path = tmp / f"B{index}.raw"
        path.write_bytes(payload)
        paths.append(path)
    return tuple(paths)

def _set(dumps, page, off, values):
    for index, value in enumerate(values):
        struct.pack_into(">I", dumps[index], page * PAGE + off, value)

class Mem1DiffTests(unittest.TestCase):
    def test_categories_and_phase_counts(self):
        with tempfile.TemporaryDirectory() as td:
            paths = _four_pages(Path(td))
            report, private = subject.compare(paths, nbytes=2*PAGE)
            self.assertEqual(report["word_category_counts"]["idle_changed_or_ambiguous"], 1)
            self.assertEqual(report["word_category_counts"]["pointer_phase_reverted_candidate"], 1)
            self.assertEqual(report["word_category_counts"]["pointer_phase_persistent_candidate"], 1)
            self.assertEqual(report["word_category_counts"]["post_pointer_only_changed"], 1)
            self.assertEqual(report["word_category_counts"]["other_ambiguous"], 1)
            self.assertEqual(report["word_category_counts"]["static"], 2*PAGE//4-5)
            self.assertEqual(report["phase_pair_change_counts"]["idle_comparison_changed_words"], 1)
            self.assertEqual(report["phase_pair_change_counts"]["pointer_comparison_changed_words"], 4)
            self.assertEqual(report["phase_pair_change_counts"]["recovery_comparison_changed_words"], 4)
            self.assertEqual(report["changed_pages_any_phase"], 2)
            self.assertEqual(private["pages_ranked"][0]["page_index_private"], 0)
            self.assertEqual(private["pages_ranked"][0]["candidate_word_offsets_private"], ["+0x008"])
            self.assertFalse(report["game_power_or_player_fields_verified"])
            self.assertFalse(report["source_dump_format_verified"])

    def test_private_detail_only_not_stdout_or_summary(self):
        with tempfile.TemporaryDirectory() as td:
            paths = _four_pages(Path(td))
            report, private = subject.compare(paths, nbytes=2*PAGE)
            serialized = json.dumps(report)
            for leak in ("B0.raw", "page_index_private", "+0x008",
                         "checkpoint_sha256", "0x80000000"):
                self.assertNotIn(leak, serialized)
            self.assertEqual(len(private["checkpoint_sha256_PRIVATE"]), 4)
            self.assertTrue(private["must_not_publish"])

    def test_wrong_lengths_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            paths = list(_four_pages(Path(td)))
            paths[1].write_bytes(paths[1].read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError, "length mismatch"):
                subject.compare(tuple(paths), nbytes=2*PAGE)

    def test_identical_path_reuse_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            paths = _four_pages(Path(td))
            with self.assertRaisesRegex(ValueError, "distinct"):
                subject.compare((paths[0], paths[0], paths[2], paths[3]),
                                nbytes=2*PAGE)

    def test_invalid_region_alignment_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            paths = _four_pages(Path(td))
            with self.assertRaises(ValueError):
                subject.compare(paths, nbytes=2*PAGE-1)
            with self.assertRaises(ValueError):
                subject.compare(paths, nbytes=2*PAGE, page_bytes=10)

    def test_top_pages_ranked_before_cap_not_biased_towards_low_addresses(self):
        with tempfile.TemporaryDirectory() as td:
            def populate(dumps):
                # Last page has more candidate words than first page.
                for off in (40, 44, 48):
                    _set(dumps, 2, off, [0, 0, 99, 0])
            paths = _four_pages(Path(td), n_pages=3, extra=populate)
            with patch.object(subject, "MAX_PRIVATE_PAGES", 1):
                report, private = subject.compare(paths, nbytes=3*PAGE)
            self.assertEqual(private["pages_ranked"][0]["page_index_private"], 2)
            self.assertEqual(len(private["pages_ranked"]), 1)
            self.assertTrue(private["pages_ranked_truncated"])
            self.assertEqual(report["changed_pages_any_phase"], 3)

    def test_private_output_rejects_file_outside_sibling_data(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "Wii-AI-Golf-Data"
            root.mkdir()
            candidate = Path(td) / "not-private.raw"
            candidate.write_bytes(b"TEST")
            with self.assertRaisesRegex(ValueError, "ignored sibling"):
                subject._resolve_private(candidate, root.resolve())

    def test_private_input_symlink_rejected_if_platform_supports(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "Wii-AI-Golf-Data"
            root.mkdir()
            p = root / "private.raw"
            p.write_bytes(b"data")
            link = root / "alias.raw"
            try:
                link.symlink_to(p)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable in this platform")
            with self.assertRaisesRegex(ValueError, "symlink"):
                subject._resolve_private(link, root.resolve())

    def test_missing_path_cli_does_not_echo_private_filename(self):
        args = ["--b0", "SECRET-B0.raw", "--b1", "SECRET-B1.raw",
                "--b2", "SECRET-B2.raw", "--b3", "SECRET-B3.raw",
                "--private-report", "SECRET.json"]
        output = StringIO()
        with redirect_stderr(output):
            self.assertEqual(subject.main(args), 1)
        self.assertIn("invalid private dump", output.getvalue())
        self.assertNotIn("SECRET", output.getvalue())

    def test_no_exported_memory_bytes_or_known_runtime_addresses(self):
        with tempfile.TemporaryDirectory() as td:
            report, private = subject.compare(_four_pages(Path(td)), nbytes=2*PAGE)
            self.assertNotIn("raw", json.dumps(report))
            self.assertNotIn("memory_values", json.dumps(private))
            self.assertNotIn("power_verified", json.dumps(report))

    def test_page_changes_only_in_idle_remain_ambiguous(self):
        with tempfile.TemporaryDirectory() as td:
            def idle_only(dumps):
                _set(dumps, 0, 32, [3, 4, 4, 4])
            paths = _four_pages(Path(td), extra=idle_only)
            report, _ = subject.compare(paths, nbytes=2*PAGE)
            self.assertEqual(report["word_category_counts"]["idle_changed_or_ambiguous"], 2)

if __name__ == "__main__":
    unittest.main()
