"""Regression: failed interactive Lab commands remain readable; no extra boot."""
from __future__ import annotations
import sys
from pathlib import Path
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lab_interactive_console import main


class LabInteractiveConsoleTests(unittest.TestCase):
    def test_reviewed_lab_command_preserves_exact_arguments(self):
        cmd = [sys.executable, str(ROOT / "scripts" / "golf.py"),
               "lab", "run", "integration.v1-diagnostic",
               "--a-lead", "45", "--live"]
        with patch("lab_interactive_console.subprocess.run") as runner:
            runner.return_value.returncode = 0
            self.assertEqual(main(["--", *cmd]), 0)
            runner.assert_called_once()
            self.assertEqual(runner.call_args.args[0], cmd)

    def test_exit_two_stays_visible_until_operator_acknowledges(self):
        cmd = [sys.executable, str(ROOT / "scripts" / "golf.py"),
               "lab", "run", "integration.v1-diagnostic", "--live"]
        with patch("lab_interactive_console.subprocess.run") as runner, \
             patch("builtins.input", return_value="") as acknowledge:
            runner.return_value.returncode = 2
            self.assertEqual(main(["--", *cmd]), 2)
            acknowledge.assert_called_once()

    def test_arbitrary_commands_do_not_execute(self):
        with patch("lab_interactive_console.subprocess.run") as runner:
            self.assertEqual(main(["--", sys.executable, "-c", "print(1)"]), 2)
            runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
