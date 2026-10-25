"""One canonical Python package supports both approved GUI and Git Bash workflows."""
import unittest
from wii_ai_golf.cli import build_parser


class LabEntrypointTests(unittest.TestCase):
    def test_user_requested_gui_entrypoint_remains_available(self):
        parsed = build_parser().parse_args(["lab", "gui"])
        self.assertEqual(parsed.group, "lab")
        self.assertEqual(parsed.lab_action, "gui")

    def test_script_lab_commands_preserved_for_git_bash(self):
        parser = build_parser()
        for command in ("list", "sync", "history", "reports"):
            with self.subTest(command=command):
                parsed = parser.parse_args(["lab", command])
                self.assertEqual(parsed.lab_action, command)


if __name__ == "__main__":
    unittest.main()
