"""Static safety contract for Lab popup opt-in.

Live GUI subprocesses inherit modal dialogs; offline execution and normal CLI
must not accidentally inherit the GUI-only setting.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LabDialogWiringTests(unittest.TestCase):
    def test_live_dialog_opt_in_only(self):
        source = (ROOT / "src/wii_ai_golf/lab/gui.py").read_text(encoding="utf-8")
        self.assertIn('child_env["WII_GOLF_DIALOGS"] = "1"', source)
        self.assertIn('child_env.pop("WII_GOLF_DIALOGS", None)', source)
        self.assertIn('observed_command, cwd=root, env=child_env,', source)


if __name__ == "__main__":
    unittest.main()
