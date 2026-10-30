"""No-Dolphin synthetic tests of S000's read-only Clean B1 Event1000 probe."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p0_read_clean_b1_event1000.ps1"


class CleanB1Event1000Tests(unittest.TestCase):
    def test_script_exists_and_disclaims_live_runtime(self):
        body = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("ConvertFrom-P0Event1000Xml", body)
        self.assertIn("Provider", body)
        self.assertIn("FaultingOffset", body)
        self.assertIn("seconds_from_incident", body)
        self.assertIn("ABSTAIN_AMBIGUOUS_MULTIPLE_MATCHES", body)
        self.assertIn("ABSTAIN_NO_MATCH", body)
        self.assertIn("native_crash_cause_verified = $false", body)

    def test_no_game_launch_or_mutating_windows_ops(self):
        body = SCRIPT.read_text(encoding="utf-8").lower()
        for forbidden in (
            "start-process ", "invoke-expression ", "set-winevent",
            "remove-item ", "new-item ", "write-eventlog ",
            "stop-process ", "start-job ", "p/invoke", "readprocessmemory",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, body)

    def test_invalid_xml_and_historical_faults_are_selftested(self):
        body = SCRIPT.read_text(encoding="utf-8")
        for case in (
            "Other Source", "NotDolphin.exe", "c0000006",
            "2026-10-27", "Name=\"Irrelevant\"", "<bad xml",
            "Sensitive?name.dll", "SELFTEST_PASS"
        ):
            with self.subTest(case=case):
                self.assertIn(case, body)

    def test_selftest_is_only_allowed_executable_test(self):
        shell = shutil.which("pwsh") or shutil.which("powershell") or shutil.which("powershell.exe")
        if shell is None:
            self.skipTest("PowerShell unavailable in local Python environment")
        run = subprocess.run(
            [shell, "-NoProfile", "-NonInteractive", "-File", str(SCRIPT), "-SelfTest"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=30, check=False,
        )
        self.assertEqual(run.returncode, 0,
                         "PowerShell synthetic-only selftest returned a nonzero code")
        lines = [line.strip() for line in run.stdout.splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["status"], "SELFTEST_PASS")
        self.assertEqual(payload["positive"], 1)
        self.assertGreaterEqual(payload["negative"], 8)
        self.assertIs(payload["event_log_accessed"], False)
        self.assertIs(payload["dolphin_launched"], False)
        self.assertNotIn("Private", run.stdout)
        self.assertNotIn("Sensitive", run.stdout)


if __name__ == "__main__":
    unittest.main()
