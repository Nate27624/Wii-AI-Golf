"""Ensure the reviewed watched-swing recorder gets exactly one post-boot handoff."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.integration.post_boot import post_boot_action_args


class WatchedSwingBootHandoffTests(unittest.TestCase):
    def test_recorder_injected_attach_exactly_once(self):
        self.assertEqual(
            post_boot_action_args(
                "record_selected_ball_swing_private.py",
                ["--send-live-swing", "--a-prime-frames", "45"]),
            ["--attach-running", "--send-live-swing", "--a-prime-frames", "45"])

    def test_regular_swing_probe_unchanged(self):
        self.assertEqual(post_boot_action_args("probe_swing.py", []),
                         ["--attach-running"])

    def test_unrecognized_action_has_no_attach(self):
        self.assertEqual(post_boot_action_args("collect_outcome_transition.py", ["x"]),
                         ["x"])

    def test_direct_user_supplied_attach_is_denied(self):
        with self.assertRaises(ValueError):
            post_boot_action_args("record_selected_ball_swing_private.py",
                                  ["--attach-running", "--send-live-swing"])

    def test_bad_argument_type_denied(self):
        with self.assertRaises(ValueError):
            post_boot_action_args("record_selected_ball_swing_private.py", None)


if __name__ == "__main__":
    unittest.main()
