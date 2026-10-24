"""S001: a swing CLI always launches the verified intro unless explicitly attaching.

Regression for user's WinError 10061 from bare probe_swing.py: without a
live bridge, default CLI MUST delegate to the canonical full launcher,
not attempt FelkRPC before Dolphin has been started.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "src")):
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)

from scripts import probe_swing


class SwingStartupContractTests(unittest.TestCase):
    def _run(self, *flags):
        with patch.object(sys, "argv", ["probe_swing.py", *flags]), \
             patch.object(probe_swing.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 0)) as spawn, \
             patch.object(probe_swing, "FelkRPC") as rpc:
            probe_swing.main()
            return spawn.call_args_list, rpc.call_count

    def test_bare_live_swing_delegates_to_full_canonical_launcher(self):
        calls, rpc_count = self._run(
            "--preset", "forward", "--follow-through-frames", "30",
            "--send-live-swing",
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(rpc_count, 0, "never connect to a missing bare bridge")
        cmd = calls[0].args[0]
        self.assertEqual(Path(cmd[1]).name, "launch_golf.py")
        self.assertIn("--swing", cmd)
        self.assertIn("--preset", cmd)
        self.assertIn("forward", cmd)
        self.assertIn("--follow-through-frames", cmd)
        self.assertEqual(cmd[cmd.index("--follow-through-frames")+1], "30")
        self.assertNotIn("--attach-running", cmd)
        self.assertIn("--catalog", cmd)

    def test_slot2_option_kept_with_full_start(self):
        calls, rpc_count = self._run(
            "--slot", "2", "--preset", "reverse",
            "--follow-through-frames", "45", "--send-live-swing"
        )
        cmd = calls[0].args[0]
        self.assertEqual(cmd[cmd.index("--slot")+1], "2")
        self.assertEqual(cmd[cmd.index("--follow-through-frames")+1], "45")
        self.assertEqual(rpc_count, 0)

    def test_full_launch_rejects_reset_profile_without_attach(self):
        with patch.object(sys, "argv", [
            "probe_swing.py", "--send-live-swing", "--reset-profile", "green-first-shot"
        ]), patch.object(probe_swing.subprocess, "run") as spawn, \
             patch.object(probe_swing, "FelkRPC") as rpc:
            with self.assertRaises(SystemExit):
                probe_swing.main()
            spawn.assert_not_called()
            rpc.assert_not_called()

    def test_attach_running_never_recurses_into_new_dolphin(self):
        with patch.object(sys, "argv", [
            "probe_swing.py", "--attach-running", "--slot", "2", "--send-live-swing"
        ]), patch.object(probe_swing.subprocess, "run") as spawn, \
             patch.object(probe_swing, "FelkRPC") as rpc:
            with self.assertRaises(SystemExit):
                probe_swing.main()
            spawn.assert_not_called()
            rpc.assert_not_called()

    def test_dry_run_never_starts_game_or_uses_bridge(self):
        with patch.object(sys, "argv", ["probe_swing.py"]), \
             patch.object(probe_swing.subprocess, "run") as spawn, \
             patch.object(probe_swing, "FelkRPC") as rpc:
            probe_swing.main()
            spawn.assert_not_called()
            rpc.assert_not_called()

    def test_delegate_child_failure_returns_nonzero(self):
        with patch.object(sys, "argv", ["probe_swing.py", "--send-live-swing"]), \
             patch.object(probe_swing.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 3)), \
             patch.object(probe_swing, "FelkRPC") as rpc:
            with self.assertRaises(SystemExit) as raised:
                probe_swing.main()
            self.assertEqual(raised.exception.code, 3)
            rpc.assert_not_called()


if __name__ == "__main__":
    unittest.main()
