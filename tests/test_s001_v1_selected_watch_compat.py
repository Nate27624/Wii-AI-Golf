"""Synthetic-only V1 watcher compatibility checks; never touch real Dolphin."""
from __future__ import annotations

import ast
import hashlib
import unittest

from wii_ai_golf.integration.atomic_patch import BOOT_MARKER, PATCH_MARKER
from wii_ai_golf.integration.swing_patch import SWING_MARKER, SWING_NEUTRAL_V2_MARKER
from wii_ai_golf.integration.ball_watch_patch import BALL_WATCH_MARKER
from wii_ai_golf.integration.v1_ball_watch_compat import (
    extend_known_v1_with_selected_watch, V1BallWatchCompatibilityError,
)


def fixture():
    return (
        PATCH_MARKER + "\n" + SWING_MARKER + "\n"
        + "def _wii_ai_submit_swing(p):\n    return p\n"
        + "def _wii_ai_tick():\n    return 'v1-motion-unchanged'\n"
        + "def _poll_sockets():\n    return None\n"
        + "HANDLERS = {\n"
        + '    "trace.submit_swing": _wii_ai_submit_swing,\n'
        + "}\n"
        + "while True:\n"
        + "    await event.frameadvance()\n"
        + "    _frame_count += 1\n"
        + "    _wii_ai_tick()\n"
        + "    # Inline comment or extra step does not change controller order.\n"
        + "    _poll_sockets()\n"
    )


def adapt(s: str):
    return extend_known_v1_with_selected_watch(
        s, expected_sha256=hashlib.sha256(s.encode("utf-8")).hexdigest()
    )


class V1WatchCompatTests(unittest.TestCase):
    def test_synthetic_source_preserved_and_compiles(self):
        original = fixture()
        target = adapt(original)
        self.assertIn(BALL_WATCH_MARKER, target)
        self.assertEqual(target.count(BALL_WATCH_MARKER), 1)
        self.assertIn("_wii_ball_watch_tick()\n    _wii_ai_tick()", target)
        self.assertEqual(target.count("    _wii_ai_tick()"), 1)
        self.assertIn('"golf.ball_watch.v1_provenance":', target)
        self.assertNotIn(SWING_NEUTRAL_V2_MARKER, target)
        compile(target, "<synthetic-watched-V1>", "exec",
                flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)

    def test_live_v1_code_is_not_mutated(self):
        original = fixture()
        watched = adapt(original)
        self.assertIn("return 'v1-motion-unchanged'", watched)
        self.assertIn('"trace.submit_swing": _wii_ai_submit_swing', watched)
        self.assertIn("_wii_ai_submit_swing(p):\n    return p", watched)
        self.assertNotIn("neutral_button_only", watched)

    def test_refuse_wrong_fingerprint(self):
        with self.assertRaises(V1BallWatchCompatibilityError):
            extend_known_v1_with_selected_watch(fixture())

    def test_refuse_v2_neutral_suppression(self):
        with self.assertRaisesRegex(V1BallWatchCompatibilityError, "no-autoload"):
            adapt(fixture() + SWING_NEUTRAL_V2_MARKER + "\n")

    def test_refuse_autoload_bridge(self):
        with self.assertRaisesRegex(V1BallWatchCompatibilityError, "no-autoload"):
            adapt(fixture() + BOOT_MARKER + "\n")

    def test_refuse_missing_atomic_or_swing_marker(self):
        for source in (fixture().replace(PATCH_MARKER, "# no atomic"),
                       fixture().replace(SWING_MARKER, "# no swing")):
            with self.subTest(source=source[:25]):
                with self.assertRaises(V1BallWatchCompatibilityError):
                    adapt(source)

    def test_refuse_duplicate_handler_or_tick(self):
        for source in (
            fixture().replace("HANDLERS = {", "HANDLERS = {\nHANDLERS = {"),
            fixture().replace("    _wii_ai_tick()\n",
                              "    _wii_ai_tick()\n    _wii_ai_tick()\n"),
        ):
            with self.assertRaises(V1BallWatchCompatibilityError):
                adapt(source)

    def test_refuse_second_watch(self):
        with self.assertRaises(V1BallWatchCompatibilityError):
            adapt(fixture() + BALL_WATCH_MARKER + "\n")

    def test_refuse_non_v1_input_type(self):
        with self.assertRaises(V1BallWatchCompatibilityError):
            extend_known_v1_with_selected_watch(b"not source")

    def test_reader_contains_all_51_words_source_offset(self):
        target = adapt(fixture())
        self.assertIn('range(0, 0xCC, 4)', target)
        self.assertIn('selected_record + 0x88', target)
        self.assertIn('selected_player_record_words_PRIVATE', target)
        self.assertIn('if read_us > 5000:', target)

    def test_provenance_does_not_claim_live_contact(self):
        target = adapt(fixture())
        self.assertIn('"live_contact_verified": False', target)
        self.assertIn('"a_lead_applied": False', target)
        self.assertIn('"training_allowed": False', target)

    def test_structural_frame_loop_accepts_nonadjacent_socket_poll(self):
        source = fixture().replace(
            "    _wii_ai_tick()\n    # Inline comment",
            "    _wii_ai_tick()\n    _other_observer()\n    # Inline comment")
        compiled = adapt(source)
        self.assertIn("    _wii_ball_watch_tick()\n    _wii_ai_tick()", compiled)
        self.assertIn("    _other_observer()", compiled)

    def test_reject_wrong_tick_scope_and_missing_advance(self):
        for source in (
            fixture().replace("    await event.frameadvance()\n", "    frameadvance_unknown()\n"),
            fixture().replace("    _frame_count += 1\n", "    _frame_count = 0\n"),
        ):
            with self.subTest(source=source[-90:]):
                with self.assertRaises(V1BallWatchCompatibilityError):
                    adapt(source)

    def test_retains_crlf_bridge_and_literal_coroutine_dispatch(self):
        source = fixture().replace("\n", "\r\n")
        patched = adapt(source)
        self.assertIn("    _wii_ball_watch_tick()\r\n    _wii_ai_tick()", patched)
        self.assertEqual(patched.count("    _wii_ai_tick()"), 1)


if __name__ == "__main__":
    unittest.main()
