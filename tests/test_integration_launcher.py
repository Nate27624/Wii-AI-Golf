"""Offline tests for one-command Dolphin + bridge + named-state launcher."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

# Make unittest discovery use this source checkout, not a stale pip editable install.
import sys
_TEST_REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (str(_TEST_REPO_ROOT), str(_TEST_REPO_ROOT / "src")):
    if _path in sys.path:
        sys.path.remove(_path)
    sys.path.insert(0, _path)

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
        # Build a portable Dolphin fixture with a real-input controller profile.
        (self.root / "portable.txt").touch()
        self.user = self.root / "User"
        self.ini = self.user / "Config" / "WiimoteNew.ini"
        self.ini.parent.mkdir(parents=True)
        self.ini.write_text("[Wiimote1]\nSource = 2\nExtension = Nunchuk\nButtons/A = F\n")
        port_probe = patch.object(launch_golf, "is_bridge_port_open", return_value=False)
        port_probe.start()
        self.addCleanup(port_probe.stop)
        self.bridge = self.root / "mcp_bridge_swing.py"
        self.bridge.write_text("# stub\n")
        self.catalog = self.root / "savestates.local.json"
        self.catalog.write_text(json.dumps({"schema_version": 1, "profiles": [
            {"name": "green-first-shot", "slot": 1, "description": "At the ball"},
            {"name": "green-pre-start", "slot": 2, "description": "At instructions screen"}
        ]}))

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

    def test_command_uses_verified_intro_and_all_paths(self):
        cmd = launch_golf.make_start_command(
            game=self.game, dolphin=self.exe, bridge=self.bridge,
            profile="green-pre-start", catalog=self.catalog, port=55355
        )
        self.assertIn("launch_hitting_green.py", cmd[1])
        self.assertEqual(cmd[cmd.index("--profile") + 1], "green-pre-start")
        self.assertIn("--send-live", cmd)
        self.assertNotIn("start", cmd)
        self.assertEqual(cmd[cmd.index("--dolphin") + 1], str(self.exe))
        self.assertEqual(cmd[cmd.index("--bridge") + 1], str(self.bridge))
        self.assertEqual(cmd[cmd.index("--game") + 1], str(self.game))
        self.assertIn(str(self.catalog), cmd)
        self.assertNotIn("capture", cmd)
        self.assertNotIn("--overwrite-slot", cmd)

    def test_standard_launcher_rejects_another_checkpoint_before_game_input(self):
        with self.assertRaisesRegex(ValueError, "green-pre-start"):
            launch_golf.make_start_command(
                game=self.game, dolphin=self.exe, bridge=self.bridge,
                profile="green-first-shot", catalog=self.catalog, port=55355
            )

    def test_default_profile_is_verified_pre_start_checkpoint(self):
        launch_golf.resolve_game(str(self.game), self.config)
        picked = launch_golf.resolve_profile(None, None, self.config, self.catalog)
        self.assertEqual((picked.name, picked.slot), ("green-pre-start", 2))

    def test_saved_legacy_at_ball_profile_does_not_bypass_intro(self):
        launch_golf.resolve_game(str(self.game), self.config)
        launch_golf.resolve_profile("green-first-shot", None, self.config, self.catalog)
        argv = [
            "--game", str(self.game), "--config", str(self.config),
            "--bridge", str(self.bridge), "--dolphin", str(self.exe),
            "--catalog", str(self.catalog),
        ]
        with patch.object(launch_golf.subprocess, "run") as run:
            self.assertEqual(launch_golf.main(argv), 1)
            run.assert_not_called()

    def test_missing_bridge_fails_before_any_subprocess(self):
        with self.assertRaisesRegex(ValueError, "bridge"):
            launch_golf.make_start_command(
                game=self.game, dolphin=self.exe, bridge=self.root / "missing.py",
                profile="green-pre-start", catalog=self.catalog, port=55355
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
            self.assertIn("launch_hitting_green.py", run.call_args.args[0][1])
            self.assertIn("--send-live", run.call_args.args[0])

        with patch.object(launch_golf.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(launch_golf.main(argv + ["--swing", "--preset", "reverse"]), 0)
            self.assertEqual(run.call_count, 2)
            self.assertIn("launch_hitting_green.py", run.call_args_list[0].args[0][1])
            self.assertIn("--send-live", run.call_args_list[0].args[0])
            self.assertIn("--send-live-swing", run.call_args_list[1].args[0])
            self.assertIn("--attach-running", run.call_args_list[1].args[0])
            self.assertIn("reverse", run.call_args_list[1].args[0])
            self.assertEqual(run.call_args_list[1].args[0][
                run.call_args_list[1].args[0].index("--follow-through-frames")+1], "30")
            self.assertEqual(run.call_args_list[1].args[0][
                run.call_args_list[1].args[0].index("--a-setup-frames")+1], "12")
            self.assertEqual(run.call_args_list[1].args[0][
                run.call_args_list[1].args[0].index("--a-prime-frames")+1], "60")

    def test_launch_forwards_extended_followthrough_to_child_after_verified_intro(self):
        argv = [
            "--game", str(self.game), "--config", str(self.config),
            "--bridge", str(self.bridge), "--dolphin", str(self.exe),
            "--catalog", str(self.catalog), "--slot", "2", "--swing",
            "--follow-through-frames", "45", "--a-setup-frames", "60",
            "--a-prime-frames", "90", "--preset", "sideways"
        ]
        with patch.object(launch_golf.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(launch_golf.main(argv), 0)
            self.assertEqual(run.call_count, 2)
            canonical_intro = run.call_args_list[0].args[0]
            swing_child = run.call_args_list[1].args[0]
            self.assertIn("launch_hitting_green.py", canonical_intro[1])
            self.assertEqual(canonical_intro[canonical_intro.index("--profile")+1],
                             "green-pre-start")
            self.assertIn("--send-live", canonical_intro)
            self.assertIn("--attach-running", swing_child)
            self.assertEqual(swing_child[swing_child.index("--follow-through-frames")+1],
                             "45")
            self.assertEqual(swing_child[swing_child.index("--a-setup-frames")+1],
                             "60")
            self.assertEqual(swing_child[swing_child.index("--a-prime-frames")+1],
                             "90")
            self.assertIn("sideways", swing_child)

    def test_bad_followthrough_never_spawns_emulator(self):
        argv = [
            "--game", str(self.game), "--config", str(self.config),
            "--bridge", str(self.bridge), "--dolphin", str(self.exe),
            "--catalog", str(self.catalog), "--slot", "2", "--swing",
            "--follow-through-frames", "181"
        ]
        with patch.object(launch_golf.subprocess, "run") as run:
            with self.assertRaises(SystemExit):
                launch_golf.main(argv)
            run.assert_not_called()

    def test_bad_a_setup_never_spawns_emulator(self):
        argv = [
            "--game", str(self.game), "--config", str(self.config),
            "--bridge", str(self.bridge), "--dolphin", str(self.exe),
            "--catalog", str(self.catalog), "--slot", "2", "--swing",
            "--a-setup-frames", "0"
        ]
        with patch.object(launch_golf.subprocess, "run") as run:
            with self.assertRaises(SystemExit):
                launch_golf.main(argv)
            run.assert_not_called()

    def test_invalid_button_prime_never_starts_dolphin(self):
        argv = [
            "--game", str(self.game), "--config", str(self.config),
            "--bridge", str(self.bridge), "--dolphin", str(self.exe),
            "--catalog", str(self.catalog), "--slot", "2", "--swing",
            "--a-prime-frames", "181"
        ]
        with patch.object(launch_golf.subprocess, "run") as run:
            with self.assertRaises(SystemExit):
                launch_golf.main(argv)
            run.assert_not_called()

    def test_select_slot2_persists_named_profile_and_reuses_later(self):
        launch_golf.resolve_game(str(self.game), self.config)
        selected = launch_golf.resolve_profile(None, 2, self.config, self.catalog)
        self.assertEqual((selected.name, selected.slot), ("green-pre-start", 2))
        self.assertEqual(launch_golf.read_config(self.config)["profile"], "green-pre-start")
        reused = launch_golf.resolve_profile(None, None, self.config, self.catalog)
        self.assertEqual((reused.name, reused.slot), ("green-pre-start", 2))

    def test_game_reconfiguration_preserves_slot_preference(self):
        launch_golf.resolve_game(str(self.game), self.config)
        launch_golf.resolve_profile(None, 2, self.config, self.catalog)
        launch_golf.save_game(self.config, self.game)
        self.assertEqual(launch_golf.read_config(self.config)["profile"], "green-pre-start")

    def test_unregistered_slot_rejected_without_changing_existing_preference(self):
        launch_golf.resolve_game(str(self.game), self.config)
        launch_golf.resolve_profile(None, 2, self.config, self.catalog)
        with self.assertRaisesRegex(ValueError, "not registered"):
            launch_golf.resolve_profile(None, 9, self.config, self.catalog)
        self.assertEqual(launch_golf.read_config(self.config)["profile"], "green-pre-start")

    def test_explicit_profile_overrides_persisted_slot(self):
        launch_golf.resolve_game(str(self.game), self.config)
        launch_golf.resolve_profile(None, 2, self.config, self.catalog)
        selected = launch_golf.resolve_profile("green-first-shot", None, self.config, self.catalog)
        self.assertEqual(selected.slot, 1)
        self.assertEqual(launch_golf.read_config(self.config)["profile"], "green-first-shot")

    def test_main_slot_select_prints_and_passes_registered_profile(self):
        argv = [
            "--game", str(self.game), "--config", str(self.config),
            "--bridge", str(self.bridge), "--dolphin", str(self.exe),
            "--catalog", str(self.catalog), "--slot", "2"
        ]
        with patch.object(launch_golf.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(launch_golf.main(argv), 0)
            self.assertEqual(run.call_count, 1)
            cmd = run.call_args.args[0]
            self.assertEqual(cmd[cmd.index("--profile")+1], "green-pre-start")
            self.assertIn("launch_hitting_green.py", cmd[1])
            self.assertNotIn("--send-live-swing", cmd)

    def test_launch_updates_source_and_keeps_existing_mapping(self):
        argv = [
            "--game", str(self.game), "--config", str(self.config),
            "--bridge", str(self.bridge), "--dolphin", str(self.exe),
            "--catalog", str(self.catalog)
        ]
        with patch.object(launch_golf.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(launch_golf.main(argv), 0)
            run.assert_called_once()
        ini = self.ini.read_text()
        self.assertIn("Source = 1", ini)
        self.assertIn("Extension = None", ini)
        self.assertIn("Buttons/A = F", ini)
        backup = self.ini.with_name(self.ini.name + ".wii-ai-golf.original.bak")
        self.assertIn("Source = 2", backup.read_text())
        self.assertIn("Extension = Nunchuk", backup.read_text())

    def test_missing_controller_ini_fails_before_dolphin_spawn(self):
        self.ini.unlink()
        argv = [
            "--game", str(self.game), "--config", str(self.config),
            "--bridge", str(self.bridge), "--dolphin", str(self.exe),
            "--catalog", str(self.catalog)
        ]
        with patch.object(launch_golf.subprocess, "run") as run:
            self.assertEqual(launch_golf.main(argv), 1)
            run.assert_not_called()

    def test_existing_bridge_prevents_mutating_controller_ini(self):
        argv = [
            "--game", str(self.game), "--config", str(self.config),
            "--bridge", str(self.bridge), "--dolphin", str(self.exe),
            "--catalog", str(self.catalog)
        ]
        with patch.object(launch_golf, "is_bridge_port_open", return_value=True), patch.object(
            launch_golf.subprocess, "run"
        ) as run:
            self.assertEqual(launch_golf.main(argv), 1)
            run.assert_not_called()
        self.assertIn("Source = 2", self.ini.read_text())

    def test_explicit_dolphin_user_dir_remembered_for_future_runs(self):
        custom = self.root / "custom-user"
        ini = custom / "Config" / "WiimoteNew.ini"
        ini.parent.mkdir(parents=True)
        ini.write_text("[Wiimote1]\nSource = 2\nExtension = Nunchuk\n")
        argv = [
            "--game", str(self.game), "--config", str(self.config),
            "--bridge", str(self.bridge), "--dolphin", str(self.exe),
            "--catalog", str(self.catalog),
            "--dolphin-user", str(custom)
        ]
        with patch.object(launch_golf.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)):
            self.assertEqual(launch_golf.main(argv), 0)
        self.assertEqual(launch_golf.read_config(self.config)["dolphin_user"], str(custom))
        self.assertIn("Source = 1", ini.read_text())
        self.assertIn("Source = 2", self.ini.read_text())
        with patch.object(launch_golf.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)):
            self.assertEqual(launch_golf.main(argv[:-2]), 0)
        self.assertIn("Source = 2", self.ini.read_text())
        self.assertIn("Source = 1", ini.read_text())

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
