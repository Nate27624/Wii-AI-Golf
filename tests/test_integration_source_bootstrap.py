"""Regression: all integrator CLIs must run from a clean/stale Python install.

The previous release passed Git and source checks yet failed at import-time on
the user's Windows host because a pip editable install pointed to another Git
worktree. This is an end-to-end subprocess smoke, not a mocked import test.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    "launch_golf.py",
    "launch_hitting_green.py",
    "savestate_session.py",
    "probe_swing.py",
    "patch_felk_bridge.py",
    "probe_dolphin_bridge.py",
    "probe_atomic_trace.py",
    "probe_wiimote.py",
    "plan_scenarios.py",
)


class SourceBootstrapTests(unittest.TestCase):
    def test_every_integrator_command_works_with_shadowing_stale_install(self):
        with tempfile.TemporaryDirectory() as d:
            hostile = Path(d)
            fake = hostile / "wii_ai_golf"
            fake.mkdir()
            (fake / "__init__.py").write_text("# unrelated older package\n", encoding="utf-8")
            # If the script omits the local src bootstrap, imports MUST fail
            # against this fake package (no integration subpackage).
            env = dict(os.environ)
            env["PYTHONPATH"] = str(hostile)
            for script in SCRIPTS:
                with self.subTest(script=script):
                    path = ROOT / "scripts" / script
                    self.assertTrue(path.is_file())
                    out = subprocess.run(
                        [sys.executable, str(path), "--help"],
                        cwd=hostile,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=20,
                    )
                    self.assertEqual(
                        out.returncode, 0,
                        f"{script} failed from another CWD + stale package:\n"
                        f"stdout={out.stdout}\nstderr={out.stderr}"
                    )
                    self.assertIn("usage:", out.stdout.lower())

    def test_isolated_interpreter_does_not_need_editable_install(self):
        # -I drops PYTHONPATH and current directory while retaining Python stdlib.
        # Local-src bootstrap must still supply the project's wii_ai_golf code.
        with tempfile.TemporaryDirectory() as d:
            for script in ("launch_golf.py", "launch_hitting_green.py", "probe_swing.py", "savestate_session.py"):
                with self.subTest(script=script):
                    out = subprocess.run(
                        [sys.executable, "-I", str(ROOT / "scripts" / script), "--help"],
                        cwd=d,
                        capture_output=True, text=True, timeout=20,
                    )
                    self.assertEqual(out.returncode, 0, out.stderr)
                    self.assertIn("usage:", out.stdout.lower())


if __name__ == "__main__":
    unittest.main()
