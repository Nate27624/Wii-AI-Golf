"""Offline synthetic tests for standalone PS5 seven manual snapshot audit.

PowerShell is mandatory and tests fail, never silently skip, when missing.
Raw game memory / Dolphin are never loaded. Full-size sparse fake banks verify
that the real 24/64 MiB strict gate is exercised.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ORIGINAL = Path(__file__).resolve().parents[1] / "scripts" / "Invoke-P0SevenDumpAudit.ps1"
SHELL = shutil.which("powershell.exe") or shutil.which("powershell") or shutil.which("pwsh")
MEM1 = 24 * 1024 * 1024
MEM2 = 64 * 1024 * 1024


class SevenManualDumpTests(unittest.TestCase):
    def setUp(self):
        if not SHELL:
            raise RuntimeError("PowerShell 5.1 or 7 is REQUIRED; never skip entire test suite")
        self.temp = tempfile.TemporaryDirectory(prefix="golf-seven-fake-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / "Dump"
        self.folder.mkdir()
        self.script = Path(self.temp.name) / "Invoke-P0SevenDumpAudit.ps1"
        shutil.copy2(ORIGINAL, self.script)

    def run_ps(self, mode="Analyze"):
        return subprocess.run([
            SHELL, "-NoProfile", "-NonInteractive", "-File", str(self.script),
            "-DumpDirectory", str(self.folder), "-Mode", mode,
        ], text=True, capture_output=True, timeout=130)

    def fixture(self, phase, *, good_header=True, altered=False):
        for which, size in ((1, MEM1), (2, MEM2)):
            path = self.folder / f"{phase}.{which}.raw"
            with path.open("wb") as f:
                f.truncate(size)
                if which == 1:
                    f.seek(0)
                    f.write(b"RSPE01\x00\x01" if good_header else b"OTHER!\x00\x00")
                if altered:
                    f.seek(4097 if which == 1 else 8192)
                    f.write(b"\x7f")
        return self.folder / f"{phase}.1.raw"

    def test_incomplete_one_named_bank_is_inventory_not_result(self):
        path = self.folder / "1.1.raw"
        with path.open("wb") as f:
            f.truncate(MEM1)
            f.seek(0)
            f.write(b"RSPE01\x00\x01")
        result = self.run_ps()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("NO WITHIN-SHOT NATIVE PAIRS READY", result.stdout + result.stderr)
        self.assertNotIn("PRIVATE REPORT WRITTEN", result.stdout)
        self.assertIn("MEM1_24MiB", result.stdout)

    def test_confounded_3_vs_4_not_pretended_to_be_a_comparison(self):
        self.fixture(3)
        self.fixture(4, altered=True)
        result = self.run_ps()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("NO WITHIN-SHOT NATIVE PAIRS READY", result.stdout + result.stderr)
        self.assertNotIn("P3_to_A4", result.stdout)

    def test_same_wedge_5_to_6_creates_private_report_and_delta(self):
        self.fixture(5)
        self.fixture(6, altered=True)
        result = self.run_ps()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("W5_to_W6_near_apex_to_descending", result.stdout)
        self.assertIn("MEM1 changed 1 pages", result.stdout)
        self.assertIn("MEM2 changed 1 pages", result.stdout)
        self.assertNotIn("RSPE01", result.stdout)
        self.assertNotIn(str(self.folder), result.stdout)
        reports = list(self.folder.glob("P0-SEVEN-AUDIT-*-PRIVATE/report-RAW-PRIVATE.json"))
        self.assertEqual(len(reports), 1)
        data = json.loads(reports[0].read_text())
        self.assertEqual(len(data["comparisons"]), 1)
        c = data["comparisons"][0]
        self.assertEqual(c["mem1"]["changed_bytes"], 1)
        self.assertEqual(c["mem2"]["changed_bytes"], 1)
        self.assertEqual(c["mem1"]["changed_4096_byte_pages"], 1)
        self.assertEqual(c["mem2"]["changed_4096_byte_pages"], 1)
        self.assertFalse(data["allowed_to_publish"])
        self.assertFalse(data["p0_ball_world_xyz_verified"])
        self.assertFalse(data["approved_for_model_training"])

    def test_three_phase_temporal_mask_classifies_reversion_and_continuing_pages(self):
        # Synthetic pages: W5 baseline zero; W6 changes pages 1,2,3;
        # W7 retains page1, restores page2, evolves page3 and adds page4.
        # A=5->6 {1,2,3}; B=6->7 {2,3,4};
        # C=5->7 {1,3,4}; common=2, all-three=1, restored=1.
        self.fixture(5)
        self.fixture(6)
        self.fixture(7)
        for bank in (1, 2):
            def alter(phase, changes):
                path = self.folder / f"{phase}.{bank}.raw"
                with path.open("r+b") as out:
                    for page, value in changes:
                        out.seek(page * 4096 + 1)
                        out.write(bytes([value]))
            alter(6, [(1, 0x10), (2, 0x30), (3, 0x50)])
            alter(7, [(1, 0x10), (3, 0x60), (4, 0x70)])
        result = self.run_ps()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("WEDGE TEMPORAL MEM1", result.stdout)
        self.assertIn("WEDGE TEMPORAL MEM2", result.stdout)
        reports = list(self.folder.glob("P0-SEVEN-AUDIT-*-PRIVATE/report-RAW-PRIVATE.json"))
        self.assertEqual(len(reports), 1)
        data = json.loads(reports[0].read_text())
        for bank in ("MEM1", "MEM2"):
            m = data["wedge_temporal_page_triage"][bank]
            self.assertEqual(m["changed_in_both_adjacent_intervals"], 2)
            self.assertEqual(m["changed_in_all_three_pairwise_contrasts"], 1)
            self.assertEqual(m["changed_in_both_adjacent_intervals_but_first_equals_last_page"], 1)
            self.assertEqual(m["changed_only_in_first_adjacent_interval"], 1)
            self.assertEqual(m["changed_only_in_second_adjacent_interval"], 1)
            self.assertTrue(m["three_state_page_triangle_consistent"])
            self.assertTrue(m["page_mask_intersection_is_NOT_ball_world_xyz"])

    def test_wrong_game_header_rejected_before_any_report(self):
        self.fixture(5, good_header=False)
        self.fixture(6, altered=True)
        result = self.run_ps()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Wrong RSPE01 Rev1", result.stderr)
        self.assertEqual(len(list(self.folder.glob("P0-SEVEN-AUDIT-*-PRIVATE"))), 0)

    def test_incorrect_bank_length_cannot_pass_as_MEM2(self):
        self.fixture(5)
        p = self.fixture(6)
        second = self.folder / "6.2.raw"
        with second.open("r+b") as f:
            f.truncate(32 * 1024 * 1024)  # Neither native bank length
        result = self.run_ps()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('wrong sizes: 1', result.stdout)
        self.assertIn('MEM2_64MiB', result.stdout)
        self.assertIn("NO WITHIN-SHOT NATIVE PAIRS READY", result.stdout + result.stderr)
        self.assertNotIn("PRIVATE REPORT WRITTEN", result.stdout)

    def test_files_without_operator_phase_name_are_not_assumed(self):
        (self.folder / "other.raw").write_bytes(b"test")
        result = self.run_ps("Inventory")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Unmatched .raw names: 1", result.stdout)
        self.assertNotIn("PRIVATE REPORT WRITTEN", result.stdout)


if __name__ == "__main__":
    unittest.main()
