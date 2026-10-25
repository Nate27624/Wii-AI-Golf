"""CLI no longer exposes the retired desktop GUI."""
import unittest
from wii_ai_golf.cli import build_parser

class ScriptOnlyCLITests(unittest.TestCase):
    def test_lab_gui_not_advertised(self):
        parser = build_parser()
        with self.assertRaises(SystemExit) as error:
            parser.parse_args(["lab", "gui"])
        self.assertEqual(error.exception.code, 2)

    def test_script_lab_commands_preserved(self):
        parser = build_parser()
        for command in ("list", "sync", "history", "reports"):
            with self.subTest(command=command):
                parsed = parser.parse_args(["lab", command])
                self.assertEqual(parsed.lab_action, command)
