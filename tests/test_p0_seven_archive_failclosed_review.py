"""Synthetic review-only regression checks for seven-bank archive fail-closed behavior.

Never reads or fabricates native 24/64 MiB game bank contents.
"""
from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sys
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))
import audit_p0_seven_numbered_source_pairs_private as seven


def manifest():
    captures = []
    for n in range(1, 8):
        captures.append({
            "capture_number": n,
            "banks": [
                {"file": f"{n}.{i+1}.raw", "bank": ("MEM1", "MEM2")[i],
                 "bytes": seven.SIZE[i], "copy_verified": True,
                 "sha256": "a" * 64}
                for i in range(2)
            ],
        })
    return {
        "kind": "p0-private-numbered-capture-inventory",
        "training_approved": False,
        "human_phase_file_mapping_verified": False,
        "capture_count": 7,
        "capture_numbers": list(range(1, 8)),
        "captures": captures,
    }


class SevenArchiveFailClosedReview(unittest.TestCase):
    def _fixture(self, root: Path, value):
        folder = root / "captures" / "cohort-PRIVATE"
        folder.mkdir(parents=True)
        (folder / "manifest-PRIVATE.json").write_text(json.dumps(value), encoding="utf-8")
        return folder

    def test_malformed_json_root_capture_and_bank_nodes_abstain_without_traceback(self):
        bad_cases = []
        bad_cases.append(("root_array", []))
        bad_cases.append(("root_null", None))
        a = manifest()
        a["captures"][0] = None
        bad_cases.append(("capture_null", a))
        b = manifest()
        b["captures"][0]["banks"][0] = None
        bad_cases.append(("bank_null", b))
        c = manifest()
        c["captures"][0]["banks"][0] = 42
        bad_cases.append(("bank_number", c))
        for label, value in bad_cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                archive = self._fixture(root, value)
                # Stub file access: these malformed manifests must be rejected
                # before any bank hash / native data operation.
                with patch.object(seven.src.selected, "DATA_ROOT", root), \
                     patch.object(seven.src, "_file", side_effect=AssertionError("bank opened")), \
                     patch.object(seven.src, "_hash_file", side_effect=AssertionError("bank hashed")):
                    output = StringIO()
                    with redirect_stderr(output):
                        rc = seven.main(["--archive", str(archive)])
                    self.assertEqual(rc, 2)
                    self.assertIn("ABSTAINED", output.getvalue())
                    self.assertNotIn("Traceback", output.getvalue())
                    self.assertNotIn(str(root), output.getvalue())

    def test_wellformed_fake_metadata_passes_precheck_with_stubbed_sha(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = self._fixture(root, manifest())
            with patch.object(seven.src.selected, "DATA_ROOT", root), \
                 patch.object(seven.src, "_file", return_value=Path("fake")), \
                 patch.object(seven.src, "_hash_file", return_value="a" * 64):
                self.assertEqual(set(seven._check_archive(archive)), set(range(1, 8)))

    def test_after_read_hash_guard_fails_closed_and_passes_when_stable(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for n in range(1, 8):
                for i in (1, 2):
                    (folder / f"{n}.{i}.raw").write_bytes(b"test")
            mock_folders = {n: folder for n in range(1, 8)}
            patches = [
                patch.object(seven, "SIZE", (4, 4)),
                patch.object(seven.src, "_file",
                             side_effect=lambda parent, filename, size: parent / filename),
                patch.object(seven.roster, "TwoBankReader",
                             side_effect=lambda mem1, mem2: (mem1, mem2)),
                patch.object(seven, "_get", return_value={"synthetic": True}),
                patch.object(seven, "summarize", return_value={"synthetic": True}),
            ]
            from contextlib import ExitStack
            with ExitStack() as stack:
                for item in patches:
                    stack.enter_context(item)
                with patch.object(seven, "_check_archive", side_effect=[
                        mock_folders, ValueError("post-read hash drift")]) as check:
                    with self.assertRaisesRegex(ValueError, "post-read hash drift"):
                        seven.analyze(folder)
                    self.assertEqual(check.call_count, 2)
                with patch.object(seven, "_check_archive",
                                  side_effect=[mock_folders, mock_folders]) as check:
                    self.assertEqual(seven.analyze(folder), {"synthetic": True})
                    self.assertEqual(check.call_count, 2)


if __name__ == "__main__":
    unittest.main()
