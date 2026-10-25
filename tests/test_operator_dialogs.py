"""Offline tests for opt-in operator dialogs without a display."""
import os
import unittest
from unittest.mock import patch
from wii_ai_golf.operator_dialogs import operator_input


class OperatorDialogTests(unittest.TestCase):
    def test_console_default(self):
        with patch.dict(os.environ, {}, clear=True), patch("builtins.input", return_value="") as mocked:
            self.assertEqual(operator_input("Ready?"), "")
            mocked.assert_called_once_with("Ready?")

    def test_dialog_cancel_fails_closed(self):
        class FakeTk:
            def withdraw(self): pass
            def destroy(self): pass
        from types import ModuleType
        import sys
        fake = ModuleType("tkinter")
        fake.Tk = FakeTk
        fake.simpledialog = ModuleType("simpledialog")
        fake.simpledialog.askstring = lambda *a, **k: None
        with patch.dict(os.environ, {"WII_GOLF_DIALOGS": "1"}), patch.dict(sys.modules, {"tkinter": fake, "tkinter.simpledialog": fake.simpledialog}):
            self.assertEqual(operator_input("Ready?"), "q")

    def test_dialog_failure_does_not_approve(self):
        class FakeTk:
            def __init__(self): raise RuntimeError("no display")
        from types import ModuleType
        import sys
        fake = ModuleType("tkinter")
        fake.Tk = FakeTk
        fake.simpledialog = ModuleType("simpledialog")
        with patch.dict(os.environ, {"WII_GOLF_DIALOGS": "1"}), patch.dict(sys.modules, {"tkinter": fake, "tkinter.simpledialog": fake.simpledialog}):
            with self.assertRaisesRegex(RuntimeError, "canceled"):
                operator_input("Ready?")


if __name__ == "__main__":
    unittest.main()
