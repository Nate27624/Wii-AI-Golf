"""Offline zero-emulator regression checks for the attached A45 recovery path."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / "scripts" / "recheck_ready_ball_v1_a45.py"
spec = importlib.util.spec_from_file_location("ready_ball_recheck", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class Recheck(unittest.TestCase):
    def test_exact_a45_attached_collector_flags(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "scripts").mkdir()
            (root / "scripts" / "collect_outcome_transition.py").touch()
            cmd = mod.build_collector_command(python="python", root=root)
            self.assertEqual(cmd, ["python", str(root / "scripts" / "collect_outcome_transition.py"),
                                   "--send-live-swing", "--a-prime-requests", "0", "--a-lead-frames", "45",
                                   "--observe-start-pose", "--ask-power", "--port", "55355"])
            self.assertNotIn("launch_golf.py", " ".join(cmd))
            self.assertNotIn("--profile", cmd)
            self.assertNotIn("--reset-profile", cmd)

    def test_missing_collector_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError, "collector missing"):
                mod.build_collector_command(root=Path(t))

    def test_no_live_opt_in_never_calls_running_bridge_or_subprocess(self):
        with patch.object(mod, "build_collector_command", return_value=["python", "collect_outcome_transition.py", "--a-lead-frames", "45"]), patch.object(mod, "check_local_v1_source"), patch.object(mod, "ensure_running_bridge") as preflight, patch.object(mod.subprocess, "run") as run:
            self.assertEqual(mod.main([]), 0)
            preflight.assert_not_called()
            run.assert_not_called()

    def test_live_refuses_when_frame_progress_fails(self):
        with patch.object(mod, "build_collector_command", return_value=["python", "collect_outcome_transition.py", "--a-lead-frames", "45"]), patch.object(mod, "check_local_v1_source"), patch.object(mod, "ensure_running_bridge", side_effect=RuntimeError("paused")), patch.object(mod.subprocess, "run") as run:
            self.assertEqual(mod.main(["--send-live-swing"]), 1)
            run.assert_not_called()

    def test_live_invokes_existing_attached_collector_once(self):
        with patch.object(mod, "build_collector_command", return_value=["python", "collect_outcome_transition.py", "--a-lead-frames", "45"]), patch.object(mod, "check_local_v1_source"), patch.object(mod, "ensure_running_bridge"), patch.object(mod.subprocess, "run") as run:
            run.return_value.returncode = 0
            self.assertEqual(mod.main(["--send-live-swing"]), 0)
            self.assertEqual(run.call_count, 1)
            argv = run.call_args.args[0]
            self.assertIn("collect_outcome_transition.py", argv[1])
            self.assertEqual(argv[argv.index("--a-lead-frames") + 1], "45")

    def test_live_forwards_error_status(self):
        with patch.object(mod, "build_collector_command", return_value=["python", "collect_outcome_transition.py", "--a-lead-frames", "45"]), patch.object(mod, "check_local_v1_source"), patch.object(mod, "ensure_running_bridge"), patch.object(mod.subprocess, "run") as run:
            run.return_value.returncode = 2
            self.assertEqual(mod.main(["--send-live-swing"]), 2)

    def test_bad_port_rejected(self):
        with self.assertRaises(SystemExit):
            mod.main(["--port", "0"])


if __name__ == "__main__":
    unittest.main()
