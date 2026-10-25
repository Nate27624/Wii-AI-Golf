"""Offline source-marker audit tests; never launch Dolphin or connect to RPC."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_local_swing_bridge import (
    ATOMIC, AUTOLOAD, NEUTRAL_V2, SWING_V1,
    audit_local_bridge, inspect_bridge, prepare_legacy_copy,
)


def legacy() -> str:
    return ATOMIC + "\n" + SWING_V1 + "\n" + "def synthetic_bridge(): return None\n"


def modern() -> str:
    return legacy() + NEUTRAL_V2 + "\n"


class LocalBridgeAuditTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.current = self.root / "mcp_bridge_swing.py"
        self.backup = self.current.with_name(self.current.name + ".before-neutral-v2.bak")

    def test_missing_report_has_no_game_actions(self):
        report = audit_local_bridge(self.current)
        self.assertEqual(report["current"]["revision"], "missing")
        self.assertEqual(report["saved_pre_v2_backup"]["revision"], "missing")
        self.assertFalse(report["v1_isolated_trial_possible"])
        self.assertFalse(self.current.exists())

    def test_recognizes_legacy_and_v2_from_local_markers(self):
        self.current.write_text(modern(), encoding="utf-8")
        self.backup.write_text(legacy(), encoding="utf-8")
        report = audit_local_bridge(self.current)
        self.assertEqual(report["current"]["revision"], "V2-neutral-button-only")
        self.assertEqual(report["saved_pre_v2_backup"]["revision"], "V1-neutral-swing-calls")
        self.assertTrue(report["v1_isolated_trial_possible"])
        self.assertTrue(report["controlled_protocol_difference_detected"])
        self.assertEqual(report["neutral_set_wiimote_swing_calls_89_frame_example"]["V2"], 35)
        self.assertEqual(len(report["current"]["sha256"]), 64)

    def test_v1_backup_autoload_disallowed(self):
        self.current.write_text(modern())
        self.backup.write_text(legacy() + AUTOLOAD)
        report = audit_local_bridge(self.current)
        self.assertFalse(report["v1_isolated_trial_possible"])
        with self.assertRaisesRegex(ValueError, "missing/unknown/autoloading"):
            prepare_legacy_copy(self.current)

    def test_v2_backup_or_unknown_source_not_a_legacy_repro(self):
        self.current.write_text(modern())
        self.backup.write_text(modern())
        with self.assertRaises(ValueError):
            prepare_legacy_copy(self.current)
        self.backup.write_text("unrelated arbitrary executable code")
        self.assertEqual(inspect_bridge(self.backup)["revision"], "unknown-or-unexpected")
        with self.assertRaises(ValueError):
            prepare_legacy_copy(self.current)

    def test_opt_in_copy_preserves_all_existing_bridge_sources(self):
        self.current.write_text(modern())
        self.backup.write_text(legacy())
        before = self.current.read_bytes()
        original_backup = self.backup.read_bytes()
        result = prepare_legacy_copy(self.current)
        self.assertEqual(result.name, "mcp_bridge_swing_legacy_eval.py")
        self.assertEqual(result.read_bytes(), original_backup)
        self.assertEqual(self.current.read_bytes(), before)
        self.assertEqual(self.backup.read_bytes(), original_backup)
        self.assertEqual(prepare_legacy_copy(self.current), result)
        self.assertEqual(inspect_bridge(result)["revision"], "V1-neutral-swing-calls")

    def test_never_overwrites_existing_other_program_or_bridge(self):
        self.current.write_text(modern())
        self.backup.write_text(legacy())
        occupied = self.root / "mcp_bridge_swing_legacy_eval.py"
        occupied.write_text("# unrelated")
        with self.assertRaises(FileExistsError):
            prepare_legacy_copy(self.current)
        self.assertEqual(occupied.read_text(), "# unrelated")
        for target in (self.current, self.backup, self.root / "not_python.bak"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                prepare_legacy_copy(self.current, destination=target)

    def test_isolated_python_cli_readonly(self):
        self.current.write_text(modern())
        self.backup.write_text(legacy())
        cmd = [sys.executable, "-I", str(ROOT / "scripts" / "audit_local_swing_bridge.py"),
               "--bridge", str(self.current)]
        first = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        details = json.loads(first.stdout)
        self.assertTrue(details["v1_isolated_trial_possible"])
        self.assertFalse((self.root / "mcp_bridge_swing_legacy_eval.py").exists())
        second = subprocess.run(cmd + ["--prepare-legacy-trial"], capture_output=True, text=True)
        self.assertEqual(second.returncode, 0, second.stderr)
        result = json.loads(second.stdout)
        self.assertEqual(result["legacy_eval_copy"]["revision"], "V1-neutral-swing-calls")
        self.assertIn("run_golf_experiment.py", result["optional_manual_full_start_example"])
        self.assertIn("collect_outcome_transition.py", result["optional_manual_full_start_example"])
        self.assertIn("--bridge", result["optional_manual_full_start_example"])


if __name__ == "__main__":
    unittest.main()
