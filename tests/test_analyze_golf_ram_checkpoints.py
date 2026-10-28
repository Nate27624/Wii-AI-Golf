"""License-safe synthetic tests for offline, private four-checkpoint RAM diff."""
import json
from pathlib import Path
import struct
import tempfile
import unittest

from scripts.analyze_golf_ram_checkpoints import analyze_four, _private_output_path


def words(*values):
    return struct.pack(">" + "I" * len(values), *values)


class FourCheckpointTests(unittest.TestCase):
    def test_reversible_aim_and_idle_noise(self):
        b0 = words(10, 5, 12, 1)
        b1 = words(10, 6, 12, 1)  # idle drift only in word 1
        b2 = words(20, 7, 12, 3)  # word 0 reversible; word 3 persistent
        b3 = words(10, 8, 12, 3)
        r = analyze_four(b0, b1, b2, b3, page_bytes=8)
        c = r["counts"]
        self.assertEqual(c["reversible_aim_candidates"], 1)
        self.assertEqual(c["persistent_aim_candidates"], 1)
        self.assertEqual(c["idle_changed_words"], 1)
        self.assertEqual(c["ambiguous_aim_words"], 1)
        self.assertEqual(r["candidate_page_count"], 2)
        self.assertEqual(r["top_candidate_pages"][0]["page_index"], 0)
        self.assertFalse(r["game_power_verified"])
        self.assertTrue(r["local_only_no_upload"])

    def test_all_equal_null(self):
        w = words(0, 42, 0xDEADBEEF)
        r = analyze_four(w, w, w, w)
        self.assertEqual(r["candidate_page_count"], 0)
        self.assertEqual(sum(r["counts"].values()), 0)

    def test_big_endian_and_byte_counts(self):
        r = analyze_four(words(0), words(0), words(0x01020304), words(0))
        self.assertEqual(r["changed_bytes"], {"idle": 0, "aim": 4, "return": 4})
        self.assertEqual(r["top_candidate_pages"][0]["local_candidate_offsets"][0]["relative_byte_offset"], 0)

    def test_mismatch_and_invalid_limits(self):
        for args in [(b"", b"", b"", b""), (b"123",)*4, (b"1234", b"12", b"1234", b"1234")]:
            with self.assertRaises(ValueError):
                analyze_four(*args)
        with self.assertRaises(ValueError):
            analyze_four(*([b"0000"] * 4), top_pages=101)

    def test_private_output_rejects_repo_and_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            repo = base / "Wii-AI-Golf" / "scripts" / "analyze.py"
            private = base / "Wii-AI-Golf-Data" / "captures" / "report.json"
            self.assertEqual(_private_output_path(str(private), repo), private)
            with self.assertRaises(ValueError):
                _private_output_path(str(base / "Wii-AI-Golf" / "report.json"), repo)
            private.parent.mkdir(parents=True)
            private.write_text(json.dumps({}))
            with self.assertRaises(ValueError):
                _private_output_path(str(private), repo)


if __name__ == "__main__":
    unittest.main()
