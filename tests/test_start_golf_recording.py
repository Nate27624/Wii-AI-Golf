"""All live evaluators must use Worker 1's ONE canonical intro sequence."""
import argparse
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
import session_bootstrap as boot


class SharedStartupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for d in ("scripts", "research", "src"):
            (self.root / d).mkdir()
        (self.root / "scripts" / "launch_hitting_green.py").write_text("# canonical launcher")
        self.catalog = self.root / "research" / "savestates.local.json"
        self.catalog.write_text(json.dumps({
            "schema_version": 1,
            "profiles": [{"name": "green-pre-start", "slot": 2,
                          "description": "known pre-menu checkpoint", "game_id": "RSPE01"}],
        }))
        self.exe = self.root / "Dolphin.exe"
        self.bridge = self.root / "mcp_bridge_swing.py"
        self.game = self.root / "WiiSports.wbfs"
        for file in (self.exe, self.bridge, self.game):
            file.touch()
        # Hardware settings come from canonical integration code; unit tests
        # must never mutate a real Dolphin user config.
        self.controller_guard = patch.object(
            boot, "prepare_emulated_remote",
            return_value={"source": "Emulated Wii Remote (1)", "extension": "None"},
        )
        self.prepare_remote = self.controller_guard.start()
        self.addCleanup(self.controller_guard.stop)

    def args(self, startup="auto", game=None):
        parser = argparse.ArgumentParser()
        boot.add_boot_options(parser)
        parser.add_argument("--port", type=int, default=55355)
        argv = ["--canonical", str(self.root), "--startup", startup,
                "--dolphin", str(self.exe), "--bridge", str(self.bridge)]
        if game is not None:
            argv.extend(["--game", str(game)])
        return parser.parse_args(argv)

    def test_physical_mode_preserves_controller_and_does_not_inject_buttons(self):
        args = self.args()
        args.controller_mode = "physical"
        with patch.object(boot, "bridge_open", return_value=True), patch.object(
            boot, "prepare_emulated_remote"
        ) as emulated, patch.object(boot.subprocess, "run") as launch:
            self.assertEqual(boot.ensure_intro(args), "physical_existing")
            emulated.assert_not_called()
            launch.assert_not_called()

    def test_physical_mode_missing_bridge_fails_without_changing_settings(self):
        args = self.args()
        args.controller_mode = "physical"
        with patch.object(boot, "bridge_open", return_value=False), patch.object(
            boot, "prepare_emulated_remote"
        ) as emulated, patch.object(boot.subprocess, "run") as launch:
            with self.assertRaisesRegex(ConnectionError, "Physical mode"):
                boot.ensure_intro(args)
            emulated.assert_not_called()
            launch.assert_not_called()

    def test_canonical_menu_only_one_load_no_second_swing(self):
        cmd = boot.boot_command(canonical=self.root, profile="green-pre-start",
                                port=55355, attach=True)
        self.assertEqual(Path(cmd[1]).name, "launch_hitting_green.py")
        self.assertIn("--send-live", cmd)
        self.assertIn("--attach-running", cmd)
        self.assertNotIn("--swing", cmd)
        self.assertNotIn("--startup-slot", cmd)
        self.assertEqual(cmd[cmd.index("--profile")+1], "green-pre-start")
        self.assertEqual(cmd[cmd.index("--catalog")+1], str(self.catalog))

    def test_fresh_mode_passes_all_required_files(self):
        cmd = boot.boot_command(canonical=self.root, profile="green-pre-start",
                                port=55355, attach=False, dolphin=self.exe,
                                bridge=self.bridge, game=self.game)
        for flag, path in (("--dolphin", self.exe), ("--bridge", self.bridge),
                           ("--game", self.game)):
            self.assertEqual(cmd[cmd.index(flag)+1], str(path))
        self.assertNotIn("--attach-running", cmd)
        self.assertNotIn("--swing", cmd)

    def test_no_bridge_automatically_launches_fresh(self):
        args = self.args(game=self.game)
        with patch.object(boot, "bridge_open", return_value=False), patch.object(
            boot, "dolphin_process_running", return_value=False
        ), patch.object(boot.subprocess, "run",
                         return_value=subprocess.CompletedProcess([], 0)) as run:
            result = boot.ensure_intro(args)
        self.assertEqual(result, "launched")
        run.assert_called_once()
        cmd = run.call_args.args[0]
        self.assertIn("launch_hitting_green.py", cmd[1])
        self.assertIn("--game", cmd)
        self.assertIn("--send-live", cmd)
        self.assertNotIn("--attach-running", cmd)
        self.assertEqual(run.call_args.kwargs["env"]["PYTHONPATH"], str(self.root / "src"))

    def test_fresh_always_configures_emulated_wiimote_before_launch(self):
        with patch.object(boot, "bridge_open", return_value=False), patch.object(
            boot, "dolphin_process_running", return_value=False
        ), patch.object(boot.subprocess, "run",
                         return_value=subprocess.CompletedProcess([], 0)):
            boot.ensure_intro(self.args(game=self.game))
        self.prepare_remote.assert_called_once_with(self.root, self.exe)

    def test_bridge_existing_auto_uses_same_prestart_intro(self):
        with patch.object(boot, "bridge_open", return_value=True), patch.object(
            boot.subprocess, "run",
            return_value=subprocess.CompletedProcess([], 0)) as run:
            result = boot.ensure_intro(self.args())
        self.assertEqual(result, "attached")
        cmd = run.call_args.args[0]
        self.assertIn("--attach-running", cmd)
        self.assertNotIn("--dolphin", cmd)
        self.assertNotIn("--swing", cmd)

    def test_local_game_config_resolves_game_without_arg(self):
        config = self.root / "research" / "launch.local.json"
        config.write_text(json.dumps({"schema_version": 1, "game": str(self.game)}))
        with patch.object(boot, "bridge_open", return_value=False), patch.object(
            boot, "dolphin_process_running", return_value=False
        ), patch.object(boot.subprocess, "run",
                         return_value=subprocess.CompletedProcess([], 0)) as run:
            boot.ensure_intro(self.args())
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[cmd.index("--game") + 1], str(self.game))

    def test_missing_game_never_launches_second_dolphin(self):
        with patch.object(boot, "bridge_open", return_value=False), patch.object(
            boot, "dolphin_process_running", return_value=False
        ), patch.object(boot.subprocess, "run") as run:
            with self.assertRaisesRegex(FileNotFoundError, "Wii Sports game image missing"):
                boot.ensure_intro(self.args())
            run.assert_not_called()

    def test_dolphin_process_without_bridge_rejected(self):
        with patch.object(boot, "bridge_open", return_value=False), patch.object(
            boot, "dolphin_process_running", return_value=True
        ), patch.object(boot.subprocess, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "already running"):
                boot.ensure_intro(self.args(game=self.game))
            run.assert_not_called()

    def test_forced_mode_mismatch_never_loads_state(self):
        with patch.object(boot, "bridge_open", return_value=False), patch.object(
            boot.subprocess, "run") as run:
            with self.assertRaises(ConnectionError):
                boot.ensure_intro(self.args(startup="attach"))
            run.assert_not_called()
        with patch.object(boot, "bridge_open", return_value=True), patch.object(
            boot.subprocess, "run") as run:
            with self.assertRaises(RuntimeError):
                boot.ensure_intro(self.args(startup="fresh", game=self.game))
            run.assert_not_called()

    def test_skip_is_explicit_and_has_no_game_side_effects(self):
        with patch.object(boot, "bridge_open") as live, patch.object(
            boot.subprocess, "run") as run:
            self.assertEqual(boot.ensure_intro(self.args(startup="skip")), "skipped")
            live.assert_not_called()
            run.assert_not_called()

    def test_missing_registered_profile_fails_closed(self):
        args = self.args(game=self.game)
        args.prestart_profile = "not-registered"
        with patch.object(boot.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "unknown savestate"):
                boot.ensure_intro(args)
            run.assert_not_called()

    def test_canonical_boot_error_stops_recording(self):
        with patch.object(boot, "bridge_open", return_value=True), patch.object(
            boot.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)
        ):
            with self.assertRaisesRegex(RuntimeError, "Canonical intro launcher failed"):
                boot.ensure_intro(self.args())

    def test_wrapper_invokes_boot_once_and_child_explicitly_skips(self):
        args = ["--canonical", str(self.root), "--startup", "auto",
                "--seconds", "12", "--no-upload"]
        calls = []
        def run(*a, **kw):
            calls.append((a, kw))
            return subprocess.CompletedProcess(a[0], 0)
        with patch.object(start, "ensure_intro", return_value="launched") as intro, patch.object(
            start.subprocess, "run", side_effect=run
        ):
            self.assertEqual(start.main(args), 0)
        intro.assert_called_once()
        self.assertEqual(len(calls), 1)
        command = calls[0][0][0]
        self.assertIn("discover_golf_motion.py", command[1])
        self.assertEqual(command[command.index("--startup")+1], "skip")
        self.assertIn("--no-upload", command)

    def test_legacy_attach_running_argument_still_auto_launches(self):
        """The exact user's previous command no longer requires a live bridge."""
        with patch.object(start, "ensure_intro", return_value="launched") as intro, patch.object(
            start.subprocess, "run",
            return_value=subprocess.CompletedProcess([], 0)
        ):
            result = start.main(["--canonical", str(self.root),
                                 "--attach-running", "--seconds", "30",
                                 "--scan-profile", "fast"])
        self.assertEqual(result, 0)
        self.assertEqual(intro.call_args.args[0].startup, "auto")

    def test_all_live_entrypoints_share_bootstrap(self):
        paths = [
            "discover_golf_motion.py", "monitor_hitting_green.py",
            "collect_hitting_green.py", "probe_golf_spatial.py",
            "probe_golf_symbols.py", "capture_golf_data.py",
        ]
        root = SCRIPT.parent
        for path in paths:
            text = (root / path).read_text()
            with self.subTest(script=path):
                self.assertIn("add_boot_options", text)
                self.assertIn("ensure_intro(args)", text)
                self.assertNotIn("execute_menu_phases(", text)


if __name__ == "__main__":
    unittest.main()
