"""Offline tests for one-command Dolphin + bridge + named-state launcher."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import launch_golf


class OneCommandLauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.game = self.root / "Wii Sports.rvz"
        self.game.write_bytes(b"stub for path test; not a ROM")
        self.config = self.root / "research" / "launch.local.json"
        self.exe = self.root / "Dolphin.exe"
        self.exe.write_bytes(b"")
        self.bridge = self.root / "mcp_bridge_swing.py"
        self.bridge.write_text("# stub\n")
        self.catalog = self.root / "savestates.local.json"
        self.catalog.write_text('{"schema_version":1,"profiles":[]}')

    def test_first_launch_prompts_once_and_saves_ignored_local_config(self):
        asked = []
        game = launch_golf.resolve_game(
            None, self.config, prompt=lambda question: asked.append(question) or str(self.game)
        )
        self.assertEqual(game, self.game.resolve())
        self.assertEqual(json.loads(self.config.read_text())["game"], str(self.game))
        again = launch_golf.resolve_game(
            None, self.config, prompt=lambda _: self.fail("unexpected second prompt")
        )
        self.assertEqual(again, game)
        self.assertEqual(len(asked), 1)

    def test_game_argument_overrides_and_persists(self):
        got = launch_golf.resolve_game(f'"{self.game}"', self.config)
        self.assertEqual(got, self.game.resolve())
        self.assertEqual(launch_golf.read_config(self.config)["game"], str(got))

    def test_missing_or_invalid_game_rejected_without_launch(self):
        with self.assertRaises(ValueError):
            launch_golf.game_path(str(self.root / "nonexistent.rvz"))
        bad = self.root / "something.txt"
        bad.write_text("no")
        with self.assertRaises(ValueError):
            launch_golf.game_path(str(bad))

    def test_command_includes_existing_start_workflow_and_all_paths(self):
        cmd = launch_golf.make_start_command(
            game=self.game, dolphin=self.exe, bridge=self.bridge,
            profile="green-first-shot", catalog=self.catalog, port=55355
        )
        self.assertIn("savestate_session.py", cmd[1])
        self.assertEqual(cmd[cmd.index("start") + 1], "green-first-shot")
        self.assertEqual(cmd[cmd.index("--dolphin") + 1], str(self.exe))
        self.assertEqual(cmd[cmd.index("--bridge") + 1], str(self.bridge))
        self.assertEqual(cmd[cmd.index("--game") + 1], str(self.game))
        self.assertIn(str(self.catalog), cmd)
        self.assertNotIn("capture", cmd)
        self.assertNotIn("--overwrite-slot", cmd)

    def test_missing_bridge_fails_before_any_subprocess(self):
        with self.assertRaisesRegex(ValueError, "bridge"):
            launch_golf.make_start_command(
                game=self.game, dolphin=self.exe, bridge=self.root / "missing.py",
                profile="green-first-shot", catalog=self.catalog, port=55355
            )

    def test_default_launch_only_then_optional_single_swing(self):
        argv = [
            "--game", str(self.game), "--config", str(self.config),
            "--bridge", str(self.bridge), "--dolphin", str(self.exe),
            "--catalog", str(self.catalog),
        ]
        with patch.object(launch_golf.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(launch_golf.main(argv), 0)
            self.assertEqual(run.call_count, 1)
            self.assertIn("start", run.call_args.args[0])

        with patch.object(launch_golf.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(launch_golf.main(argv + ["--swing", "--preset", "reverse"]), 0)
            self.assertEqual(run.call_count, 2)
            self.assertIn("start", run.call_args_list[0].args[0])
            self.assertIn("--send-live-swing", run.call_args_list[1].args[0])
            self.assertIn("reverse", run.call_args_list[1].args[0])

    def test_launch_error_never_sends_swing(self):
        argv = [
            "--game", str(self.game), "--config", str(self.config),
            "--bridge", str(self.bridge), "--dolphin", str(self.exe),
            "--catalog", str(self.catalog), "--swing"
        ]
        with patch.object(launch_golf.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)) as run:
            self.assertEqual(launch_golf.main(argv), 1)
            run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
