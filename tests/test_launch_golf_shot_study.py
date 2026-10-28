"""No-emulator synthetic tests for source-local shot-study intro."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import launch_golf_shot_study as launcher


class StudyIntroTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.main = root / "Wii-AI-Golf"
        self.clean = root / "tools" / "FelkDolphin-Clean"
        self.bridge = root / "tools" / "bridge.py"
        (self.main / "scripts").mkdir(parents=True)
        (self.main / "research").mkdir()
        (self.clean / "User" / "Config").mkdir(parents=True)
        for p in (self.main / "scripts" / "launch_golf.py",
                  self.clean / "Dolphin.exe", self.clean / "portable.txt",
                  self.clean / "User" / "Config" / "WiimoteNew.ini",
                  self.bridge):
            p.write_text("test")
        self.game = root / "test-game.rvz"
        self.game.write_text("test")
        (self.main / "research" / "launch.local.json").write_text(
            json.dumps({"schema_version": 1, "game": str(self.game)}))
        self.catalog = self.main / "research" / "savestates.local.json"
        self.catalog.write_text(json.dumps({"schema_version": 1, "profiles": [
            {"name": "green-pre-start", "slot": 7}]}))
        self.args = ["--main-repo", str(self.main),
                     "--clean-dolphin", str(self.clean),
                     "--bridge", str(self.bridge)]

    def test_canonical_registered_intro_and_no_swing(self):
        command, metadata = launcher.build_command(
            main=self.main, clean=self.clean, bridge=self.bridge)
        self.assertIn(str(self.main / "scripts" / "launch_golf.py"), command)
        self.assertEqual(command[command.index("--profile")+1],
                         "green-pre-start")
        self.assertNotIn("--swing", command)
        self.assertEqual(metadata["slot"], 7)
        self.assertFalse(metadata["live_savestate_bytes_independently_verified"])

    def test_dry_run_never_starts_emulator(self):
        with patch.object(launcher, "_port_in_use", return_value=False), \
             patch.object(launcher.subprocess, "run") as run, \
             redirect_stdout(StringIO()):
            result = launcher.main(self.args + ["--dry-run"])
        self.assertEqual(result, 0)
        run.assert_not_called()

    def test_live_delegates_only_one_existing_launcher(self):
        with patch.object(launcher, "_port_in_use", return_value=False), \
             patch.object(launcher.subprocess, "run",
                          return_value=SimpleNamespace(returncode=0)) as run, \
             redirect_stdout(StringIO()):
            self.assertEqual(launcher.main(self.args), 0)
        self.assertEqual(run.call_count, 1)
        self.assertNotIn("--swing", run.call_args.args[0])

    def test_active_bridge_refuses_second_instance(self):
        with patch.object(launcher, "_port_in_use", return_value=True), \
             patch.object(launcher.subprocess, "run") as run, \
             redirect_stdout(StringIO()):
            self.assertEqual(launcher.main(self.args), 1)
        run.assert_not_called()

    def test_missing_named_state_or_clean_user_fails_closed(self):
        self.catalog.write_text(json.dumps({"schema_version":1,"profiles":[]}))
        with self.assertRaises(ValueError):
            launcher.build_command(main=self.main,clean=self.clean,
                                   bridge=self.bridge)
        self.catalog.write_text(json.dumps({"schema_version":1,"profiles":[
            {"name":"green-pre-start","slot":7}]}))
        (self.clean / "User" / "Config" / "WiimoteNew.ini").unlink()
        with self.assertRaises(ValueError):
            launcher.build_command(main=self.main,clean=self.clean,
                                   bridge=self.bridge)

    def test_port_and_bridge_identity_fail_closed(self):
        with self.assertRaises(ValueError):
            launcher.build_command(main=self.main,clean=self.clean,
                                   bridge=self.bridge,port=0)
        self.bridge.unlink()
        with self.assertRaises(ValueError):
            launcher.build_command(main=self.main,clean=self.clean,
                                   bridge=self.bridge)


if __name__ == "__main__":
    unittest.main()
