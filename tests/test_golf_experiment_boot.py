"""Mocked safety checks for the fresh-boot-first live experiment dispatcher."""
from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_golf_experiment as dispatcher


class FreshBootDispatchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.scripts = Path(temporary.name) / "scripts"
        self.scripts.mkdir()
        for name in ("launch_golf.py", "probe_swing.py", "discover_golf_motion.py"):
            (self.scripts / name).write_text("# fixture\n", encoding="utf-8")

    def plan(self, **kwargs):
        options = dict(action="probe_swing.py", action_args=["--preset", "forward",
                       "--send-live-swing"], game="G:/Wii Sports.wbfs",
                       dolphin=None, bridge=None, config=None, catalog=None,
                       dolphin_user=None, scripts_dir=self.scripts,
                       port=55355, profile="green-pre-start", python="py")
        options.update(kwargs)
        return dispatcher.build_commands(**options)

    def test_boot_precedes_action_and_invokes_canonical_launcher(self):
        boot, action = self.plan()
        self.assertEqual(boot[:2], ["py", str(self.scripts / "launch_golf.py")])
        self.assertEqual(boot[boot.index("--profile") + 1], "green-pre-start")
        self.assertEqual(boot[boot.index("--game") + 1], "G:/Wii Sports.wbfs")
        self.assertEqual(action[1], str(self.scripts / "probe_swing.py"))
        self.assertIn("--send-live-swing", action)
        self.assertIn("--attach-running", action)
        self.assertEqual(action.count("--attach-running"), 1)
        self.assertEqual(action[-2:], ["--port", "55355"])

    def test_future_capture_script_without_boot_code_is_accepted(self):
        boot, action = self.plan(action="discover_golf_motion.py",
                                 action_args=["--seconds", "30", "--profile", "fast"])
        self.assertEqual(action[1], str(self.scripts / "discover_golf_motion.py"))
        self.assertNotIn("--attach-running", action)
        self.assertEqual(boot[1], str(self.scripts / "launch_golf.py"))

    def test_no_arbitrary_paths_or_double_launch(self):
        for action in ("../probe_swing.py", "/tmp/probe_swing.py",
                       "scripts/../probe_swing.py", "launch_golf.py",
                       "launch_hitting_green.py", "savestate_session.py",
                       "start_golf_recording.py", "does_not_exist.py"):
            with self.subTest(action=action), self.assertRaises(ValueError):
                self.plan(action=action)

    def test_reject_second_savestate_reset(self):
        for forbidden in ("--reset-profile", "--reset-profile=green-first-shot",
                          "--attach-running", "--fresh", "--startup-slot=2"):
            with self.subTest(flag=forbidden), self.assertRaises(ValueError):
                self.plan(action_args=[forbidden])

    def test_wrong_profile_rejected_before_launch(self):
        with self.assertRaisesRegex(ValueError, "green-pre-start"):
            self.plan(profile="green-first-shot")

    def test_invalid_port_rejected_before_launch(self):
        for invalid in (0, -1, 65536, True):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.plan(port=invalid)

    def test_boot_failure_blocks_live_experiment(self):
        with patch.object(dispatcher.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 7)) as run:
            result = dispatcher.main(["--script", "probe_swing.py", "--send-live",
                                      "--", "--send-live-swing"])
            self.assertEqual(result, 7)
            run.assert_called_once()
            self.assertIn("launch_golf.py", run.call_args.args[0][1])

    def test_success_runs_boot_then_one_action(self):
        with patch.object(dispatcher.subprocess, "run",
                          side_effect=[subprocess.CompletedProcess([], 0),
                                       subprocess.CompletedProcess([], 0)]) as run:
            result = dispatcher.main(["--script", "probe_swing.py", "--send-live",
                                      "--", "--preset", "forward", "--send-live-swing"])
            self.assertEqual(result, 0)
            self.assertEqual(run.call_count, 2)
            self.assertIn("launch_golf.py", run.call_args_list[0].args[0][1])
            self.assertIn("probe_swing.py", run.call_args_list[1].args[0][1])
            self.assertIn("--attach-running", run.call_args_list[1].args[0])
            self.assertNotIn("--attach-running", run.call_args_list[0].args[0])

    def test_attach_is_internal_only_even_when_user_passes_it(self):
        with self.assertRaisesRegex(ValueError, "must not launch/reset"):
            self.plan(action_args=["--attach-running", "--send-live-swing"])
        _, action = self.plan(action_args=["--preset", "forward", "--send-live-swing"])
        self.assertEqual(action.count("--attach-running"), 1)
        self.assertEqual(action[2], "--attach-running")

    def test_dry_run_never_launches_or_sends_controller_input(self):
        with patch.object(dispatcher.subprocess, "run") as run:
            result = dispatcher.main(["--script", "probe_swing.py",
                                      "--", "--send-live-swing"])
            self.assertEqual(result, 0)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
