from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import savestate_session as session
from wii_ai_golf.integration.savestates import StateProfile


class MockPopen:
    def __init__(self, args, cwd):
        self.args = args
        self.cwd = cwd
        self.pid = 1234
        self.returncode = None
    def poll(self):
        return None


class FakeRPC:
    def __init__(self, *args, **kwargs):
        self.calls = []
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def call(self, method, params=None):
        self.calls.append((method, params))
        if method == "bridge.ping":
            return {"bridge_version": "0.3.0"}
        return None


class SessionLaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name).resolve()
        self.exe = base / "Dolphin.exe"
        self.bridge = base / "bridge.py"
        self.game = base / "game.rvz"
        for x in (self.exe, self.bridge, self.game):
            x.write_bytes(b"fake")
        self.args = SimpleNamespace(dolphin=str(self.exe), bridge=str(self.bridge),
                                    game=str(self.game), port=55355, timeout=10.0)
        self.profile = StateProfile("green-first-shot", 20)

    def test_start_sends_script_exec_and_reset(self):
        with patch.object(session, "_connected", return_value=False), \
             patch.object(session.subprocess, "Popen", side_effect=MockPopen) as popen, \
             patch.object(session, "FelkRPC", FakeRPC):
            result = session._launch(self.args, self.profile)
        self.assertEqual(result["state_load"]["slot"], 20)
        self.assertEqual(result["action"], "launched_and_load_requested")
        self.assertEqual(result["pid"], 1234)
        self.assertEqual(popen.call_args.args[0],
                         [str(self.exe), "--script", str(self.bridge), "--exec", str(self.game)])

    def test_start_refuses_existing_listener(self):
        with patch.object(session, "_connected", return_value=True), \
             patch.object(session.subprocess, "Popen") as popen:
            with self.assertRaisesRegex(RuntimeError, "already open"):
                session._launch(self.args, self.profile)
        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
