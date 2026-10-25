"""The same post-boot contract is used by the dispatcher and S001 launcher."""
import unittest
from wii_ai_golf.integration.post_boot import post_boot_action_args


class PostBootTests(unittest.TestCase):
    def test_s001_probe_attaches_exactly_once(self):
        self.assertEqual(
            post_boot_action_args("probe_swing.py", ["--preset", "forward"]),
            ["--attach-running", "--preset", "forward"])

    def test_s002_capture_does_not_receive_unknown_attach_flag(self):
        self.assertEqual(
            post_boot_action_args("collect_outcome_transition.py", ["--send-live-swing"]),
            ["--send-live-swing"])

    def test_manual_attach_is_disallowed(self):
        for value in ("--attach-running", "--attach-running=yes"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    post_boot_action_args("probe_swing.py", [value])

    def test_bad_argument_types_rejected(self):
        with self.assertRaises(ValueError):
            post_boot_action_args("probe_swing.py", ["--port", 55355])
