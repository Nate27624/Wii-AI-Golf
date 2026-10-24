"""Use the integrator's exact pre-start sequence, never a duplicated copy."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "start_golf_recording.py"
spec = importlib.util.spec_from_file_location("golf_recording_launcher_under_test", SCRIPT)
start = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(start)


class BootAndCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "scripts").mkdir()
        (self.root / "research").mkdir()
        (self.root / "src").mkdir()
        (self.root / "scripts" / "launch_hitting_green.py").write_text("# existing integrator")
        self.catalog = self.root / "research" / "savestates.local.json"
        self.catalog.write_text(json.dumps({
            "schema_version": 1,
            "profiles": [{"name": "green-pre-start", "slot": 2,
                          "description": "pre-start checkpoint", "game_id": "RSPE01"}],
        }))

    def test_attach_uses_integrators_menu_not_our_own(self):
        cmd = start.boot_command(
            canonical=self.root, profile="green-pre-start",
            port=55355, attach_running=True)
        self.assertEqual(Path(cmd[1]).name, "launch_hitting_green.py")
        self.assertIn("--send-live", cmd)
        self.assertIn("--attach-running", cmd)
        self.assertNotIn("--swing", cmd)
        self.assertEqual(cmd[cmd.index("--profile") + 1], "green-pre-start")
        self.assertEqual(cmd[cmd.index("--catalog") + 1], str(self.catalog))
        self.assertNotIn("menu_sequence.py", " ".join(cmd))

    def test_fresh_uses_exact_selected_paths_and_does_not_swing(self):
        files = [self.root / n for n in ("Dolphin.exe", "mcp_bridge_swing.py", "WiiSports.wbfs")]
        for f in files:
            f.touch()
        cmd = start.boot_command(
            canonical=self.root, profile="green-pre-start",
            port=55355, attach_running=False,
            dolphin=files[0], bridge=files[1], game=files[2])
        self.assertNotIn("--attach-running", cmd)
        self.assertNotIn("--swing", cmd)
        for flag, path in zip(("--dolphin", "--bridge", "--game"), files):
            self.assertEqual(cmd[cmd.index(flag) + 1], str(path))

    def test_invalid_or_missing_boot_resources_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "fresh launch requires"):
            start.boot_command(canonical=self.root, profile="green-pre-start",
                               port=55355, attach_running=False)
        with self.assertRaises(FileNotFoundError):
            start.boot_command(canonical=self.root, profile="green-pre-start",
                               port=55355, attach_running=False,
                               dolphin=self.root / "missing.exe",
                               bridge=self.root / "missing.py",
                               game=self.root / "missing.wbfs")
        (self.root / "scripts" / "launch_hitting_green.py").unlink()
        with self.assertRaises(FileNotFoundError):
            start.boot_command(canonical=self.root, profile="green-pre-start",
                               port=55355, attach_running=True)

    def test_scan_command_is_read_only_and_does_not_duplicate_reset(self):
        cmd = start.scan_command(
            seconds=25, interval=0.6, profile="broad", port=55355,
            no_upload=True)
        self.assertIn("discover_golf_motion.py", cmd[1])
        self.assertEqual(cmd[cmd.index("--profile") + 1], "broad")
        self.assertIn("--no-upload", cmd)
        for forbidden in ("--send-live", "--swing", "--startup-profile",
                          "--savestate-profile", "--attach-running"):
            self.assertNotIn(forbidden, cmd)

    def test_boot_must_succeed_before_scanner_starts(self):
        with patch.object(start, "bridge_open", return_value=True), patch.object(
            start.subprocess, "run",
            return_value=subprocess.CompletedProcess([], 1)
        ) as run:
            self.assertEqual(start.main(["--canonical", str(self.root), "--attach-running"]), 1)
            run.assert_called_once()

    def test_attached_flow_runs_integrator_then_scan_with_isolated_paths(self):
        def side_effect(*args, **kwargs):
            calls.append((args[0], kwargs))
            return subprocess.CompletedProcess(args[0], 0)
        calls = []
        with patch.object(start, "bridge_open", return_value=True), patch.object(
            start.subprocess, "run", side_effect=side_effect
        ):
            result = start.main(["--canonical", str(self.root),
                                 "--attach-running", "--seconds", "12",
                                 "--scan-profile", "fast", "--no-upload"])
        self.assertEqual(result, 0)
        self.assertEqual(len(calls), 2)
        boot, boot_opts = calls[0]
        scan, scan_opts = calls[1]
        self.assertIn("launch_hitting_green.py", boot[1])
        self.assertIn("discover_golf_motion.py", scan[1])
        self.assertIn("--send-live", boot)
        self.assertNotIn("--send-live", scan)
        self.assertEqual(boot_opts["env"]["PYTHONPATH"], str(self.root / "src"))
        self.assertEqual(scan_opts["env"]["PYTHONPATH"], str(start.EVALUATION_ROOT / "src"))

    def test_unavailable_bridge_never_loads_savestate(self):
        with patch.object(start, "bridge_open", return_value=False), patch.object(
            start.subprocess, "run"
        ) as run:
            with self.assertRaisesRegex(ConnectionError, "No bridge listening"):
                start.main(["--canonical", str(self.root), "--attach-running"])
            run.assert_not_called()

    def test_missing_profile_never_sends_menu_buttons(self):
        with patch.object(start, "bridge_open", return_value=True), patch.object(
            start.subprocess, "run"
        ) as run:
            with self.assertRaisesRegex(ValueError, "unknown savestate"):
                start.main(["--canonical", str(self.root),
                            "--savestate-profile", "not-registered"])
            run.assert_not_called()

    def test_fresh_rejects_already_running_bridge(self):
        with patch.object(start, "bridge_open", return_value=True), patch.object(
            start.subprocess, "run"
        ) as run:
            with self.assertRaisesRegex(RuntimeError, "already listening"):
                start.main(["--canonical", str(self.root), "--fresh"])
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
