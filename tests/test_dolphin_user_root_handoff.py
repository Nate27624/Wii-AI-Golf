"""Offline S001 regression: configured Wii Remote INI and child Dolphin share User root.

Mocks all processes and connections. This file does not run Dolphin, any game,
a bridge, or a private capture; a native startup crash is not diagnosed here.
"""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import launch_golf
import launch_hitting_green
import savestate_session


class DolphinUserRootHandoffTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.dolphin = self._file("native/Dolphin.exe")
        self.bridge = self._file("bridge.py")
        self.game = self._file("game.rvz")
        self.catalog = self._file("catalog.json")
        self.user_root = self.base / "custom User"
        self._file("custom User/Config/WiimoteNew.ini")

    def _file(self, name):
        path = self.base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"placeholder")
        return path

    def _args(self, user_root):
        return SimpleNamespace(
            dolphin=self.dolphin, bridge=self.bridge, game=self.game,
            dolphin_user=user_root, port=55355, timeout=2.0,
        )

    def _assert_early_exit(self, args):
        fake = SimpleNamespace(poll=lambda: 0, returncode=0)
        with patch.object(savestate_session, "_connected", return_value=False), \\
             patch.object(savestate_session.subprocess, "Popen", return_value=fake) as popen:
            with self.assertRaisesRegex(RuntimeError, "before bridge preflight"):
                savestate_session._launch(args, object())
        return popen.call_args

    def test_start_command_transmits_existing_explicit_root(self):
        cmd = launch_golf.make_start_command(
            game=self.game, dolphin=self.dolphin, bridge=self.bridge,
            profile="green-pre-start", catalog=self.catalog, port=55355,
            dolphin_user=self.user_root,
        )
        self.assertEqual(cmd[-2:], ["--dolphin-user", str(self.user_root.resolve())])
        self.assertIn("--send-live", cmd)

    def test_start_command_default_stays_compatible(self):
        cmd = launch_golf.make_start_command(
            game=self.game, dolphin=self.dolphin, bridge=self.bridge,
            profile="green-pre-start", catalog=self.catalog, port=55355,
        )
        self.assertNotIn("--dolphin-user", cmd)
        self.assertEqual(cmd[-1], "--send-live")

    def test_native_launch_explicit_user_root_is_before_script(self):
        call = self._assert_early_exit(self._args(self.user_root))
        argv = call.args[0]
        self.assertEqual(argv, [
            str(self.dolphin.resolve()), "--user", str(self.user_root.resolve()),
            "--script", str(self.bridge.resolve()), "--exec", str(self.game.resolve()),
        ])
        self.assertEqual(call.kwargs["cwd"], str(self.dolphin.parent.resolve()))

    def test_native_launch_without_override_keeps_old_argv(self):
        call = self._assert_early_exit(self._args(None))
        self.assertEqual(call.args[0], [
            str(self.dolphin.resolve()),
            "--script", str(self.bridge.resolve()), "--exec", str(self.game.resolve()),
        ])

    def test_nonexistent_user_root_refuses_before_spawning(self):
        with patch.object(savestate_session, "_connected", return_value=False), \\
             patch.object(savestate_session.subprocess, "Popen") as popen:
            with self.assertRaisesRegex(ValueError, "existing Config/WiimoteNew.ini"):
                savestate_session._launch(self._args(self.base / "absent"), object())
            popen.assert_not_called()

    def test_user_root_without_controller_ini_refuses_before_spawning(self):
        other = self.base / "unprepared"
        other.mkdir()
        with patch.object(savestate_session, "_connected", return_value=False), \\
             patch.object(savestate_session.subprocess, "Popen") as popen:
            with self.assertRaisesRegex(ValueError, "existing Config/WiimoteNew.ini"):
                savestate_session._launch(self._args(other), object())
            popen.assert_not_called()

    def test_attach_running_cannot_override_user_root(self):
        argv = ["launch_hitting_green.py", "--attach-running",
                "--dolphin-user", str(self.user_root)]
        with patch.object(sys, "argv", argv), \\
             patch.object(launch_hitting_green, "StateCatalog") as catalog, \\
             redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as exc:
                launch_hitting_green.main()
        self.assertEqual(exc.exception.code, 2)
        catalog.assert_not_called()

    def test_canonical_main_pins_prepared_user_root_in_child_command(self):
        profile = SimpleNamespace(name="green-pre-start", slot=2, description="")
        controller = {
            "user_dir": str(self.user_root), "source": "Emulated Wii Remote (1)",
            "extension": "None", "ini": str(self.user_root / "Config" / "WiimoteNew.ini"),
            "changed": False, "backup": None,
        }
        argv = ["--catalog", str(self.catalog), "--dolphin", str(self.dolphin),
                "--bridge", str(self.bridge)]
        with patch.object(launch_golf, "resolve_game", return_value=self.game), \\
             patch.object(launch_golf, "resolve_profile", return_value=profile), \\
             patch.object(launch_golf, "read_config", return_value={"game": str(self.game)}), \\
             patch.object(launch_golf, "is_bridge_port_open", return_value=False), \\
             patch.object(launch_golf, "ensure_emulated_controller", return_value=controller), \\
             patch.object(launch_golf.subprocess, "run",
                          return_value=SimpleNamespace(returncode=0)) as run, \\
             redirect_stdout(io.StringIO()):
            code = launch_golf.main(argv)
        self.assertEqual(code, 0)
        command = run.call_args.args[0]
        self.assertEqual(command[-2:], ["--dolphin-user", str(self.user_root.resolve())])


if __name__ == "__main__":
    unittest.main()
